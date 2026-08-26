"""Structural finding identity, and matching across two scans — ADR 009.

The fingerprint *string* is a human label, and it is deliberately weak:
`git mv` changes the path inside it, and swapping two same-named
overloads changes their ordinals. Every consumer that compared label
sets — the `--fail-on-new` gate, recurrence — inherited those false
"new" findings. This module is the fix: identity is a structured record
(kind, path, name, ordinal, body digest, label), and *matching* is a
relation over those records plus git's own rename evidence, never a
string comparison.

Foundations, on purpose. The gate (`baseline`), recurrence
(`_recurrence`) and presentation (`_identity`) all need the same
matching rule, and they sit on different sides of the layer graph. The
only internal import here is `git_tools`, which owns the process rule.

What deliberately does not match: a **copy**. An identical body at a new
path with no git rename is new code that duplicates old code — gluing it
to the original by digest alone would let cloned findings ride an old
baseline. And a renamed *declaration* (`def huge` → `def enormous`) is a
different finding about different code; the digest never overrides the
name.
"""
from __future__ import annotations

import hashlib
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .git_tools import probe_git

# Enough to make collision fanciful without making a fingerprint
# unreadable in a diff. These land in checked-in baseline files and in
# the scan history that humans review.
DIGEST_CHARS = 12

KIND_DECLARATION = "declaration"
KIND_FILE = "file"
KIND_RISK = "risk"
KIND_DUPLICATE = "duplicate"


def content_digest(sample: str | list[str]) -> str:
    """Digest a block's text as-is; duplicates and risk samples use this."""
    text = "\n".join(sample) if isinstance(sample, list) else str(sample)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:DIGEST_CHARS]


def normalized_body_digest(block: list[str]) -> str:
    """Digest a declaration body so indentation-only moves do not change it.

    Dedent then strip trailing whitespace per line: nesting a function
    one level deeper, or a trailing-space cleanup, is not a new body.
    Comments stay and identifiers stay — a body whose comments changed
    *was* edited, and normalizing harder than the edit people actually
    made would glue distinct findings together.
    """
    body = textwrap.dedent("\n".join(block))
    normalized = "\n".join(line.rstrip() for line in body.splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:DIGEST_CHARS]


def ordinals_by(items: list[dict[str, Any]], key: Any, order: Any) -> dict[int, int]:
    """Map each item's index to its ordinal among items sharing `key`.

    Ordered by `order` so the numbering is a property of position within
    the file rather than of whatever sequence the scanner happened to emit.
    """
    grouped: dict[Any, list[int]] = defaultdict(list)
    for index, item in enumerate(items):
        grouped[key(item)].append(index)
    ordinals: dict[int, int] = {}
    for indexes in grouped.values():
        for rank, index in enumerate(sorted(indexes, key=lambda i: order(items[i]))):
            ordinals[index] = rank
    return ordinals


def file_fingerprint(path: str) -> str:
    return f"file-lines:{path}"


def declaration_fingerprint(path: str, name: str, ordinal: int) -> str:
    return f"function:{path}:{name}#{ordinal}"


def risk_fingerprint(path: str, name: str, ordinal: int) -> str:
    return f"risk:{path}:{name}#{ordinal}"


def duplicate_fingerprint(locations: list[str], sample: str | list[str]) -> str:
    """Identity label for a duplicated block.

    Locations carry `path:line`, so the line is stripped and the paths
    are sorted — a block does not become a different block because one
    copy moved down, or because the scanner listed the copies in another
    order. The sample text disambiguates two distinct blocks duplicated
    across the same files.
    """
    paths = sorted({location.rsplit(":", 1)[0] for location in locations})
    return f"duplicate:{','.join(paths)}:{content_digest(sample)}"


@dataclass(frozen=True)
class Identity:
    """One finding, as the things an unrelated edit cannot move.

    `fingerprint` is the existing human label, kept verbatim so every
    string consumer (charts, targeted lists, old baselines' diffability)
    still has its key. For a duplicate, `path` holds the sorted member
    paths joined by commas and `body_digest` holds the sample digest —
    the same facts the label encodes, held as data so the rename map can
    be applied to each member path.
    """

    kind: str  # "declaration" | "file" | "risk" | "duplicate"
    path: str
    name: str
    ordinal: int
    body_digest: str
    fingerprint: str


