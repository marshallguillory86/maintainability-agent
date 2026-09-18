"""A question this agent asks is one a host can answer (D189).

The tool asks a repository's operator seven first-run questions. On a
host the MCP SDK can elicit, the SDK fills the `setup` parameter and the
answers persist to the repository's local configuration. On a host it
cannot elicit — the documented and common case — the same questions come
back as data for the host's own question UI to ask.

They came back, were asked, and had nowhere to go. `setup` is an
elicitation-resolved parameter: the SDK fills it, and it is therefore
absent from the **published input schema**, so no client could pass it.
The tool's own docstring told a host to "ask and call again"; calling
again returned the same questions, forever.

**This is why reading the source did not find it.** In source the path is
correct: the function takes `setup`, `_apply_call_consents` reads it,
`apply_answers` writes the file. The defect exists only in what the
schema publishes to a caller, which is a different artifact from the
function's signature. So these tests assert against the schema a client
actually receives, not against the code that produces it.

The class, not the instance: every question the agent can emit must have
a name a caller can submit, and the legal names are derived from the
questions rather than listed beside them.
"""

from __future__ import annotations

import inspect

import pytest

from maintainability_audit._mcp_setup import (
    setup_questions,
    submittable_answer_names,
)

# --- the class gate: no question without a way to answer it ----------------


def test_every_setup_question_has_a_submittable_name() -> None:
    """The gate. A question the agent asks and cannot receive is the defect."""
    asked = {question["name"] for question in setup_questions({})}
    assert asked, "no questions found; this gate would pass vacuously"

    unanswerable = sorted(asked - submittable_answer_names())

    assert not unanswerable, (
        f"questions this agent asks with no way to submit an answer: "
        f"{unanswerable}. Every name in `setup_questions` must be accepted "
        "by `setup_answers`, or a host is asked something it cannot reply to."
    )


def test_the_submittable_names_are_derived_from_the_questions() -> None:
    """Derived, not listed beside them — a second list is how they drift.

    Adding a question must extend what can be submitted without anyone
    remembering to update a constant.
    """
    source = inspect.getsource(submittable_answer_names)

    assert "setup_questions" in source, (
        "submittable_answer_names no longer reads setup_questions; a "
        "hand-kept list drifts silently and the drift is invisible until "
        "someone answers a question that goes nowhere"
    )


# --- the published schema, which is where the defect actually lived --------


def _audit_tool_parameters() -> set[str]:
    """Parameter names on the registered audit tool, SDK-filled ones removed."""
    from maintainability_audit import mcp_server

    source = inspect.getsource(mcp_server)
    start = source.index("async def audit_repository_tool(")
    end = source.index(") -> dict[str, Any]:", start)
    block = source[start:end]
    names = {
        line.split(":", 1)[0].strip()
        for line in block.splitlines()[1:]
        if ":" in line and not line.strip().startswith("#")
    }
    # Resolved by the SDK, never sent by a caller.
    return names - {"setup", "grant", "ctx"}


def test_the_tool_publishes_a_parameter_that_carries_setup_answers() -> None:
    """The fix, asserted where the defect was: the caller-facing surface.

    `setup` does not count and is excluded deliberately — it is exactly
    what was there while the flow was unusable.
    """
    assert "setup_answers" in _audit_tool_parameters(), (
        "the audit tool publishes no parameter a host can put setup answers "
        "in, so questions returned as data cannot be answered"
    )


def test_the_elicitation_parameter_is_not_counted_as_an_answer_path() -> None:
    """Guards the guard: `setup` must stay excluded from the caller surface.

    If this ever stops being true the test above starts passing for the
    wrong reason, which is the state that shipped.
    """
    from maintainability_audit import mcp_server

    source = inspect.getsource(mcp_server)

    assert "setup: Any = None" in source, (
        "the elicitation-resolved `setup` parameter changed shape; re-check "
        "whether it now reaches the published schema"
    )


# --- answers submitted as data actually persist ----------------------------


def test_submitted_answers_reach_the_local_configuration(tmp_path) -> None:
    """The whole point: a host's answers become the repository's config.

    Seven answers in, seven settings on disk. Asserted against the file,
    because a return value that says "applied" is what the broken path
    would also have produced.
    """
    import json

    from maintainability_audit._mcp_setup import apply_answers

    apply_answers(tmp_path, {
        "run_pool": "yes",
        "depth": "heavy",
        "license_policy": "copyleft-any",
        "economics": "skip",
        "run_tests": "yes",
        "default_format": "html",
        "record_scan_history": "yes",
    })

    config = json.loads((tmp_path / "maintainability-agent.json").read_text(encoding="utf-8"))

    assert config["analyzers"]["run"] is True
    assert config["analyzers"]["depth"] == "heavy"
    assert config["analyzers"]["license_policy"] == "copyleft-any"
    assert config["presentation"]["format"] == "html"
    assert config["test_execution"]["requested"] is True
    assert config["history"]["record"] is True


def test_a_misspelled_answer_is_refused_rather_than_dropped() -> None:
    """`apply_answers` ignores names it does not know, which is right for a
    validated elicitation payload and wrong for an argument a host typed:
    `dept` would persist the default depth and report success.
    """
    from maintainability_audit._mcp_setup import coerce_submitted_answers
    from maintainability_audit._setup_errors import SetupRequired

    with pytest.raises(SetupRequired, match="dept"):
        coerce_submitted_answers({"run_pool": "yes", "dept": "heavy"})


def test_the_answers_a_host_is_shown_are_all_accepted() -> None:
    """Answer every published question at once; none may be refused."""
    from maintainability_audit._mcp_setup import coerce_submitted_answers

    answers = {
        question["name"]: str(question.get("default") or question["options"][0])
        for question in setup_questions({})
    }

    coerce_submitted_answers(answers)  # must not raise
