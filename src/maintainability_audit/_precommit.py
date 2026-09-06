"""What the index is about to commit, measured before it becomes history.

The roadmap names this project end-of-loop heavy: *"strong where it is
cheapest to be strong — a CI gate after the work is done — and thin
during the loop, where a constraint is worth far more because it prevents
rather than rejects."* This is the other end. Same rubric, same
thresholds, at the moment the change is still in the author's hands.

Four properties decide the design, and three of them are refusals.

**It reads the index, never the working tree.** A developer who stages
half a file with `git add -p` and keeps typing has a tree the commit will
not contain. A hook that reads the tree therefore passes content nobody
measured — the classic pre-commit bug, and the one this exists to avoid.
Everything here comes from `git show :path`.

**It never scores.** A staged diff has no population, and the rubric
already says so: a `--changed-only` run reports *"6 is below the
calibration floor of 32 for files_scanned, so no rate drawn from it means
anything."* What survives without a population is the absolute half —
this declaration is 118 lines against a budget of 80, this file crossed
`max_file_lines`, this line adds a suppression. Thresholds need no
denominator. Rates do, and there is none.

**It applies no repository gates.** A missing README, an undocumented
test command, a dirty worktree: those are properties of a repository, not
of a diff, and a hook that blocks a commit for them is punishing the
author for the state of the room.

**It writes nothing and runs nothing.** No history append, no report
file, and emphatically not the opt-in test suite — on this repository
that suite is 255 of the 266 seconds a full audit takes, and a
four-minute commit is a hook that gets uninstalled the same afternoon.

The remedy text is not written here. A finding is shaped into the report
dictionary `_work_order` already consumes, so the `target`, `rationale`
and ordering a full audit produces are the ones a blocked commit prints.
Two sources of advice for one finding class is how they drift apart.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ._conformance import markers_in
from .declarations import DECLARATION_SUFFIXES, detect_functions
from .git_tools import staged_added_lines, staged_blob, staged_paths
from .metrics import file_status, is_excluded

#: A finding class the full audit does not have, because only a diff can
#: see it: a marker that silences an analyser, added by this change. The
#: repository-wide audit deliberately ignores markers already in the tree
#: — they are somebody's earlier decision — so this is the one place the
#: rule can fire honestly.
SUPPRESSION_CLASS = "added-suppression"


def _scannable(config: dict[str, Any], paths: set[str]) -> list[str]:
    """Staged paths this audit is allowed to open, in a stable order.

    The same two filters the repository scan applies, so a file excluded
    from the audit is excluded from the hook. A hook stricter than the
    gate it belongs to is a hook that blocks commits CI would have passed.
    """
    include = set(config["paths"]["include_extensions"])
    excludes = list(config["paths"].get("exclude_patterns") or [])
    return sorted(
        rel for rel in paths
        if Path(rel).suffix in include and not is_excluded(rel, excludes)
    )


def _risk_patterns(config: dict[str, Any]) -> list[tuple[str, re.Pattern[str]]]:
    compiled = []
    for entry in config.get("risk_patterns") or []:
        pattern = entry.get("pattern") if isinstance(entry, dict) else None
        if not pattern:
            continue
        try:
            compiled.append((entry.get("name", "risk"), re.compile(pattern)))
        except re.error:
            # A repository's own bad regex is not this hook's failure to
            # report. The audit surfaces it; a commit is not blocked by it.
            continue
    return compiled


def _hotspots_for(
    root: Path, rel: str, lines: list[str], thresholds: dict[str, int]
) -> list[dict[str, Any]]:
    """Staged declarations in one file, in the report's hotspot shape."""
    if Path(rel).suffix not in DECLARATION_SUFFIXES:
        return []
    # `root / rel` names where the file will be, which is not always
    # where it is: the scanners take the path for its suffix and its name
    # relative to the root, and read their content from `lines` — which
    # came from the index, not from that path. A staged file whose
    # working copy has since been deleted is still measured, because the
    # commit still contains it.
    return [
        {"path": rel, "name": metric.name, "start_line": metric.start_line,
         "lines": metric.lines, "complexity": metric.complexity,
         "cognitive": metric.cognitive, "status": metric.status,
         "kind": metric.kind}
        for metric in detect_functions(root, root / rel, lines, thresholds)
    ]