def _failing_hotspots(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [i for i in report.get("function_hotspots", []) if i["status"] == "fail"]


def _declaration_identities(report: dict[str, Any]) -> list[Identity]:
    hotspots = _failing_hotspots(report)
    ordinals = ordinals_by(hotspots, lambda i: (i["path"], i["name"]), lambda i: i["start_line"])
    return [
        Identity(
            kind=KIND_DECLARATION,
            path=item["path"],
            name=item["name"],
            ordinal=ordinals[index],
            body_digest=str(item.get("body_digest") or ""),
            fingerprint=declaration_fingerprint(item["path"], item["name"], ordinals[index]),
        )
        for index, item in enumerate(hotspots)
    ]


def _risk_identities(report: dict[str, Any]) -> list[Identity]:
    risks = list(report.get("risk_findings", []))
    ordinals = ordinals_by(risks, lambda i: (i["path"], i["name"]), lambda i: i["line"])
    return [
        Identity(
            kind=KIND_RISK,
            path=item["path"],
            name=item["name"],
            ordinal=ordinals[index],
            # A risk finding is a matched pattern, not a body; the flagged
            # text is its content for rule-3 purposes.
            body_digest=content_digest(item.get("text") or ""),
            fingerprint=risk_fingerprint(item["path"], item["name"], ordinals[index]),
        )
        for index, item in enumerate(risks)
    ]


def identities_from_report(report: dict[str, Any]) -> frozenset[Identity]:
    """Every failing finding in `report`, as structured identities.

    The population is exactly `finding_fingerprints`' population — the
    two views must name the same findings or the gate and the label
    consumers would disagree about what the scan found.
    """
    identities: set[Identity] = set()
    for item in report.get("largest_files", []):
        if item["status"] == "fail":
            identities.add(Identity(
                kind=KIND_FILE, path=item["path"], name="", ordinal=0,
                body_digest="", fingerprint=file_fingerprint(item["path"]),
            ))
    identities.update(_declaration_identities(report))
    identities.update(_risk_identities(report))
    for item in report.get("duplicate_blocks", []):
        paths = sorted({loc.rsplit(":", 1)[0] for loc in item["locations"]})
        sample = item.get("sample", "")
        identities.add(Identity(
            kind=KIND_DUPLICATE, path=",".join(paths), name="", ordinal=0,
            body_digest=content_digest(sample),
            fingerprint=duplicate_fingerprint(item["locations"], sample),
        ))
    return frozenset(identities)


def rename_map(root: Path, old_commit: str, new_commit: str) -> dict[str, str]:
    """Old path → new path, as git itself attests between two commits.

    Only `R` status lines count: git's rename detection is the evidence
    that a file moved, and nothing weaker (a matching digest at a new
    path) is accepted in its place. Empty or equal commits yield an
    empty map, as does any git failure — no map means no rename glue,
    never a crash.
    """
    if not old_commit or not new_commit or old_commit == new_commit:
        return {}
    # Probed on purpose, as this function's docstring already promised:
    # no map means no rename glue, never a crash.
    output = probe_git(
        ["diff", "--name-status", "--find-renames", old_commit, new_commit], root,
    )
    renames: dict[str, str] = {}
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) == 3 and fields[0].startswith("R"):
            renames[fields[1]] = fields[2]
    return renames


def _mapped(path: str, renames: dict[str, str]) -> str:
    return renames.get(path, path)


def _named_alike(current: Identity, known: Identity, renames: dict[str, str]) -> bool:
    """Kind, name and rename-mapped path agree, for the named kinds."""
    return (
        current.kind == known.kind
        and known.kind in (KIND_DECLARATION, KIND_RISK)
        and current.name == known.name
        and current.path == _mapped(known.path, renames)
    )


def _label_match(current: Identity, known: Identity, renames: dict[str, str]) -> bool:
    return current.fingerprint == known.fingerprint


def _digest_match(current: Identity, known: Identity, renames: dict[str, str]) -> bool:
    """The body itself, at the same (rename-mapped) home: survives reorder.

    A duplicate block is all body, so its sample digest plus its mapped
    member paths is this rule for that kind. A digest alone — new path,
    no rename; or a different name — never matches: a copy and a
    renamed declaration are new findings.
    """
    if not known.body_digest or current.body_digest != known.body_digest:
        return False
    if current.kind == known.kind == KIND_DUPLICATE:
        mapped = sorted(_mapped(path, renames) for path in known.path.split(","))
        return current.path.split(",") == mapped
    return _named_alike(current, known, renames)


def _position_match(current: Identity, known: Identity, renames: dict[str, str]) -> bool:
    """Same (path, name, ordinal): survives body edits and line inserts."""
    return _named_alike(current, known, renames) and current.ordinal == known.ordinal


def _file_rename_match(current: Identity, known: Identity, renames: dict[str, str]) -> bool:
    """A file finding follows git's rename evidence and nothing weaker."""
    return (
        current.kind == known.kind == KIND_FILE
        and known.path in renames
        and current.path == renames[known.path]
    )


# Strongest evidence claims its counterpart first when whole sets are
# matched. The digest — the body itself — outranks the label, because a
# same-named sibling inserted above shifts every ordinal below it: the
# old #0 label then *names the newcomer*, and label-first pairing would
# call the newcomer old and an old body new.
_MATCH_PASSES = (_digest_match, _label_match, _position_match, _file_rename_match)


def same_finding(current: Identity, known: Identity, renames: dict[str, str]) -> bool:
    """Whether `current` could be the finding `known` recorded.

    The disjunction of every matching rule. Kinds with no structural
    rule — including the degenerate label-only identities that older
    records and hand-written baselines reduce to — can match nothing
    but their exact label.
    """
    return any(rule(current, known, renames) for rule in _MATCH_PASSES)


def assignment(
    current: frozenset[Identity] | list[Identity],
    known: frozenset[Identity] | list[Identity],
    renames: dict[str, str],
) -> dict[Identity, Identity]:
    """One-to-one pairing of known findings to current ones, best rule first.

    Each pass sweeps the still-unpaired knowns in label order and lets
    each claim at most one still-unpaired current. One-to-one is the
    point: `same_finding` says two findings *could* be the same, and a
    body that matches one known cannot also be the survival of another.
    """
    paired: dict[Identity, Identity] = {}
    unclaimed = set(current)
    for rule in _MATCH_PASSES:
        for item in sorted(set(known) - paired.keys(), key=lambda i: i.fingerprint):
            match = next(
                (candidate for candidate in sorted(unclaimed, key=lambda i: i.fingerprint)
                 if rule(candidate, item, renames)), None)
            if match is not None:
                paired[item] = match
                unclaimed.remove(match)
    return paired


def unmatched(
    current: frozenset[Identity],
    known: frozenset[Identity],
    renames: dict[str, str],
) -> frozenset[Identity]:
    """The current findings no known finding accounts for — the new ones."""
    claimed = set(assignment(current, known, renames).values())
    return frozenset(finding for finding in current if finding not in claimed)
