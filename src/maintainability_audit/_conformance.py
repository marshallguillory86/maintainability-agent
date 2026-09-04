"""Did the diff stay inside the work order it was given?

The product's central claim is a bounded work order: *fix exactly these
findings and refactor nothing else*. Until now that bound was an
**instruction**. The prompt said it, and nothing checked it — so an agent
that rewrote half the tree while closing one finding produced a diff
indistinguishable, to this tool, from one that did as it was told.

This is the check that makes the bound verifiable. It reads the finished
report and a revspec, and reports which changed files the work order
actually named. It is the first of the three mechanisms behind the
attestation artifact, and the one a code-generating agent cannot honestly
perform about itself.

**What it must not do is cry wolf.** A correct remediation almost always
touches a file the work order does not name: the test that proves the fix.
A check that flagged every good remediation would be turned off within a
week, so a test file is in scope when it pairs to a named path by the same
convention `_test_pairing` already uses for coverage — `test_foo.py` pairs
to `foo.py`. A test paired to nothing named is still reported, because
"while I was here I rewrote the suite" is exactly the drift being watched
for.

Three deliberate limits:

- **It never scores.** Whether a diff was obedient is a fact about an
  agent's behaviour, not evidence about the code's condition, so nothing
  here reaches scoring or moves a grade.
- **It reports, it does not gate**, unless a caller asks it to. A finding
  can legitimately require touching a caller the work order did not name,
  and a check that cannot be argued with becomes a check that is bypassed.
- **It compares paths, not intent.** A file being in scope says the work
  order named it, not that the change to it was the right one. Review is
  still review.
"""

from __future__ import annotations

from typing import Any

from ._metrics_types import is_test_path
from ._test_pairing import subject_stem


def _named_paths(work_order: list[dict[str, Any]]) -> set[str]:
    """Every path the work order put in front of the agent."""
    return {
        str(item["path"]) for item in work_order
        if isinstance(item, dict) and item.get("path")
    }


def _pairs_to_named(path: str, named: set[str]) -> bool:
    """Whether a test file covers something the work order named.

    Uses the pairing convention the coverage aspect already applies, so a
    remediation's own test is in scope without the caller declaring it —
    and a test that covers nothing in the work order is not.
    """
    if not is_test_path(path):
        return False
    subject = subject_stem(path)
    if not subject:
        return False
    return any(subject_stem(candidate) == subject for candidate in named)


def scope_conformance(
    report: dict[str, Any], changed: set[str], revspec: str
) -> dict[str, Any]:
    """How a diff relates to the work order the agent was handed.

    Returns the record, never a verdict on the code. `in_scope`,
    `paired_tests` and `out_of_scope` partition the changed files;
    `unaddressed` names work-order paths the diff did not touch, which is
    not a failure — a bounded change may take one item at a time.
    """
    work_order = report.get("work_order") or []
    named = _named_paths(work_order)

    in_scope = sorted(path for path in changed if path in named)
    remaining = {path for path in changed if path not in named}
    paired = sorted(path for path in remaining if _pairs_to_named(path, named))
    out_of_scope = sorted(remaining - set(paired))

    return {
        "revspec": revspec,
        "work_order_items": len(work_order),
        "named_paths": sorted(named),
        "changed_paths": sorted(changed),
        "in_scope": in_scope,
        "paired_tests": paired,
        "out_of_scope": out_of_scope,
        "unaddressed": sorted(named - set(in_scope)),
        "conformant": not out_of_scope,
        # Stated so a reader does not infer more than was checked. The
        # record says which files the work order named, not whether the
        # edits inside them were the right ones.
        "note": (
            "Paths only. A file in scope means the work order named it, not "
            "that the change to it was correct."
        ),
    }