def _added_line_findings(
    rel: str, added: list[tuple[int, str]],
    patterns: list[tuple[str, re.Pattern[str]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Risk matches and suppression markers among one file's added lines.

    Added lines only, and that is the whole reason this reads a diff at
    all: a marker already in the tree is somebody's earlier decision,
    and reporting it here would blame this author for it.
    """
    risk: list[dict[str, Any]] = []
    suppressions: list[dict[str, Any]] = []
    for number, text in added:
        excerpt = text.strip()[:120]
        risk.extend(
            {"path": rel, "line": number, "pattern": name, "text": excerpt}
            for name, pattern in patterns if pattern.search(text)
        )
        label = markers_in(text)
        if label:
            suppressions.append(
                {"path": rel, "line": number, "marker": label, "text": excerpt})
    return risk, suppressions


def staged_report(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    """A report-shaped dictionary describing only what the index holds.

    Deliberately report-*shaped* rather than a real report: `_work_order`
    reads `function_hotspots`, `largest_files` and `summary`, so building
    those three from staged content buys every remedy string and the
    whole ordering without a second copy of either.

    `summary` carries zeroed counters on purpose. `_delta_for` recomputes
    the score to order items by what clearing them is worth, finds no
    estimate — a diff has no population — and returns 0.0 for every
    class, which is the honest answer. The ordering then falls back to
    severity, which is a property of the finding rather than of a
    population, and is exactly what a hook should sort by.
    """
    thresholds = config["thresholds"]
    scannable = _scannable(config, staged_paths(root))
    added = staged_added_lines(root)
    patterns = _risk_patterns(config)

    largest: list[dict[str, Any]] = []
    hotspots: list[dict[str, Any]] = []
    risk: list[dict[str, Any]] = []
    suppressions: list[dict[str, Any]] = []

    for rel in scannable:
        lines = staged_blob(root, rel).splitlines()
        largest.append({
            "path": rel, "lines": len(lines),
            "status": file_status(len(lines), thresholds),
        })
        hotspots.extend(_hotspots_for(root, rel, lines, thresholds))
        matched, silenced = _added_line_findings(rel, added.get(rel, []), patterns)
        risk.extend(matched)
        suppressions.extend(silenced)

    return {
        "root": str(root),
        "scanned": scannable,
        "largest_files": largest,
        "function_hotspots": hotspots,
        "risk_findings": risk,
        "added_suppressions": suppressions,
        # Zeroed, and never scored. See the docstring: this exists so the
        # work-order builders can run, not so a number can be produced.
        "summary": {
            "files_scanned": len(scannable), "declarations_scanned": 0,
            "file_failures": sum(1 for f in largest if f["status"] == "fail"),
            "function_failures": sum(1 for h in hotspots if h["status"] == "fail"),
            "file_warnings": 0, "function_warnings": 0,
            "duplicate_blocks": 0, "risk_findings": len(risk),
            "hard_gate_failures": 0, "test_file_count": 0,
        },
    }


def staged_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Every blocking finding in a staged report, worst first.

    Takes the report rather than a repository so the judgment half of
    this module can be exercised without a git index: what blocks a
    commit is a property of the content, and a test that has to build a
    repository to ask about it will be written once and then avoided.

    Threshold breaches come from the same two `_work_order` builders the
    full audit uses, so their wording is the wording a report gives. What
    is deliberately skipped is everything `work_order` does *around*
    those builders: it recomputes the score twice per class to order
    items by what clearing them is worth, and the evidence boundary
    refuses that outright on a diff — `UnsupportedReportSchema`, because
    a staged report carries no schema version and never will. The refusal
    is correct and this is the design honouring it rather than routing
    around it. The items therefore carry no `delta` and no `class_delta`:
    those are score movements, and no score exists here to move.

    Only the two breach classes block. A work order legitimately proposes
    improvements — an unpaired file, a duplicated concern — and a commit
    is not the place to demand them.

    Added suppressions are appended here because no repository-wide
    builder can produce them: the audit reads whole files, and a marker
    in a whole file is history rather than this change's doing.
    """
    from ._work_order import _items_from_files, _items_from_hotspots, band_of

    items: list[dict[str, Any]] = []
    for entry in _items_from_hotspots(report) + _items_from_files(report):
        weight = entry.pop("weight")
        rationale = entry.pop("rationale", None) or weight.rationale
        items.append({**entry, "rationale": rationale,
                      "band": band_of(weight.risk, weight.effort).value,
                      "risk": weight.risk, "effort": weight.effort,
                      "verification": weight.verification})
    for entry in report["added_suppressions"]:
        items.append({
            "finding_class": SUPPRESSION_CLASS,
            "title": f"{entry['marker']} added in {entry['path']}",
            "path": entry["path"], "line": entry["line"],
            "target": (
                "remove the suppression, or fix the finding it silences; a "
                "marker added alongside a change is not a resolved finding"
            ),
            "rationale": (
                "this project treats a suppression as a finding rather than a "
                "fix, and only a diff can tell a new one from a decision "
                "somebody already made"
            ),
            # Stated here rather than drawn from `CLASS_RISK_EFFORT`,
            # because that table is the *audit's* class registry and the
            # audit can never emit this class: it reads whole files, and
            # only a diff separates a marker somebody just wrote from one
            # that has been there for years. A weight in a table nothing
            # else in the product can produce would be a claim the rubric
            # does not make. The fields are still present, because an
            # agent parsing `findings` must not have to special-case one
            # entry's shape.
            "band": "quick-win", "risk": 4, "effort": 1,
            "verification": "git diff --cached | grep -n <marker>",
            # Above every threshold breach on purpose. A file is 40 lines
            # over its budget; a suppression is the measurement being
            # switched off, and nothing is learned from the run that
            # follows it.
            "severity": 250.0,
        })
    return sorted(items, key=lambda item: -float(item.get("severity") or 0))
