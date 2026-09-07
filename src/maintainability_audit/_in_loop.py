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

import re
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


#: Which budget grades which kind. A class is a container, so the
#: per-function line budget is the wrong yardstick for it — the config
#: schema has said so since `max_class_lines` shipped (300 against 80),
#: and the declaration scanner already grades it that way. Only this
#: module did not, so an ordinary class reported a negative remainder
#: against a budget it was nowhere near (Gemini's field check).
_BUDGETS = {
    "class": ("max_class_lines", "warn_class_lines"),
}
_DEFAULT_BUDGET = ("max_function_lines", "warn_function_lines")


def _budget_for(kind: str, thresholds: dict[str, int]) -> tuple[int, int]:
    limit_key, warn_key = _BUDGETS.get(kind, _DEFAULT_BUDGET)
    # A config predating `max_class_lines` falls back to the function
    # budget rather than raising: an old config should measure something
    # defensible, not refuse to answer.
    limit = thresholds.get(limit_key, thresholds["max_function_lines"])
    warn = thresholds.get(warn_key, thresholds["warn_function_lines"])
    return limit, warn


def _headroom(metric: Any, thresholds: dict[str, int]) -> dict[str, Any]:
    """How much of its own budget a declaration has left.

    Only ever called for declarations that are *inside* their budget, so
    `remaining` is never negative. It used to be: a breach appeared here
    as "-31 lines left" beside an exit code of 0, which is not a warning
    but a contradiction the reader has to resolve. A negative remainder
    means a breach, and breaches are findings.
    """
    limit, warn = _budget_for(metric.kind, thresholds)
    return {
        "name": metric.name,
        "kind": metric.kind,
        "line": metric.start_line,
        "lines": metric.lines,
        "limit": limit,
        "remaining": limit - metric.lines,
        "band": _band(metric.lines, warn, limit),
    }


def _file_headroom(lines: int, thresholds: dict[str, int]) -> dict[str, Any]:
    limit = thresholds["max_file_lines"]
    return {
        "lines": lines,
        "limit": limit,
        "remaining": limit - lines,
        "band": file_status(lines, thresholds),
    }


#: The budgets a declaration can breach, in the order a reader wants to
#: hear about them. Length first because it is the one an author can act
#: on without rereading the function.
_DECLARATION_BUDGETS = (
    ("lines", "lines", None),
    ("complexity", "complexity", "max_complexity"),
)


def _breaches_for(metric: Any, thresholds: dict[str, int]) -> list[dict[str, Any]]:
    """Every budget this declaration is actually over, with by how much.

    Reported per budget rather than as one number, because the first
    version subtracted `max_function_lines` from the line count whatever
    had failed. A short, complex function then rendered as "-71 over" —
    a negative overage of a budget it was comfortably inside, printed for
    a breach that was real (Grok's audit). A figure has to be about the
    thing that failed or it is worse than no figure.
    """
    lines_limit, _ = _budget_for(metric.kind, thresholds)
    breaches = []
    for label, attribute, key in _DECLARATION_BUDGETS:
        # `None` means "the length budget for this kind", which is the
        # class budget for a class and the function budget otherwise.
        limit = lines_limit if key is None else thresholds[key]
        value = getattr(metric, attribute)
        if value > limit:
            breaches.append({"budget": label, "value": value, "limit": limit,
                             "over_by": value - limit})
    return breaches


def _declaration_findings(
    path: str, metrics: list[Any], thresholds: dict[str, int]
) -> list[dict[str, Any]]:
    """Breaches only, worded as the full audit words them.

    The remedy text matches `_work_order`'s oversized-declaration item
    deliberately: an author who meets this mid-edit and the same author
    who meets the gate later should not be told two different things
    about one budget.
    """
    findings = []
    for metric in metrics:
        if metric.status != "fail":
            continue
        breaches = _breaches_for(metric, thresholds)
        # A declaration can be graded `fail` by a rule these two budgets
        # do not name. Reporting no breach then would print a finding
        # with nothing to act on, so the length budget stands as the
        # stated one and the figure remains about it.
        if not breaches:
            fallback, _ = _budget_for(metric.kind, thresholds)
            breaches = [{"budget": "lines", "value": metric.lines,
                         "limit": fallback,
                         "over_by": metric.lines - fallback}]
        findings.append({
            "finding_class": "oversized-declaration",
            "name": metric.name,
            "path": path,
            "line": metric.start_line,
            "lines": metric.lines,
            "breaches": breaches,
            # The first breached budget, for a consumer that wants one
            # number. Never negative: it names a budget that failed.
            "breached": breaches[0]["budget"],
            "over_by": breaches[0]["over_by"],
            "target": (
                f"reduce below the configured limits (currently {metric.lines} "
                f"lines against {_budget_for(metric.kind, thresholds)[0]}, "
                f"complexity {metric.complexity} against "
                f"{thresholds['max_complexity']})"
            ),
        })
    return findings


