"""Detecting a helper that was written twice under two names.

This is the most-cited empirical complaint about AI-written code: an
agent that cannot see your existing helper writes a second one, the
copies drift, and a bug fixed in one survives in the others. Exact text
matching cannot catch it, because the second copy is the same structure
with different identifiers.

The tests below pin both halves of the contract — that renamed copies
*are* found, and that the two false-positive classes the reference corpus
exposed are *not* reported:

- bodies too short for similarity to mean anything
- thin delegations whose shape is dictated by the API surface rather than
  by what they do, such as requests' ``put``/``patch`` or flask's
  ``template_filter``/``template_test``
"""
from __future__ import annotations

from pathlib import Path

from maintainability_audit._tokens import declaration_tokens
from maintainability_audit.config import load_config
from maintainability_audit.report import build_report
from maintainability_audit.similarity import (
    find_near_duplicates,
    fingerprint,
    is_eligible,
    jaccard,
    shingles,
)

# A body with real branching, comfortably past MIN_TOKENS.
ORIGINAL = """
export function normalizeOrder(input, rate) {
  const parsed = Number(input);
  if (!Number.isFinite(parsed)) {
    throw new Error("bad amount");
  }
  let scaled = parsed * rate;
  for (const step of [2, 4, 8]) {
    if (scaled > step) {
      scaled = scaled / step;
    }
  }
  return scaled > 0 ? scaled : 0;
}
"""

# Same logic, every identifier renamed. What an agent produces when it
# does not know the first one exists.
RENAMED = """
export function scaleTrade(value, factor) {
  const converted = Number(value);
  if (!Number.isFinite(converted)) {
    throw new Error("bad amount");
  }
  let total = converted * factor;
  for (const tier of [2, 4, 8]) {
    if (total > tier) {
      total = total / tier;
    }
  }
  return total > 0 ? total : 0;
}
"""

DIFFERENT = """
export function summarize(rows) {
  const seen = new Map();
  for (const row of rows) {
    const key = row.id;
    if (!seen.has(key)) {
      seen.set(key, []);
    }
    seen.get(key).push(row.value);
  }
  return Array.from(seen.entries());
}
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def mark(name: str, source: str, path: str = "a.ts", start: int = 1):
    tokens = declaration_tokens(Path(path).suffix, source.strip().splitlines())
    return fingerprint(path, name, start, start + len(source.splitlines()), "function", tokens)


# ---------------------------------------------------------------------------
# Renaming must not hide a copy
# ---------------------------------------------------------------------------

def test_a_renamed_copy_is_detected() -> None:
    pairs = find_near_duplicates([mark("normalizeOrder", ORIGINAL, "a.ts"), mark("scaleTrade", RENAMED, "b.ts")])

    assert len(pairs) == 1
    assert pairs[0].similarity >= 0.8


def test_genuinely_different_logic_is_not_reported() -> None:
    assert find_near_duplicates([mark("normalizeOrder", ORIGINAL, "a.ts"), mark("summarize", DIFFERENT, "b.ts")]) == []


def test_identifier_renaming_produces_the_same_fingerprint() -> None:
    """The whole mechanism in one assertion: names are anonymized by order
    of first appearance, so only structure survives."""
    left = declaration_tokens(".ts", ORIGINAL.strip().splitlines())
    right = declaration_tokens(".ts", RENAMED.strip().splitlines())

    assert left == right


def test_comments_and_string_contents_never_reach_the_fingerprint() -> None:
    commented = ORIGINAL.replace('throw new Error("bad amount");', '/* if for while */ throw new Error("x if for");')

    assert jaccard(shingles(declaration_tokens(".ts", ORIGINAL.strip().splitlines())),
                   shingles(declaration_tokens(".ts", commented.strip().splitlines()))) >= 0.8


# ---------------------------------------------------------------------------
# The false positives the corpus exposed
# ---------------------------------------------------------------------------

def test_short_bodies_are_ineligible() -> None:
    assert not is_eligible(["V0", "=", "V1", "(", ")", ";"])


def test_thin_delegations_are_ineligible_however_long() -> None:
    """requests' `put`/`patch` are near-identical because they forward a
    call with a different constant. That is API surface, not duplication,
    and reporting it trains users to ignore the finding."""
    delegation = ["V0"] * (200) + ["(", ")", ";"]

    assert not is_eligible(delegation)


def test_a_long_branching_body_is_eligible() -> None:
    assert is_eligible(declaration_tokens(".ts", ORIGINAL.strip().splitlines()))


# ---------------------------------------------------------------------------
# Reporting shape
# ---------------------------------------------------------------------------

def test_a_clique_of_copies_collapses_toward_one_original() -> None:
    """Four copies of one helper form six pairs. Emitting all six says the
    same thing six times; the useful shape is "these all duplicate that
    one", which is linear in the number of copies and reads as a single
    instruction: reuse the original."""
    marks = [mark(f"copy{index}", RENAMED, f"file{index}.ts") for index in range(4)]

    pairs = find_near_duplicates(marks)

    assert len(pairs) == 3, "expected N-1 pairs for N copies, not N(N-1)/2"
    keys = {(pair.left.location, pair.right.location) for pair in pairs}
    assert len(keys) == len(pairs), "no pair reported twice"
    shared = set.intersection(*({pair.left.location, pair.right.location} for pair in pairs))
    assert len(shared) == 1, "every pair should reference one common original"


def test_report_pairs_each_finding_with_the_original_to_reuse(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "src" / "one.ts", ORIGINAL)
    write(tmp_path / "src" / "two.ts", RENAMED)

    findings = build_report(tmp_path, load_config(None))["near_duplicates"]

    assert len(findings) == 1
    finding = findings[0]
    assert finding["cross_file"] is True
    assert finding["duplicate_of"]["name"] in {"normalizeOrder", "scaleTrade"}
    assert finding["duplicate_of"]["start_line"] > 0


def test_test_files_are_excluded_from_near_duplicate_scanning(tmp_path: Path) -> None:
    """In the corpus, near-duplicates in mature projects were almost
    entirely parallel test variants. They are not the defect this
    measures, and including them drowns the production signal."""
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "tests" / "test_one.ts", ORIGINAL)
    write(tmp_path / "tests" / "test_two.ts", RENAMED)

    assert build_report(tmp_path, load_config(None))["near_duplicates"] == []
