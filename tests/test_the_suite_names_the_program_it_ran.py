"""The audit says which program ran, not only which was configured (D196).

`locate` searches the agent's own script directory before `PATH`, so a
package in a virtualenv finds the analyzers installed beside it (D142).
The consequence is that the same configured name resolves to different
programs depending on which interpreter is running the agent — and the
audit reported only the name it was handed.

Observed: the MCP server was a venv console script invoked by a *foreign*
interpreter, so `sys.executable` was that interpreter and `locate("pytest")`
returned a different environment's pytest. It could not import the project,
the suite did not run, and `test_effectiveness` was `null`. The same
configuration through the CLI resolved the venv's pytest, ran 2,908 tests
and measured 96% coverage.

Two surfaces, one config, opposite answers, and nothing in either result
saying why. `command` is what the person chose; `resolved_program` is what
the host executed, and a reader comparing two runs can now see it in one
look instead of six probes.

This is D194's shape: the tool substituted something correctly and by
design, and did not say what it substituted.
"""

from __future__ import annotations

from test_first_run_prompt import _repo

from maintainability_audit._evidence_view import test_suite_lines as suite_lines
from maintainability_audit._runner import Invocation, ToolResult, run
from maintainability_audit.config import load_config
from maintainability_audit.renderers import render_html, render_markdown
from maintainability_audit.report import build_report


def test_a_run_reports_the_program_it_resolved() -> None:
    """An absolute path, not the bare name the caller passed."""
    result = run("probe", Invocation(argv=("pytest", "--version"),
                                     findings_exit_codes=(0, 1)))

    assert result.resolved_program is not None
    assert result.resolved_program.endswith("pytest")
    assert result.resolved_program != "pytest", (
        "the bare name is what was configured; this field exists to say what ran"
    )


def test_an_unresolvable_program_is_reported_as_given() -> None:
    """A name nothing resolves still names what was attempted.

    `locate` returns None and the runner execs the bare name, which fails.
    Reporting the name is honest: it is what the host tried.
    """
    result = run("probe", Invocation(argv=("definitely-not-a-real-tool-xyz",),
                                     findings_exit_codes=(0,)))

    assert result.resolved_program == "definitely-not-a-real-tool-xyz"


def test_module_style_pytest_names_the_resolved_interpreter(
    monkeypatch,
) -> None:
    """``python3 -m pytest`` executes the located argv[0], never pytest.

    Covers existing behaviour: D196 already resolved argv[0], so this
    passes at that commit. It is kept because D199 changed what the skins
    print about the resolved program, and the module-style command is the
    case where the program and the command differ most — the one a
    renderer is likeliest to get wrong.
    """
    monkeypatch.setattr(
        "maintainability_audit._runner.locate", lambda _program: "/opt/venv/bin/python3"
    )

    result = run(
        "probe", Invocation(argv=("python3", "-m", "pytest"), findings_exit_codes=(0,))
    )

    assert result.resolved_program == "/opt/venv/bin/python3"


def test_the_field_defaults_to_none_for_results_that_never_executed() -> None:
    """A result built without a run has nothing to report, and says None
    rather than inventing a path."""
    assert ToolResult(slug="x", outcome=run.__globals__["Outcome"].NOT_INSTALLED
                      ).resolved_program is None


# --- the suite result carries it ------------------------------------------


def _suite(root, command: list[str] | None):
    """Run the test-execution path with `command` as the consented one."""
    from maintainability_audit import _test_execution

    answers = {"test_execution": {"requested": True}}
    originals = (
        _test_execution.user_config_answers,
        _test_execution.opted_in_command,
        _test_execution.suite_opted_in,
    )
    _test_execution.user_config_answers = lambda: answers
    _test_execution.opted_in_command = lambda: command or []
    # The opt-in gate reads the merged config; this exercises the path
    # *after* consent, which is where the program is resolved.
    _test_execution.suite_opted_in = lambda _config: True
    try:
        return _test_execution.run_test_suite(root, {})
    finally:
        (_test_execution.user_config_answers,
         _test_execution.opted_in_command,
         _test_execution.suite_opted_in) = originals


def test_the_suite_result_names_the_program(tmp_path) -> None:
    """The key a reader compares across two surfaces."""
    result = _suite(tmp_path, ["pytest", "--version"])

    assert result["command"] == ["pytest", "--version"]
    assert result["resolved_program"].endswith("pytest")


def test_a_suite_that_never_ran_still_carries_the_key(tmp_path) -> None:
    """Absent is worse than None: a consumer should not have to guess
    whether the field is missing or the program unresolved."""
    result = _suite(tmp_path, None)

    assert "resolved_program" in result
    assert result["resolved_program"] is None


def test_every_test_suite_skin_names_the_resolved_program_not_just_command(
    tmp_path,
) -> None:
    """D196: the configured command and executable that ran are distinct.

    ``python3 -m pytest`` resolves its program at argv[0].  A renderer that
    merely joins ``command`` says only what the operator configured, which is
    the instance D196 leaves open.  The population is the complete Markdown,
    HTML, and bounded-chat skins consuming these production sentences.
    """
    root = _repo(tmp_path)
    report = build_report(root, load_config(None))
    suite = {
        "command": ["python3", "-m", "pytest"],
        "resolved_program": "/opt/venv/bin/python3",
        "ran": True,
        "exit_code": 0,
        "passed": True,
        "detail": "",
        "coverage_percent": None,
    }
    report["test_suite"] = suite
    sentences = suite_lines(suite)
    skins = {
        "complete Markdown": render_markdown(report),
        "HTML": render_html(report, []),
        "bounded chat": render_markdown(report, complete=False),
    }

    assert skins, "the derived test-suite skin population is empty"
    assert any(suite["resolved_program"] in sentence for sentence in sentences), (
        "test_suite_lines describes only the configured command, not the program run"
    )
    for skin, rendered in skins.items():
        assert "Command: python3 -m pytest" in rendered, (
            f"{skin} dropped the configured test command"
        )
        assert suite["resolved_program"] in rendered, (
            f"{skin} joins command but hides the program it ran"
        )
