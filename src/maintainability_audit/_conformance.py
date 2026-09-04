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

import re
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


#: Markers that switch a checker off rather than satisfy it. Per language,
#: because the vocabulary differs and a single regex over all of them
#: matches prose: "# type: ignore" in a docstring explaining the convention
#: is not a suppression, and neither is this comment.
#:
#: Deliberately narrow. A marker here has to be a real directive that a
#: real tool obeys; guessing wider would report ordinary comments as
#: evasion, and a check that cries wolf is a check that gets switched off —
#: the same reasoning as the test-pairing rule above.
SUPPRESSION_MARKERS: tuple[tuple[str, str], ...] = (
    (r"#\s*noqa\b", "noqa"),
    (r"#\s*type:\s*ignore\b", "type: ignore"),
    (r"#\s*pragma:\s*no\s*cover\b", "pragma: no cover"),
    (r"#\s*nosec\b", "nosec"),
    (r"//\s*eslint-disable", "eslint-disable"),
    (r"/\*\s*eslint-disable", "eslint-disable"),
    (r"//\s*@ts-(ignore|expect-error)\b", "ts-ignore"),
    (r"@SuppressWarnings\b", "SuppressWarnings"),
    (r"//\s*NOSONAR\b", "NOSONAR"),
    (r"#\s*pylint:\s*disable\b", "pylint: disable"),
    (r"@pytest\.mark\.(skip|xfail)\b", "skipped test"),
    (r"@unittest\.skip\b", "skipped test"),
    (r"\bit\.skip\(|\bdescribe\.skip\(", "skipped test"),
    (r"@Disabled\b", "disabled test"),
    (r"@Ignore\b", "ignored test"),
)

_SUPPRESSION = tuple(
    (re.compile(pattern, re.IGNORECASE), label) for pattern, label in SUPPRESSION_MARKERS
)


def suppressions_added(
    added: dict[str, list[tuple[int, str]]], named: set[str]
) -> list[dict[str, Any]]:
    """Suppressions this change introduced, and whether they land on a finding.

    The failure being watched for: a finding is closed by making it
    invisible rather than by fixing it. Add `# noqa` to the flagged line and
    the next audit reports nothing — the scan goes green over code nobody
    repaired, and scope conformance alone would call that diff obedient,
    because the file it touched is exactly the file the work order named.

    Only *added* lines are read. A suppression already in the tree is not
    evidence about this change, and treating a decade of accumulated
    directives as newly written would drown the signal that matters.

    `on_named_path` is that signal: a suppression added to a file the work
    order flagged is the shape of a finding being silenced, while one added
    elsewhere is ordinary engineering that a reviewer may still want to see.
    """
    found: list[dict[str, Any]] = []
    for path in sorted(added):
        for line_number, text in added[path]:
            for pattern, label in _SUPPRESSION:
                if pattern.search(text):
                    found.append({
                        "path": path,
                        "line": line_number,
                        "marker": label,
                        "on_named_path": path in named,
                    })
                    break
    return found


def scope_conformance(
    report: dict[str, Any],
    changed: set[str],
    revspec: str,
    added: dict[str, list[tuple[int, str]]] | None = None,
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
    suppressions = suppressions_added(added or {}, named)
    silenced = [item for item in suppressions if item["on_named_path"]]

    return {
        "revspec": revspec,
        "work_order_items": len(work_order),
        "named_paths": sorted(named),
        "changed_paths": sorted(changed),
        "in_scope": in_scope,
        "paired_tests": paired,
        "out_of_scope": out_of_scope,
        "unaddressed": sorted(named - set(in_scope)),
        "suppressions_added": suppressions,
        "suppressions_on_named_paths": len(silenced),
        # Two questions, kept apart. `conformant` answers "did it change
        # only what it was asked to"; `clean` also answers "and without
        # switching a checker off in a file that was flagged". Scope alone
        # is satisfiable by adding `# noqa` to the named file and changing
        # nothing else, which is the evasion this pairing exists to catch.
        "conformant": not out_of_scope,
        "clean": not out_of_scope and not silenced,
        # Stated so a reader does not infer more than was checked. The
        # record says which files the work order named, not whether the
        # edits inside them were the right ones.
        "note": (
            "Paths and added lines. A file in scope means the work order "
            "named it, not that the change to it was correct."
        ),
    }