#: Languages whose parser can refuse content outright, and the check
#: that asks. Only Python today: the brace scanners do not fail, they
#: find nothing, and reporting "unparsed" for them would be a guess.
#: A unified-diff hunk header, as `diff -u` and git emit it. The counts
#: are optional — a single-line hunk is written `@@ -1 +1 @@`.
_HUNK_HEADER = re.compile(r"^@@ -\d+(,\d+)? \+\d+(,\d+)? @@")


def _is_unified_diff(text: str) -> bool:
    """Whether this is a diff rather than the content of a file.

    Piping a diff instead of file content is the most likely mistake at
    this door, and it was the quietest: the content refused to parse,
    nothing was found, and `declarations_read` still said the file had
    been read. Exit 0, no output, "clean".

    Gemini found that on Python and the fix taught `_parses` to use
    `ast.parse`, which refuses a diff — so the sentence in the docs
    ("it will say it could not parse") was true of Python and of nothing
    else. Every other suffix returned `True` before reaching any check
    (D133).

    Detected by **shape**, not by a substring: the `---`/`+++` header
    pair and a hunk header. A string literal containing `@@ -1,3 +1,4 @@`
    is somebody writing about a diff, which is the mention-versus-
    assertion distinction this project has already met in suppression
    markers, escape phrases and risk patterns.

    The format is specified rather than guessed, so this holds for every
    language equally instead of for the one with a parser in the standard
    library.
    """
    lines = text.splitlines()
    has_old = any(line.startswith("--- ") for line in lines)
    has_new = any(line.startswith("+++ ") for line in lines)
    has_hunk = any(_HUNK_HEADER.match(line) for line in lines)
    return has_hunk and has_old and has_new


def _parses(path: str, text: str) -> bool:
    """Whether the content is what its extension claims to be.

    An agent piping a unified diff instead of file content is the most
    likely mistake at this door, and it used to be the quietest: the
    parser refused the diff, nothing was found, and `declarations_read`
    still said the file had been read. Exit 0, no output, "clean" — which
    is absence read as a pass, arriving through the exact feature whose
    docstring promises to refuse it (Gemini's field check).
    """
    if _is_unified_diff(text):
        return False
    if Path(path).suffix != ".py":
        # No parser for the brace languages, and zero declarations is not
        # evidence of one being needed: plenty of valid files mint none,
        # and marking those "unparsed" would trade a quiet pass for a
        # loud wrong answer. What is checked for every language is the
        # diff above, which is the mistake that actually happens.
        return True
    import ast

    try:
        ast.parse(text)
    except (SyntaxError, ValueError):
        return False
    return True


def _note_for(suffix: str, parsed: bool, readable: bool) -> str:
    """What was not looked at, said plainly, or "" when everything was.

    Two different silences need two different sentences. A language with
    no scanner was never going to be read; content that refused to parse
    was supposed to be and was not. Both are reported because absence
    read as a pass is the defect this whole door exists to refuse.
    """
    if not parsed:
        return (f"{suffix or 'this file'} has no declaration scanner, so "
                "nothing was read about its declarations — that is not the "
                "same as finding nothing")
    if not readable:
        return (f"this content did not parse as {suffix}, so nothing was read "
                "about its declarations — check you passed file content rather "
                "than a diff or a fragment")
    return ""


def _file_finding(path: str, room: dict[str, Any]) -> list[dict[str, Any]]:
    """The file-length breach, in the shape the declaration breaches use."""
    if room["band"] != "fail":
        return []
    return [{
        "finding_class": "oversized-file",
        "name": path, "path": path, "line": None,
        "lines": room["lines"], "over_by": -room["remaining"],
        "breached": "lines",
        "breaches": [{"budget": "lines", "value": room["lines"],
                      "limit": room["limit"], "over_by": -room["remaining"]}],
        "target": (
            f"split below the configured file-length limit (currently "
            f"{room['lines']} lines against {room['limit']})"
        ),
    }]


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
    readable = _parses(path, text) if parsed else False

    metrics: list[Any] = []
    if parsed and readable:
        # `Path(path)` is passed for its suffix and its name only; the
        # content comes from `lines`, which is the argument. Nothing here
        # touches the filesystem, so a path that does not exist is fine.
        metrics = detect_functions(Path(path).parent, Path(path), lines, thresholds)

    file_room = _file_headroom(len(lines), thresholds)
    return {
        "path": path,
        "declarations_read": parsed and readable,
        "note": _note_for(suffix, parsed, readable),
        "file": file_room,
        "findings": (_declaration_findings(path, metrics, thresholds)
                     + _file_finding(path, file_room)),
        # Only declarations inside their budget. A breach is a finding,
        # never a headroom entry with a negative number in it.
        "headroom": [
            entry for entry in (
                _headroom(metric, thresholds)
                for metric in metrics if metric.status != "fail"
            ) if entry["remaining"] >= 0
        ],
        "scored": False,
        "scored_reason": NO_SCORE,
    }
