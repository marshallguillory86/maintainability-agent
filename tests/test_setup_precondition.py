"""D26/D27: nothing is audited until the user has been asked twice.

Split out of ``test_first_run_elicitation.py`` when that file crossed
this repository's own file-length gate. Elicitation is a mechanism —
how a question reaches a person. These are the contract: that an
unconfigured repository is asked rather than audited, that answering
configures without launching a scan, and that the way back into setup
stays open on every run.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from test_first_run_elicitation import _accepted_content, _repo

from maintainability_audit._mcp_setup import setup_questions
from maintainability_audit._user_config import repo_first_run
from maintainability_audit.config import CONFIG_FILENAME, load_config
from maintainability_audit.mcp_server import audit_repository, create_server


def _assert_setup_needed(result: dict) -> None:
    """Questions, and deliberately nothing to mistake for an answer (D26).

    This used to assert the opposite shape: a full report, graded, with
    the questions filed beside it. That is what shipped, and what a
    first-time user got was a letter grade computed with the analyzer
    pool off while the question that turns the pool on rode along
    unasked. Setup is a precondition now, so a pending repository
    returns questions and no report at all.
    """
    expected = setup_questions(load_config(None))
    assert result["setup_needed"]["questions"] == expected
    assert result["audit_ran"] is False
    for absent in ("report", "report_markdown", "report_html", "score",
                   "gate_passed", "analyzers_run"):
        assert absent not in result, (
            f"a repository still awaiting setup returned {absent!r}; "
            "there is no audit result to report yet"
        )
    assert "setup_instruction" in result, (
        "the caller is handed questions with no instruction to ask them"
    )


def test_declined_or_unsupported_elicitation_returns_questions_not_an_audit(
    tmp_path: Path,
) -> None:
    from mcp import Client, types

    declined_root = _repo(tmp_path / "declined")
    unsupported_root = _repo(tmp_path / "unsupported")
    calls: list[Any] = []

    async def decline(_context: Any, params: Any) -> Any:
        calls.append(params)
        return types.ElicitResult(action="decline")

    async def exercise() -> tuple[dict, dict]:
        server = create_server(roots=(tmp_path.resolve(),))
        async with Client(server, elicitation_callback=decline) as client:
            declined = await client.call_tool(
                "audit_repository",
                {"repository_root": str(declined_root), "format": "json"},
            )
            assert not declined.is_error
        async with Client(server) as client:
            unsupported = await client.call_tool(
                "audit_repository",
                {"repository_root": str(unsupported_root), "format": "json"},
            )
            assert not unsupported.is_error
        return declined.structured_content, unsupported.structured_content

    declined, unsupported = asyncio.run(exercise())

    assert len(calls) == 1
    _assert_setup_needed(declined)
    _assert_setup_needed(unsupported)
    assert not (declined_root / CONFIG_FILENAME).exists()
    assert not (unsupported_root / CONFIG_FILENAME).exists()


@pytest.mark.parametrize("readme", [True, False])
def test_a_completed_mcp_audit_marks_seen_even_when_a_gate_fails(
    tmp_path: Path,
    readme: bool,
) -> None:
    root = _repo(tmp_path, readme=readme)
    # Configured, because this test is about a *completed* audit: an
    # unconfigured repository returns setup questions and never reaches
    # a gate to pass or fail (D26).
    (root / CONFIG_FILENAME).write_text(
        json.dumps({"version": 1, "analyzers": {"run": False}}), encoding="utf-8",
    )
    assert repo_first_run(root) is True

    result = audit_repository(str(root), roots=(tmp_path.resolve(),))

    assert result["gate_passed"] is readme
    assert repo_first_run(root) is False


def test_setup_is_a_precondition_and_answering_it_yields_the_real_report(
    tmp_path: Path,
) -> None:
    """D26: ask first, audit second — the operator's ruling, end to end.

    Before this, an unconfigured repository was audited on built-in
    defaults and its questions were filed beside a finished report. A
    first-time user therefore received a complete letter grade computed
    with the analyzer pool *off*, while the question that turns the pool
    on rode along unasked, disclosed by one table cell reading "fallback
    tier". A field run produced exactly that: a 3.9/C that was not the
    product's answer to anything.

    The loop is asserted whole, because either half alone can pass while
    the product is useless: refusing to audit is only correct if
    answering actually unblocks it, and the answers must reach the
    report — here the html presentation the user picked.
    """
    from maintainability_audit._mcp_setup import apply_answers

    root = _repo(tmp_path)
    roots = (tmp_path.resolve(),)

    pending = audit_repository(str(root), roots=roots)
    assert pending["audit_ran"] is False
    assert "report" not in pending
    names = [question["name"] for question in pending["setup_needed"]["questions"]]
    assert "default_format" in names and "run_pool" in names

    # Repeating the call must not wear the precondition down.
    assert audit_repository(str(root), roots=roots)["audit_ran"] is False

    apply_answers(root, {
        "run_pool": "no",  # no pool: this test is about the gate, not tools
        "depth": "baseline",
        "license_policy": "permissive",
        "economics": "skip",
        "default_format": "html",
        "record_scan_history": "no",
    })

    # Configured now — and still not audited. Running is its own
    # decision, offered alongside the way back into setup, on this run
    # and every later one (D27).
    choice = audit_repository(str(root), action=None, roots=roots)
    assert choice["audit_ran"] is False
    assert "report" not in choice
    assert choice["choice_needed"]["options"] == ["run", "reconfigure"]

    # And the way back in works without deleting a config file.
    again = audit_repository(str(root), action="reconfigure", roots=roots)
    assert again["audit_ran"] is False
    assert [q["name"] for q in again["setup_needed"]["questions"]] == names

    audited = audit_repository(str(root), action="run", roots=roots)
    assert audited["audit_ran"] is True
    assert "setup_needed" not in audited, "answered setup still asks"
    assert audited["format"] == "html", "the chosen presentation was not honoured"
    assert audited["report_html"], "html was chosen and no html came back"
