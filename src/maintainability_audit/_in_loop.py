"""What a budget says about content that has not been written yet.

The roadmap names this project end-of-loop heavy: *"strong where it is
cheapest to be strong — a CI gate after the work is done — and thin
during the loop, where a constraint is worth far more because it prevents
rather than rejects."* `--staged` (2.9.0) moved one step earlier, to the
commit. This is the step before that, and it is the one the sentence is
actually about.

**It answers about content, not about a repository.** No git, no index,
no scan, no working tree. An agent mid-edit is not at a commit boundary,
and a check that made it reach one would be a check it calls once and
then stops calling.

**The content it is given is authoritative.** It never opens the path.
Reading the file would answer about the version already on disk — which
is the pre-commit bug (`_precommit`: read the index, not the tree) one
step earlier in the loop, and the same mistake.

**Headroom is the output that matters, not the verdict.** A gate says no
when it is already too late to be cheap. "Nine of ten lines, one left" is
usable while the author is still writing, and that difference is the
whole reason this exists beside `--staged` rather than inside it.

**It never scores.** One file has no population — the same refusal
`_precommit` makes, for the same reason, and stated in the result rather
than left to be inferred from a missing key.

**It says when it did not look.** A language with no declaration scanner
produces no findings, which is true and useless. Reporting that as clean
would be absence read as a pass, which is the defect this project keeps
finding in itself.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .declarations import DECLARATION_SUFFIXES, detect_functions
from .metrics import file_status

#: Said in the result rather than left to inference. A caller that reads
#: no score and concludes a good one is the failure the evidence model
#: exists to prevent, and a missing key invites exactly that.
NO_SCORE = "no score: one file has no population to draw a rate from"


def _band(value: int, warn: int, limit: int) -> str:
    if value > limit:
        return "fail"
    return "warn" if value > warn else "ok"


def _headroom(name: str, lines: int, thresholds: dict[str, int],
              start_line: int | None = None) -> dict[str, Any]:
    """How much of a budget is left, and which band that puts it in.

    `remaining` can go negative, and is left that way on purpose: "three
    lines over" is a more useful thing to hand an author mid-edit than a
    floor at zero, which would make every breach look identical.
    """
    limit = thresholds["max_function_lines"]
    entry = {
        "name": name,
        "lines": lines,
        "limit": limit,
        "remaining": limit - lines,
        "band": _band(lines, thresholds["warn_function_lines"], limit),
    }
    if start_line is not None:
        entry["line"] = start_line
    return entry


def _file_headroom(lines: int, thresholds: dict[str, int]) -> dict[str, Any]:
    limit = thresholds["max_file_lines"]
    return {
        "lines": lines,
        "limit": limit,
        "remaining": limit - lines,
        "band": file_status(lines, thresholds),
    }


def _declaration_findings(
    path: str, metrics: list[Any], thresholds: dict[str, int]
) -> list[dict[str, Any]]:
    """Breaches only, worded as the full audit words them.

    The remedy text matches `_work_order`'s oversized-declaration item
    deliberately: an author who meets this mid-edit and the same author
    who meets the gate later should not be told two different things
    about one budget.
    """
    limit = thresholds["max_function_lines"]
    return [
        {
            "finding_class": "oversized-declaration",
            "name": metric.name,
            "path": path,
            "line": metric.start_line,
            "lines": metric.lines,
            "over_by": metric.lines - limit,
            "target": (
                f"reduce below the configured limits (currently {metric.lines} "
                f"lines against {limit}, complexity {metric.complexity})"
            ),
        }
        for metric in metrics if metric.status == "fail"
    ]


def check_content(path: str, text: str, config: dict[str, Any]) -> dict[str, Any]:
    """Whether this content fits its budgets, and how much room is left.

    `path` names the content — it decides the language and appears in the
    output — and is never opened. Callers pass a path that may not exist
    yet, which is the ordinary case for an agent about to write a file.
    """
    thresholds = config["thresholds"]
    suffix = Path(path).suffix
    lines = text.splitlines()
    parsed = suffix in DECLARATION_SUFFIXES

    metrics: list[Any] = []
    if parsed:
        # `Path(path)` is passed for its suffix and its name only; the
        # content comes from `lines`, which is the argument. Nothing here
        # touches the filesystem, so a path that does not exist is fine.
        metrics = detect_functions(Path(path).parent, Path(path), lines, thresholds)

    note = "" if parsed else (
        f"{suffix or 'this file'} has no declaration scanner, so nothing was "
        "read about its declarations — that is not the same as finding nothing"
    )

    file_room = _file_headroom(len(lines), thresholds)
    findings = _declaration_findings(path, metrics, thresholds)
    if file_room["band"] == "fail":
        findings.append({
            "finding_class": "oversized-file",
            "name": path,
            "path": path,
            "line": None,
            "lines": len(lines),
            "over_by": -file_room["remaining"],
            "target": (
                f"split below the configured file-length limit "
                f"(currently {len(lines)} lines against {file_room['limit']})"
            ),
        })

    return {
        "path": path,
        "declarations_read": parsed,
        "note": note,
        "file": file_room,
        "findings": findings,
        # Every declaration that is *not* a breach, with what is left of
        # its budget. The breaches are in `findings`; this is the half a
        # gate cannot give you, because a gate only speaks when it is
        # already too late.
        "headroom": [
            _headroom(metric.name, metric.lines, thresholds, metric.start_line)
            for metric in metrics if metric.status != "fail"
        ],
        "scored": False,
        "scored_reason": NO_SCORE,
    }
