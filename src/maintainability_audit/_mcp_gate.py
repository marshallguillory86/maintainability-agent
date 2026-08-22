"""What the audit answers with when it is not answering with an audit.

Two questions stand between a call and a scan, because they are two
decisions: how this repository is configured (D26), and whether to run
now (D27). Welding them together meant a user answered setup and
thereby launched a scan they had not asked for.

Extracted from ``_mcp_audit`` at this repository's own file-length
gate, and the seam is real: everything here returns a reply that is
deliberately *not* a report, and every one of them states
``audit_ran: false`` rather than leaving a consumer to infer it from a
missing key.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._mcp_setup import setup_pending, setup_questions
from ._user_config import mark_repo_seen
from .config import VERSION, load_config


def _gate(root: Path, config_path: str | None,
          action: str | None) -> dict[str, Any] | None:
    """What to answer instead of auditing, or ``None`` to go ahead.

    Two questions stand between a call and a scan, because they are two
    decisions: how this repository is configured, and whether to run
    now. Welding them together meant a user answered setup and thereby
    launched a scan they had not asked for (D27).

    ``action`` unset never audits — an unconfigured repository gets its
    setup questions, a configured one gets run-or-reconfigure.
    ``"reconfigure"`` reopens setup for a repository that already has
    answers, so changing your mind never requires deleting a file.
    ``"run"`` proceeds.

    Note what ``"run"`` does *not* do: it never overrides the setup
    precondition. An unconfigured repository returns questions whatever
    the action says, because there is nothing to run against yet. Only
    an explicit ``config_path`` bypasses that, and it does so by
    supplying the configuration the precondition is asking for.

    The default differs by door on purpose. The MCP tool passes unset,
    because a person is on the other end and has not been asked; the
    plain function defaults to ``"run"`` so a scripted caller with a
    configured repository gets a report rather than a question it has
    no one to put. An audit corrected an earlier version of this
    paragraph, which claimed the default was how the CLI and the report
    resource skip the gate — neither calls this function at all (D30).
    """
    if config_path is not None:
        return None
    if setup_pending(root):
        return _setup_first(root)
    if action == "reconfigure":
        return _setup_first(root, reconfigure=True)
    return None if action == "run" else _choose_next(root)


def _envelope(root: Path) -> dict[str, Any]:
    """The shell every not-an-audit answer shares.

    `audit_ran` is stated rather than implied, because the failure this
    whole family of gates exists to prevent is an agent reporting a
    number that no audit produced.
    """
    mark_repo_seen(root)
    return {
        "agent": "maintainability-agent",
        "agent_version": VERSION,
        "audit_ran": False,
    }


def _choose_next(root: Path) -> dict[str, Any]:
    """Configured, so ask what to do — never assume the answer is "audit".

    Answering setup does not start an audit, and neither does calling a
    configured repository: the questions configure the agent, running is
    a separate decision, and the choice is offered on every run so a
    user can revisit setup at any point rather than only on first
    contact (D27).
    """
    result = _envelope(root)
    result["choice_needed"] = {
        "name": "next_action",
        "prompt": (
            "This repository is configured. Run the maintainability audit "
            "now, or go back into setup and change the configuration?"
        ),
        "options": ["run", "reconfigure"],
        "default": "run",
    }
    result["choice_instruction"] = (
        "No audit ran and no score exists. Ask the user this question as a "
        "structured choice, offering both options, then call "
        "audit_repository again with action set to their answer: 'run' to "
        "audit, 'reconfigure' to reopen the setup questions. Do not pick "
        "for them and do not report a grade; there is none yet."
    )
    return result


def _setup_first(root: Path, reconfigure: bool = False) -> dict[str, Any]:
    """Questions, and no report, until this repository has been set up.

    Setup is a precondition, not a footnote. The audit used to run on
    built-in defaults whenever a host could not be elicited and hand its
    questions back beside a finished report — which meant a first-time
    user received a complete letter grade computed with the analyzer
    pool off, while the question that turns the pool on rode along
    unasked. One table cell reading "fallback tier" was the whole
    disclosure, and a field run produced exactly the predicted outcome:
    a 3.9/C that was not the product's answer to anything.

    A grade nobody can act on is worse than no grade, so none is
    produced. The caller gets the questions, asks them, and calls again
    with the answers — one extra round trip, and the report it then
    returns is the product's actual reading.

    Elicitation is unaffected: a host that can be elicited is asked
    before the audit and never reaches here. This is only the path where
    nobody could be asked, which used to audit anyway.

    ``reconfigure`` serves the same questions to a repository that is
    already configured, because a user revisiting their answers is not a
    first run and must not have to delete a file to be asked again.
    """
    from ._first_run import PRESENTATIONS

    result = _envelope(root)
    result["setup_needed"] = {"questions": setup_questions(load_config(None))}
    opening = (
        "The user asked to change this repository's configuration."
        if reconfigure else
        "This repository has not been set up."
    )
    result["setup_instruction"] = (
        f"{opening} No audit ran and no score was produced. Ask the user "
        "every question in setup_needed, offering exactly the options each "
        f"one lists — default_format offers {', '.join(PRESENTATIONS)} — "
        "and then call audit_repository again. Answering setup does not "
        "start an audit: the next call returns the run-or-reconfigure "
        "choice, and the user decides when to run. Do not substitute "
        "questions of your own, do not answer on the user's behalf, and do "
        "not report a grade: there is none to report yet."
    )
    return result
