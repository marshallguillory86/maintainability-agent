"""Missing security scanners are named, with their installs, before the run.

A self-audit ran with checkov, osv-scanner, trivy and rubocop absent. The
maintainability half was valid and the security pillar came back
`unverified`: the grade was wasted, and the only signal was a reason string
inside the pillar. The environment work order — the list of install
actions a reader acts on — was empty, because it only ever covered this
tool's own analyzer pool.

secure-code-agent already answers the question: `--preflight --json`
resolves every enabled scanner and gives each missing one its own install
hint. This reads it, so the advice is the delegate's and cannot drift from
it, and puts each gap in the environment work order — in every report, and
on the chat door's run-or-reconfigure question, which comes before the run.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from maintainability_audit import _security_delegate

PREFLIGHT = {
    "required": ["bandit", "pip_audit"],
    "scanners": [
        {"scanner": "bandit", "required": True, "available": True, "remedy": None},
        {"scanner": "trivy", "required": False, "available": False, "remedy": "brew install trivy"},
        {"scanner": "pip_audit", "required": True, "available": False, "remedy": "pip install pip-audit"},
    ],
    "required_unresolved": ["pip_audit"],
    "required_not_selected": [],
    "ready": False,
}


def _preflight_returns(monkeypatch, payload, *, exit_code=1, installed=True) -> list:
    calls: list = []

    def fake_run(name, invocation, **kwargs):
        calls.append(invocation.argv)
        return SimpleNamespace(exit_code=exit_code, stdout=json.dumps(payload) if payload is not None else "",
                               stderr="", detail="", outcome=None)

    monkeypatch.setattr(_security_delegate, "run", fake_run)
    monkeypatch.setattr(_security_delegate.importlib.util, "find_spec",
                        lambda name: object() if installed else None)
    monkeypatch.setattr(_security_delegate, "_installed_version", lambda: _security_delegate.SUPPORTED_FLOOR)
    return calls


def test_each_missing_scanner_becomes_an_install_action(monkeypatch, tmp_path: Path) -> None:
    calls = _preflight_returns(monkeypatch, PREFLIGHT)

    gaps = _security_delegate.scanner_gaps(tmp_path)

    assert "--preflight" in calls[0] and "--json" in calls[0]
    assert [(g["tool"], g["install"]) for g in gaps] == [
        ("pip_audit", "pip install pip-audit"), ("trivy", "brew install trivy")]
    assert all(g["concepts"] == "security" for g in gaps)
    assert "required" in gaps[0]["reason"] and "optional" in gaps[1]["reason"]


def test_nothing_missing_is_an_empty_list(monkeypatch, tmp_path: Path) -> None:
    ready = {**PREFLIGHT, "scanners": [PREFLIGHT["scanners"][0]], "ready": True}
    _preflight_returns(monkeypatch, ready, exit_code=0)

    assert _security_delegate.scanner_gaps(tmp_path) == []


def test_an_unreadable_preflight_adds_nothing_and_breaks_nothing(monkeypatch, tmp_path: Path) -> None:
    """Advice never breaks a run: no JSON, no entries, no exception."""
    _preflight_returns(monkeypatch, None, exit_code=2)

    assert _security_delegate.scanner_gaps(tmp_path) == []


def test_without_the_delegate_there_is_no_preflight(monkeypatch, tmp_path: Path) -> None:
    """Its absence already has its own install entry; no second spawn."""
    calls = _preflight_returns(monkeypatch, PREFLIGHT, installed=False)

    assert _security_delegate.scanner_gaps(tmp_path) == []
    assert calls == []


def test_the_run_carries_the_gaps_into_the_environment_work_order(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(_security_delegate, "scanner_gaps",
                        lambda root, **k: [{"tool": "trivy", "reason": "r", "install": "i",
                                            "verify": "v", "concepts": "security"}])
    _preflight_returns(monkeypatch, {"x": 1}, exit_code=0)
    monkeypatch.setattr(_security_delegate, "read_produced", lambda path: {"pillar": "security"})

    run = _security_delegate.run_security_delegate(tmp_path)

    assert [e["tool"] for e in run.environment] == ["trivy"]


def test_the_chat_door_names_them_before_the_run(monkeypatch, tmp_path: Path) -> None:
    from maintainability_audit import _mcp_gate

    monkeypatch.setattr(_mcp_gate, "scanner_gaps",
                        lambda root, **k: [{"tool": "trivy", "reason": "optional scanner not installed",
                                            "install": "brew install trivy", "verify": "trivy --version",
                                            "concepts": "security"}])
    monkeypatch.setattr(_mcp_gate, "run_tests_pending", lambda root: False)
    monkeypatch.setattr(_mcp_gate, "consented_without_command", lambda root: False)

    reply = _mcp_gate._choose_next(tmp_path)

    assert reply["environment_work_order"][0]["tool"] == "trivy"
    assert "trivy" in reply["choice_needed"]["prompt"]


def test_a_required_scanner_switched_off_is_named_once_the_tree_is_read(monkeypatch, tmp_path: Path) -> None:
    """`required_not_selected` was never read, so the advice said nothing (Grok, 4.0.0).

    A required scanner the tree's config disables makes the pillar's
    coverage fail, and that is as much an environment fact as a missing
    install. It can only be known from the tree's own config, so it is named
    by the preflight the run makes after consent.
    """
    disabled = {**PREFLIGHT, "scanners": [PREFLIGHT["scanners"][0]],
                "required_unresolved": [], "required_not_selected": ["semgrep"]}
    calls = _preflight_returns(monkeypatch, disabled)

    gaps = _security_delegate.scanner_gaps(tmp_path, tree_config=True)

    assert "--config" not in calls[0]
    assert [g["tool"] for g in gaps] == ["semgrep"]
    assert "enabled" in gaps[0]["install"] and "required" in gaps[0]["reason"]


def test_before_consent_the_preflight_is_handed_a_neutral_config(monkeypatch, tmp_path: Path) -> None:
    calls = _preflight_returns(monkeypatch, PREFLIGHT)

    _security_delegate.scanner_gaps(tmp_path)

    config = calls[0][calls[0].index("--config") + 1]
    assert not Path(config).is_relative_to(tmp_path)
