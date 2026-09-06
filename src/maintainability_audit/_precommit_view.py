"""What a blocked commit prints, and what an agent reads instead.

Split from `_precommit` on the same seam `_work_order_view` splits from
`_work_order`: that module decides what blocks, this one decides how it
reads. The split matters here more than usual, because these two
renderings have different audiences and the same content — a person
reading a terminal that has just refused their commit, and an agent
reading JSON that has just refused its commit. Neither is allowed to
learn something the other does not.

Nothing here computes: it receives findings and prints them.
"""
from __future__ import annotations

import json
from typing import Any

#: Said once, in both renderings, and nowhere else. A hook that reports
#: "no findings" without it reads as "this change is fine", when what
#: happened is that no rate was computable — the absence-as-a-pass this
#: project removes everywhere else.
NO_SCORE = "no score: a diff supports no rate"


def render_staged(findings: list[dict[str, Any]], scanned: int) -> list[str]:
    """The lines a blocked commit prints. Empty when nothing blocks.

    Silence on success is the design, not an omission: a hook that
    congratulates the author on every commit is one they learn to skip,
    and a skipped hook constrains nothing.

    Every finding prints a path, a line where one exists, what is wrong,
    and what to do — in that order, because the first thing an author
    needs from a hook is somewhere to click.
    """
    if not findings:
        return []
    files = "file" if scanned == 1 else "files"
    lines = [
        f"maintainability — {scanned} staged {files}, thresholds only",
        f"  ({NO_SCORE})",
        "",
    ]
    for item in findings:
        where = item.get("path") or ""
        line = item.get("line")
        lines.append(f"  {where}:{line}" if line else f"  {where}")
        lines.append(f"    {item.get('title')}")
        lines.append(f"    → {item.get('target')}")
        lines.append("")
    count = len(findings)
    noun = "finding" if count == 1 else "findings"
    lines.append(f"commit blocked · {count} {noun} in what you staged")
    lines.append("fix them, or `git commit --no-verify`")
    return lines


def staged_json(report: dict[str, Any], findings: list[dict[str, Any]]) -> str:
    """The same refusal, shaped for the agent that caused it.

    `scored: false` is a field rather than a comment because a consumer
    that reads `findings` and infers a grade from their absence is the
    failure this whole feature is built to avoid, and prose in a
    docstring does not reach a parser.

    Emitted even when nothing blocks — unlike the text rendering, which
    stays silent. A program asking "what happened" deserves an answer;
    a terminal does not need one.
    """
    return json.dumps(
        {
            "staged": report["scanned"],
            "findings": findings,
            "scored": False,
            "scored_reason": NO_SCORE,
            "blocked": bool(findings),
        },
        indent=2,
        sort_keys=True,
    )
