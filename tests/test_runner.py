"""The runner must never turn a broken tool into a clean result — ADR 006.

The motivating measurement, taken on a developer machine: `/usr/bin/java`
exists and `command -v java` succeeds, but it is the macOS stub with no JDK
behind it, and PMD refused to launch through it. Presence on `PATH` says
nothing about whether a tool works.

Exit codes are not sufficient either — a launcher can exit zero having done
nothing, and many linters exit non-zero to report findings. A runner trusting
`PATH` or exit codes alone would record a tool as having run, found nothing,
and contributed a clean result. That is the hello-world A+ arriving
through a new door, so these tests are about the *class*: no failure mode may
be indistinguishable from success.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from maintainability_audit._runner import (
    Invocation,
    Outcome,
    Probe,
    ToolResult,
    run,
)


def _script(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


@pytest.fixture
def on_path(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    return tmp_path


def test_a_missing_tool_is_reported_not_assumed_clean() -> None:
    result = Probe().check("nope", ("definitely-not-a-real-tool-xyz", "--version"))

    assert result.outcome is Outcome.NOT_INSTALLED
    assert not result.usable
    assert "PATH" in result.detail


def test_a_stub_that_exits_zero_is_not_available(on_path) -> None:
    """A launcher reporting success while doing nothing.

    Constructed rather than copied from `java`, which in fact exits 1 —
    an earlier note here claimed it exited 0, from a shell pipeline whose
    `$?` was `head`'s. The case is still worth guarding: nothing forces a
    broken launcher to signal failure, and this is the shape that would
    contribute a clean result if it did not.
    """
    _script(on_path, "javaish", 'echo "Unable to locate a Java Runtime" >&2; exit 0')
    result = Probe().check("javaish", ("javaish", "-version"))

    assert result.outcome is Outcome.NOT_WORKING
    assert not result.usable
    assert "not functional" in result.detail


def test_a_tool_that_exits_zero_saying_nothing_is_not_available(on_path) -> None:
    """Silence cannot be evidence of a working tool."""
    _script(on_path, "mute", "exit 0")
    result = Probe().check("mute", ("mute", "--version"))

    assert result.outcome is Outcome.NOT_WORKING
    assert "no version output" in result.detail


def test_a_working_tool_reports_its_version(on_path) -> None:
    _script(on_path, "good", 'echo "good 1.2.3"')
    result = Probe().check("good", ("good", "--version"))

    assert result.outcome is Outcome.RAN
    assert result.usable
    assert result.version == "good 1.2.3"


@pytest.mark.parametrize(
    "body,expected",
    [
        ('echo "boom" >&2; exit 3', Outcome.FAILED),
        ("exit 1", Outcome.FAILED),
    ],
    ids=["stderr-and-nonzero", "bare-nonzero"],
)
def test_a_failing_tool_is_never_usable(on_path, body: str, expected: Outcome) -> None:
    _script(on_path, "bad", body)
    result = run("bad", Invocation(argv=("bad",)))

    assert result.outcome is expected
    assert not result.usable


def test_a_nonzero_exit_can_still_be_findings_when_declared(on_path) -> None:
    """Many linters signal findings with exit 1.

    Treating that as failure would silently discard every finding the tool
    produced — the opposite error, and just as quiet.
    """
    _script(on_path, "linty", 'echo "a.py:1: something"; exit 1')
    result = run("linty", Invocation(argv=("linty",), findings_exit_codes=(0, 1)))

    assert result.outcome is Outcome.RAN
    assert "something" in result.stdout


def test_a_hanging_tool_times_out_rather_than_hanging_the_audit(on_path) -> None:
    _script(on_path, "slow", "sleep 30")
    result = run("slow", Invocation(argv=("slow",)), timeout_seconds=1)

    assert result.outcome is Outcome.TIMED_OUT
    assert not result.usable
    assert "timeout_seconds" in result.detail, "the remedy belongs in the message"


def test_a_non_executable_file_on_path_is_not_available(on_path) -> None:
    """`which` can succeed where exec fails: no execute bit, bad shebang."""
    broken = on_path / "brokenbit"
    broken.write_text("#!/nonexistent/interpreter\n", encoding="utf-8")
    broken.chmod(broken.stat().st_mode | stat.S_IEXEC)

    result = Probe().check("brokenbit", ("brokenbit",))
    assert not result.usable


def test_no_outcome_other_than_ran_is_usable() -> None:
    """The structural guard.

    An outcome added later is unusable until someone deliberately decides
    otherwise, rather than defaulting into contributing evidence.
    """
    for outcome in Outcome:
        result = ToolResult(slug="x", outcome=outcome)
        assert result.usable == (outcome is Outcome.RAN)


def test_the_probe_is_cached_so_one_tool_is_asked_once(on_path) -> None:
    counter = on_path / "count"
    _script(on_path, "counted", f'echo run >> {counter}; echo "counted 1.0"')
    probe = Probe()
    for _ in range(3):
        assert probe.check("counted", ("counted", "--version")).usable

    assert counter.read_text(encoding="utf-8").count("run") == 1


def test_running_a_real_tool_end_to_end() -> None:
    """One check against a genuinely installed binary, not a shell stub."""
    result = Probe().check("python", (sys.executable, "--version"))

    assert result.outcome is Outcome.RAN
    assert "Python" in (result.version or "")
