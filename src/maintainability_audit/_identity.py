"""Stable identity for findings.

A finding's fingerprint answers "is this the same problem I saw last time?"
Get it wrong and two features break at once: `--fail-on-new` raises false
failures on untouched code, and recurrence tracking cannot tell a returning
finding from a fresh one.

The previous scheme embedded the start line — `function:{path}:{name}:{line}`
— so inserting a single import above an untouched function made it read as
simultaneously fixed and new:

    before: function:big.py:huge:1
    after:  function:big.py:huge:2

Nothing about the function changed. One line was added above it.

So identity here is built only from things an unrelated edit elsewhere in the
file cannot move:

* **path and name**, which survive any amount of insertion;
* an **ordinal** among same-named findings in the same file, ordered by
  position. Two overloads both shift together when a line is inserted above
  them, so their relative order — and therefore their ordinals — hold;
* a **content hash** where the finding is about a block of text rather than a
  named unit, as with duplicate blocks.

Line numbers are still reported everywhere. They are just not identity.

Deliberately derived from the report alone. Identity must not require reading
source, or presentation would need a parsing dependency, and the report would
stop being a self-contained record of its own findings.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

# Enough to make collision fanciful without making a fingerprint unreadable
# in a diff. These land in a checked-in baseline file that humans review.
_DIGEST_CHARS = 12


def _digest(sample: str | list[str]) -> str:
    # Duplicate blocks carry their sample as a list of lines; other callers
    # pass a string. Joining rather than repr-ing keeps the digest stable if
    # the carrier type ever changes back.
    text = "\n".join(sample) if isinstance(sample, list) else str(sample)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:_DIGEST_CHARS]


def _ordinals(items: list[dict[str, Any]], key: Any, order: Any) -> dict[int, int]:
    """Map each item's index to its ordinal among items sharing `key`.

    Ordered by `order` so the numbering is a property of position within the
    file rather than of whatever sequence the scanner happened to emit.
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
    """Identity for a duplicated block.

    Locations carry `path:line`, so the line is stripped and the paths are
    sorted — a block does not become a different block because one copy moved
    down, or because the scanner listed the copies in another order. The sample
    text disambiguates two distinct blocks duplicated across the same files.
    """
    paths = sorted({location.rsplit(":", 1)[0] for location in locations})
    return f"duplicate:{','.join(paths)}:{_digest(sample)}"


def finding_fingerprints(report: dict[str, Any]) -> set[str]:
    """Every failing finding in `report`, as stable identities."""
    fingerprints: set[str] = set()

    for item in report.get("largest_files", []):
        if item["status"] == "fail":
            fingerprints.add(file_fingerprint(item["path"]))

    hotspots = [i for i in report.get("function_hotspots", []) if i["status"] == "fail"]
    ordinals = _ordinals(hotspots, lambda i: (i["path"], i["name"]), lambda i: i["start_line"])
    for index, item in enumerate(hotspots):
        fingerprints.add(declaration_fingerprint(item["path"], item["name"], ordinals[index]))

    risks = list(report.get("risk_findings", []))
    ordinals = _ordinals(risks, lambda i: (i["path"], i["name"]), lambda i: i["line"])
    for index, item in enumerate(risks):
        fingerprints.add(risk_fingerprint(item["path"], item["name"], ordinals[index]))

    for item in report.get("duplicate_blocks", []):
        fingerprints.add(duplicate_fingerprint(item["locations"], item.get("sample", "")))

    return fingerprints
