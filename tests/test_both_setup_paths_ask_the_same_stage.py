"""The elicited host and the data host are asked the same thing (D190).

Setup is staged. Answering stage one can open stage two: saying `include`
to the economic scenario opens the three labor rates, and saying `yes` to
running the suite opens the test command. Those second stages exist so
that nobody is asked for a rate they do not want to give.

`setup_schema` knew about the stages. The gate that returns questions as
data did not — it called `setup_questions` directly, with no root, so it
could only ever produce stage one. A host that could not be elicited
answered stage one, which opened stage two, and was then handed stage one
again. Forever, with the second stage unreachable.

This is D189's asymmetry one layer in. There the answers had nowhere to
go; here they went somewhere and the next question never came. Both are
the same shape: the elicited path knew something the data path did not.

`staged_questions` is now the one stage decision and both paths render
it, so the two cannot hold different opinions about what a repository
still needs. These tests hold that — for every stage, not just the one
that broke.
"""

from __future__ import annotations

import json

import pytest

from maintainability_audit._mcp_setup import setup_schema, staged_questions


def _schema_names(root) -> set[str]:
    return set(getattr(setup_schema(root), "model_fields", {}))


def _data_names(root) -> set[str]:
    return {question["name"] for question in staged_questions(root)}


def _configure(root, **overrides) -> None:
    """Write a repository config in the state under test."""
    config = {
        "version": 1,
        "analyzers": {"run": True, "depth": "heavy", "license_policy": "permissive"},
        "presentation": {"format": "chat"},
        "history": {"record": True},
        "test_execution": {"requested": False},
    }
    config.update(overrides)
    (root / "maintainability-agent.json").write_text(
        json.dumps(config), encoding="utf-8"
    )


# --- the gate: the two renderings never disagree ---------------------------


@pytest.mark.parametrize(
    "state,overrides",
    [
        ("economics opted in", {"economic_context": {"version": 1, "requested": True}}),
        ("suite opted in", {"test_execution": {"requested": True}}),
        ("neither", {}),
    ],
)
def test_both_paths_offer_the_same_questions(tmp_path, state, overrides) -> None:
    """One stage decision, two renderings — never two opinions.

    Parametrised over the states that stage, because the bug was not "the
    data path is broken" but "only one of them knows about stages", and a
    single-state test would have passed against the broken code in two of
    these three.
    """
    _configure(tmp_path, **overrides)

    assert _data_names(tmp_path) == _schema_names(tmp_path), (
        f"with {state}, the host that reads questions as data is offered a "
        "different set than the host that gets elicited"
    )


def test_opting_into_economics_moves_the_data_path_to_the_rates(tmp_path) -> None:
    """The failure exactly: answered, advanced, and still shown stage one.

    Asserted positively rather than as agreement with the schema, so this
    still fails if both paths regress together.
    """
    _configure(tmp_path, economic_context={"version": 1, "requested": True})

    assert _data_names(tmp_path) == {"labor_low", "labor_base", "labor_high"}


def test_a_repository_needing_nothing_staged_is_asked_the_first_stage(tmp_path) -> None:
    """Stage one is still stage one; the fix must not skip it."""
    _configure(tmp_path)

    names = _data_names(tmp_path)

    assert "run_pool" in names and "depth" in names
    assert "labor_low" not in names, "the rates are asked only of someone who opted in"


def test_the_gate_reply_carries_the_staged_questions(tmp_path) -> None:
    """The reply a host actually receives, not just the helper behind it."""
    from maintainability_audit import _mcp_gate

    _configure(tmp_path, economic_context={"version": 1, "requested": True})

    reply = _mcp_gate._setup_first(tmp_path, reconfigure=False)
    offered = {question["name"] for question in reply["setup_needed"]["questions"]}

    assert offered == {"labor_low", "labor_base", "labor_high"}, (
        "the gate returns stage one to a host whose repository is in stage two"
    )


def test_the_staged_questions_are_answerable(tmp_path) -> None:
    """Every staged question must be submittable, or D189 returns per stage.

    A stage that can be reached and not answered is the same dead end,
    moved.
    """
    from maintainability_audit._mcp_setup import submittable_answer_names

    for overrides in (
        {"economic_context": {"version": 1, "requested": True}},
        {"test_execution": {"requested": True}},
        {},
    ):
        _configure(tmp_path, **overrides)
        unanswerable = _data_names(tmp_path) - submittable_answer_names()
        assert not unanswerable, (
            f"staged questions with no way to submit an answer: {sorted(unanswerable)}"
        )
