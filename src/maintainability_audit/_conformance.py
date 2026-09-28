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

from fnmatch import fnmatchcase
from typing import Any

from ._metrics_types import is_test_path

# The marker vocabulary lives with the oracle check that also reads it;
# re-exported here because `_precommit` and the tests ask this module.
from ._oracle import SUPPRESSION_MARKERS as SUPPRESSION_MARKERS
from ._oracle import markers_in as markers_in
from ._oracle import oracle_weakening
from ._test_pairing import subject_stem


def read_ask(path: str) -> set[str]:
    """The paths and globs an operator's ask names (Decision 13).

    Read through the operator-file door, so a symlink, a FIFO or a directory
    is refused rather than followed. Always the operator's path: an ask the
    audited tree supplied about itself would be the writable oracle again.
    An ask that names nothing is refused, because reading it as "nothing
    was asked" would report every change out of scope and look like a
    finding rather than a mistake in the ask.
    """
    from pathlib import Path

    from ._operator_reads import read_operator_file

    entries = {
        line.strip() for line in read_operator_file(Path(path)).splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    if not entries:
        raise ValueError(f"the ask {path} names no path; list the paths or globs the task was asked to change")
    return entries


def _asked(path: str, ask: set[str]) -> bool:
    return any(path == entry or fnmatchcase(path, entry) for entry in ask)


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
            label = markers_in(text)
            if label:
                found.append({
                    "path": path,
                    "line": line_number,
                    "marker": label,
                    "on_named_path": path in named,
                })
    return found


def _what_was_asked(work_order: list[dict[str, Any]], changed: set[str],
                    ask: set[str] | None) -> tuple[set[str], list[str]]:
    """``(named paths, changed paths in scope)`` from the ask or the work order.

    Decision 13: with an operator's ask, the ask is what was named — for
    work this tool did not order. Without one, the work order is the ask.
    """
    if ask:
        in_scope = sorted(path for path in changed if _asked(path, ask))
        literal = {entry for entry in ask if not any(c in entry for c in "*?[")}
        return set(in_scope) | literal, in_scope
    named = _named_paths(work_order)
    return named, sorted(path for path in changed if path in named)


def _partition(changed: set[str], named: set[str]) -> tuple[list[str], list[str]]:
    """``(paired tests, out of scope)`` among the changed files not named."""
    remaining = {path for path in changed if path not in named}
    paired = sorted(path for path in remaining if _pairs_to_named(path, named))
    return paired, sorted(remaining - set(paired))


def _note(ask: set[str] | None) -> str:
    """Stated so a reader does not infer more than was checked."""
    whose = "operator's ask" if ask else "work order"
    return f"Paths and changed lines. A file in scope means the {whose} named it, not that the change to it was correct."


def _source(ask: set[str] | None) -> str:
    """Whose ask the diff was read against: the operator's, or the work order."""
    return "operator" if ask else "work order"


def _unmatched_globs(ask: set[str] | None, changed: set[str]) -> list[str]:
    """Globs in the ask that matched no changed file: said, not dropped."""
    return sorted(
        entry for entry in (ask or ())
        if any(c in entry for c in "*?[") and not any(fnmatchcase(path, entry) for path in changed)
    )


def _tests_among(paths: list[str]) -> int:
    return sum(1 for path in paths if is_test_path(path))


def scope_conformance(
    report: dict[str, Any],
    changed: set[str],
    revspec: str,
    added: dict[str, list[tuple[int, str]]] | None = None,
    removed: dict[str, list[tuple[int, str]]] | None = None,
    ask: set[str] | None = None,
) -> dict[str, Any]:
    """How a diff relates to the work order the agent was handed.

    Returns the record, never a verdict on the code. `in_scope`,
    `paired_tests` and `out_of_scope` partition the changed files;
    `unaddressed` names work-order paths the diff did not touch, which is
    not a failure — a bounded change may take one item at a time.
    """
    work_order = report.get("work_order") or []
    named, in_scope = _what_was_asked(work_order, changed, ask)
    paired, out_of_scope = _partition(changed, named)
    suppressions = suppressions_added(added or {}, named)
    silenced = [item for item in suppressions if item["on_named_path"]]
    weakened = oracle_weakening(added or {}, removed)

    return {
        "revspec": revspec,
        "ask_source": _source(ask),
        # A glob in the ask that matched no changed file: said, not dropped.
        "ask_unmatched": _unmatched_globs(ask, changed),
        "work_order_items": len(work_order),
        "named_paths": sorted(ask or named),
        "changed_paths": sorted(changed),
        "in_scope": in_scope,
        "paired_tests": paired,
        "out_of_scope": out_of_scope,
        "out_of_scope_production": len(out_of_scope) - _tests_among(out_of_scope),
        "out_of_scope_tests": _tests_among(out_of_scope),
        "unaddressed": sorted(named - set(in_scope)),
        "suppressions_added": suppressions,
        "suppressions_on_named_paths": len(silenced),
        # Decision 12: the tests are a record the diff can write. A skip,
        # an alias, a tautology or a deleted assertion in any test file the
        # diff touched makes the suite unable to fail, and `clean` said
        # nothing about it while the file was a paired test.
        "oracle_weakened": weakened,
        # Two questions, kept apart. `conformant` answers "did it change
        # only what it was asked to"; `clean` also answers "and without
        # switching a checker off in a file that was flagged". Scope alone
        # is satisfiable by adding `# noqa` to the named file and changing
        # nothing else, which is the evasion this pairing exists to catch.
        "conformant": not out_of_scope,
        "clean": not out_of_scope and not silenced and not weakened,
        # Stated so a reader does not infer more than was checked. The
        # record says which files the work order named, not whether the
        # edits inside them were the right ones.
        "note": _note(ask),
    }
