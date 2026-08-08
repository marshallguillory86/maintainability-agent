"""Finding declarations that are near-copies of each other.

The complaint this measures is specific and empirically the most common
one about AI-written code: an agent that does not know your helper exists
writes a second one. The copies then drift, and a bug fixed in one
survives in the other three.

The existing duplicate-block scanner cannot see this. It matches text, and
a model asked twice for the same helper produces the same *structure* with
different names. ``_tokens`` handles that by anonymizing identifiers; this
module decides which of the resulting fingerprints are close enough to
report, and pairs each finding with the declaration it duplicates so the
remediation prompt can say *reuse the one at this path and line* rather
than the useless *there is duplication somewhere*.

Three deliberate conservatisms, all of which under-report:

- **Small declarations are skipped.** Short bodies are legitimately alike
  — every two-line getter resembles every other — and reporting them
  would train users to ignore the finding.
- **Similarity is compared over sets of k-token shingles**, so a pair must
  share ordered runs of structure, not merely a bag of tokens.
- **Only pairs above a high threshold are reported**, and each declaration
  is reported once, against its closest match.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._tokens import declaration_tokens
from .declarations import DECLARATION_SUFFIXES
from .metrics import is_test_path
from .source import SourceIndex, index_or_new

# A declaration must reach this many normalized tokens, and contain this
# much branching, before it is considered at all.
#
# Both thresholds were fitted against the reference corpus, not guessed.
# At 45 tokens with no branching requirement the detector reported
# requests' `put`/`patch` and flask's `template_filter`/`template_test` —
# deliberate parallel API surface, not defects. Those are thin
# delegations: nearly all signature, one statement, no control flow.
# Requiring real logic removes that class of false positive while keeping
# genuine clones like a crypto helper copied across two packages.
MIN_TOKENS = 80

# Keywords that indicate a body does something rather than forwarding a
# call. Union of the Python and C-family spellings; ``_tokens`` preserves
# keywords verbatim, so these survive identifier anonymization.
CONTROL_TOKENS = frozenset(
    {"if", "elif", "else", "for", "while", "try", "except", "catch", "switch", "case", "with", "return"}
)

MIN_CONTROL_TOKENS = 2

# Length of each token run. Long enough that sharing one is meaningful,
# short enough that a small edit does not destroy every shingle.
SHINGLE_SIZE = 6

# Jaccard similarity at or above which two declarations are reported.
# 0.8 keeps near-identical bodies and drops merely similar ones.
SIMILARITY_THRESHOLD = 0.8

# A pair must share at least this many shingles before the exact
# similarity is computed. Purely a cost control: it prunes the candidate
# set without changing which pairs can qualify, since two bodies cannot
# reach the threshold on fewer.
MIN_SHARED_SHINGLES = 3


@dataclass(frozen=True)
class Fingerprint:
    """One declaration, reduced to the shape used for comparison."""

    path: str
    name: str
    start_line: int
    end_line: int
    kind: str
    shingles: frozenset[int]

    @property
    def location(self) -> str:
        return f"{self.path}:{self.start_line}"


@dataclass
class SimilarPair:
    left: Fingerprint
    right: Fingerprint
    similarity: float


def shingles(tokens: list[str], size: int = SHINGLE_SIZE) -> frozenset[int]:
    """Hashed runs of ``size`` consecutive tokens.

    Hashed rather than kept as tuples purely for memory: a large repo
    produces millions of runs, and only set membership is ever needed.
    """
    if len(tokens) < size:
        return frozenset()
    return frozenset(hash(tuple(tokens[index : index + size])) for index in range(len(tokens) - size + 1))


def is_eligible(tokens: list[str]) -> bool:
    """Whether a body carries enough logic for similarity to mean anything.

    Guards the two false-positive classes the corpus exposed: bodies too
    short to differ from any other, and thin delegations whose shape is
    dictated by the API rather than by what they do.
    """
    if len(tokens) < MIN_TOKENS:
        return False
    return sum(1 for item in tokens if item in CONTROL_TOKENS) >= MIN_CONTROL_TOKENS


def fingerprint(path: str, name: str, start: int, end: int, kind: str, tokens: list[str]) -> Fingerprint | None:
    """Reduce one declaration, or None when it is too small to judge."""
    if not is_eligible(tokens):
        return None
    marks = shingles(tokens)
    return Fingerprint(path, name, start, end, kind, marks) if marks else None


def jaccard(left: frozenset[int], right: frozenset[int]) -> float:
    union = len(left | right)
    return len(left & right) / union if union else 0.0


def _candidate_pairs(fingerprints: list[Fingerprint]) -> dict[tuple[int, int], int]:
    """Count shared shingles per pair, via an inverted index.

    Comparing every declaration against every other is quadratic and
    unusable on a large repo. Indexing by shingle means only declarations
    that already share structure are ever compared.
    """
    index: dict[int, list[int]] = defaultdict(list)
    for position, item in enumerate(fingerprints):
        for mark in item.shingles:
            index[mark].append(position)

    shared: dict[tuple[int, int], int] = defaultdict(int)
    for holders in index.values():
        # A shingle appearing in a great many declarations is boilerplate
        # (an import preamble, a decorator stack). It carries no signal
        # and would contribute a quadratic number of useless pairs.
        if len(holders) > 12:
            continue
        for offset, left in enumerate(holders):
            for right in holders[offset + 1 :]:
                shared[(left, right)] += 1
    return shared


def find_near_duplicates(
    fingerprints: list[Fingerprint],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[SimilarPair]:
    """Pair each declaration with its single closest near-copy.

    Emitting every qualifying pair would bury the reader under a clique —
    four copies of one helper make six pairs saying one thing. Keeping
    only each declaration's best match collapses that to three, all
    referencing the same original, which reads as one instruction: reuse
    it. Growth is linear in the number of copies rather than quadratic.
    """
    shared = _candidate_pairs(fingerprints)
    best: dict[int, tuple[float, int]] = {}
    for (left, right), count in shared.items():
        if count < MIN_SHARED_SHINGLES:
            continue
        score = jaccard(fingerprints[left].shingles, fingerprints[right].shingles)
        if score < threshold:
            continue
        for position, other in ((left, right), (right, left)):
            if position not in best or score > best[position][0]:
                best[position] = (score, other)

    seen: set[tuple[int, int]] = set()
    pairs: list[SimilarPair] = []
    for position, (score, other) in best.items():
        key = (min(position, other), max(position, other))
        if key in seen:
            continue
        seen.add(key)
        pairs.append(SimilarPair(fingerprints[key[0]], fingerprints[key[1]], round(score, 3)))
    pairs.sort(key=lambda pair: (-pair.similarity, pair.left.location))
    return pairs


def collect_fingerprints(
    root: Path, files: list[Path], production_only: bool = True, index: SourceIndex | None = None
) -> list[Fingerprint]:
    """Fingerprint every eligible declaration across the given files.

    Production-only by default. In the reference corpus, near-duplicates
    in mature projects were overwhelmingly *test* variants — deliberately
    parallel cases like ``test_filter_with_template`` beside
    ``test_filter_with_name_and_template`` — which are not the defect this
    measures. Excluding them is what makes the signal legible.
    """
    source = index_or_new(index)
    found: list[Fingerprint] = []
    for path in files:
        if path.suffix not in DECLARATION_SUFFIXES:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if production_only and is_test_path(rel):
            continue
        lines = source.lines(path)
        ranges, _ = source.declarations(path)
        for decl in ranges:
            if decl.kind != "function":
                continue
            tokens = declaration_tokens(path.suffix, lines[decl.start - 1 : decl.end])
            mark = fingerprint(rel, decl.name, decl.start, decl.end, decl.kind, tokens)
            if mark is not None:
                found.append(mark)
    return found


def near_duplicate_findings(
    root: Path, files: list[Path], index: SourceIndex | None = None
) -> list[dict[str, Any]]:
    """Near-duplicate declarations, worst first, ready for the report.

    Each finding names *both* sides, because the actionable instruction is
    "reuse the one that already exists", and an agent cannot follow that
    without being told where it is.
    """
    pairs = find_near_duplicates(collect_fingerprints(root, files, index=index))
    return [
        {
            "similarity": pair.similarity,
            "cross_file": pair.left.path != pair.right.path,
            "path": pair.left.path,
            "name": pair.left.name,
            "start_line": pair.left.start_line,
            "lines": pair.left.end_line - pair.left.start_line + 1,
            "duplicate_of": {
                "path": pair.right.path,
                "name": pair.right.name,
                "start_line": pair.right.start_line,
            },
        }
        for pair in pairs
    ]
