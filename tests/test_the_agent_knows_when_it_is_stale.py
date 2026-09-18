"""The agent reports when the code answering is not the code installed (D188).

`config.VERSION` is a source constant, so `agent_version` is read from
whatever code is loaded. It is therefore always self-consistent and can
never be wrong about itself: a server running last week's module states
last week's version as fact, and a reader cannot tell that from a correct
answer. That is how an MCP server here served 3.7.7 for a full day after
3.7.8 shipped, reporting it plainly on every reply.

The installed distribution's metadata is the second opinion, and which
side is ahead names the fault: loaded code *behind* the metadata is a
stale process, loaded code *ahead* of it is an editable install whose
`dist-info` froze at `pip install -e .` time.

The second is the dangerous one, because this project gates its security
delegate on `metadata.version("secure-code-agent")`. A frozen environment
does not just misreport a number — it can refuse a correctly installed
delegate and report the Security pillar unmeasured while everything else
looks green.
"""

from __future__ import annotations

import pytest

from maintainability_audit import _running_version
from maintainability_audit._running_version import version_drift


@pytest.fixture
def installed(monkeypatch):
    """Set what the installed distribution claims, independent of reality."""

    def _set(version: str | None):
        monkeypatch.setattr(_running_version, "installed_version", lambda: version)

    return _set


def _running(monkeypatch, version: str):
    monkeypatch.setattr(_running_version, "VERSION", version)


# --- silence where silence is correct --------------------------------------


def test_agreement_reports_nothing(installed, monkeypatch):
    """The ordinary case says nothing at all."""
    _running(monkeypatch, "3.7.8")
    installed("3.7.8")

    assert version_drift() is None


def test_an_uninstalled_source_checkout_reports_nothing(installed, monkeypatch):
    """Running from a tree with nothing installed is a legitimate way to run.

    A check that fired on every uninstalled run would be trained away
    inside a day, and then it would not be read on the day it mattered.
    """
    _running(monkeypatch, "3.7.8")
    installed(None)

    assert version_drift() is None


# --- the two faults, told apart --------------------------------------------


def test_a_stale_process_is_named_as_a_stale_process(installed, monkeypatch):
    """Loaded code behind the metadata: the install is fine, restart it.

    This is the exact shape that went unnoticed: the server answered 3.7.7
    while 3.7.8 sat installed on disk.
    """
    _running(monkeypatch, "3.7.7")
    installed("3.7.8")

    drift = version_drift()

    assert drift is not None
    assert drift["running"] == "3.7.7"
    assert drift["installed"] == "3.7.8"
    assert "restart" in drift["detail"].lower()
    assert "editable" not in drift["detail"].lower(), (
        "a stale process was told to reinstall, which fixes the wrong thing"
    )


def test_a_frozen_editable_install_is_named_as_one(installed, monkeypatch):
    """Loaded code ahead of the metadata: reinstall, do not restart.

    The observed case — an editable venv serving 3.7.8 with `dist-info`
    still at 1.8.0 — and the detail has to say *reinstall*, because
    restarting a stale editable install changes nothing.
    """
    _running(monkeypatch, "3.7.8")
    installed("1.8.0")

    drift = version_drift()

    assert drift is not None
    assert drift["running"] == "3.7.8"
    assert drift["installed"] == "1.8.0"
    assert "reinstall" in drift["detail"].lower()


def test_the_editable_remedy_names_what_else_reads_the_stale_number(
    installed, monkeypatch
):
    """The consequence is the point, not the mismatched digits.

    A frozen `dist-info` is easy to dismiss as cosmetic. It is not: the
    security delegate's supported-range check reads the same metadata, so
    the remedy says so rather than leaving a reader to find out.
    """
    _running(monkeypatch, "3.7.8")
    installed("1.8.0")

    assert "delegate" in version_drift()["detail"].lower()


def test_an_unorderable_version_still_reports_the_disagreement(
    installed, monkeypatch
):
    """Neither side ordered: say they disagree rather than guess the fault."""
    _running(monkeypatch, "3.7.8")
    installed("not-a-version")

    drift = version_drift()

    assert drift is not None
    assert drift["installed"] == "not-a-version"


# --- it reaches the surfaces that report a version -------------------------


def test_the_gate_reply_carries_the_drift(installed, monkeypatch, tmp_path):
    """The replies that run no audit are where this went unseen for a day.

    `_envelope` answers every `choice_needed` and `setup_needed` call, and
    it stated a stale version with nothing beside it.
    """
    from maintainability_audit import _mcp_gate

    _running(monkeypatch, "3.7.7")
    monkeypatch.setattr(_mcp_gate, "version_drift", lambda: {
        "running": "3.7.7", "installed": "3.7.8", "detail": "stale process",
    })
    monkeypatch.setattr(_mcp_gate, "mark_repo_seen", lambda root: None)

    reply = _mcp_gate._envelope(tmp_path)

    assert reply["version_drift"]["installed"] == "3.7.8"


def test_the_gate_reply_is_unchanged_when_versions_agree(monkeypatch, tmp_path):
    """No key at all in the ordinary case; consumers do not learn to ignore one."""
    from maintainability_audit import _mcp_gate

    monkeypatch.setattr(_mcp_gate, "version_drift", lambda: None)
    monkeypatch.setattr(_mcp_gate, "mark_repo_seen", lambda root: None)

    assert "version_drift" not in _mcp_gate._envelope(tmp_path)


def test_server_info_states_the_drift_field(monkeypatch):
    """`server_info` always carries the key, `None` when there is nothing to say.

    Unlike the gate reply this is a capability description, so a consumer
    reading it should see the field exists rather than infer it.
    """
    from maintainability_audit import mcp_server

    monkeypatch.setattr(mcp_server, "version_drift", lambda: None)

    assert mcp_server.server_info(roots=())["version_drift"] is None
