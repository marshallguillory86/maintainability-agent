"""The instruction describes the questions it is attached to (D192).

`setup_instruction` is prose for the agent relaying the questions. It was
written once and served every stage, so a stage-two reply — the three
labor rates, which exist only because stage one was answered — opened with
"This repository has not been set up", and recited the option list for
`default_format` with no such question anywhere in the reply.

Neither is a dead end, so neither costs an answer. They cost trust: an
instruction that contradicts the payload beside it teaches a reader to
stop reading the instruction, and the instruction is the only thing
telling a host not to invent questions or answer on the user's behalf.

It also never named `setup_answers`. It said "call audit_repository
again" and stopped, which is the sentence that was true and useless
before D189 gave the answers a way in.

Derived from the questions in the reply, so it cannot describe a
different set than the one it ships with.

The first-stage wording is held by
`test_first_stage_setup_wording_holds.py`, which passes at the base and
is kept out of this file so the citations here stay evidence.
"""

from __future__ import annotations

import json

import pytest

from maintainability_audit import _mcp_gate


def _configure(root, **overrides) -> None:
    config = {
        "version": 1,
        "analyzers": {"run": True, "depth": "heavy", "license_policy": "permissive"},
        "presentation": {"format": "chat"},
        "history": {"record": True},
        "test_execution": {"requested": False},
    }
    config.update(overrides)
    (root / "maintainability-agent.json").write_text(json.dumps(config), encoding="utf-8")


def _reply(root, reconfigure=False) -> dict:
    return _mcp_gate._setup_first(root, reconfigure=reconfigure)


def test_a_staged_reply_does_not_claim_setup_never_happened(tmp_path) -> None:
    """The rates exist *because* setup happened. Saying otherwise is false."""
    _configure(tmp_path, economic_context={"version": 1, "requested": True})

    instruction = _reply(tmp_path)["setup_instruction"]

    assert "has not been set up" not in instruction
    assert "part-answered" in instruction


def test_a_staged_reply_does_not_recite_the_presentation_options(tmp_path) -> None:
    """`default_format` is not in a stage-two reply, so its options are noise."""
    _configure(tmp_path, economic_context={"version": 1, "requested": True})

    reply = _reply(tmp_path)
    names = {question["name"] for question in reply["setup_needed"]["questions"]}

    assert "default_format" not in names, "fixture no longer produces a staged reply"
    assert "default_format" not in reply["setup_instruction"]


@pytest.mark.parametrize("overrides,stage", [
    ({}, "first stage"),
    ({"economic_context": {"version": 1, "requested": True}}, "rates"),
    ({"test_execution": {"requested": True}}, "test command"),
])
def test_every_stage_says_how_to_submit_the_answers(tmp_path, overrides, stage) -> None:
    """"Call again" without naming the parameter is the D189 dead end in prose."""
    _configure(tmp_path, **overrides)

    assert "setup_answers" in _reply(tmp_path)["setup_instruction"], (
        f"the {stage} reply does not tell a host how to submit the answers"
    )
