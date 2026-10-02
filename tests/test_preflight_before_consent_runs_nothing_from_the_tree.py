"""Asking about a repository runs nothing that repository chose.

3.12.0 named missing security scanners before the run by calling
secure-code-agent's `--preflight` from the chat door's run-or-reconfigure
reply — before anyone had said "run". The preflight reads the audited
tree's `secure-code-agent.json` and probes each scanner's configured
command with `--version`, and that file may name a program on PATH with
any arguments. A tree setting bandit's command to `python -c "<anything>"`
ran it on the auditor's machine the moment it was asked about (Grok's
audit of 4.0.0). "Nothing is audited until the user has been asked twice"
did not hold for the one thing that runs first.

Before consent the preflight now reads a neutral configuration, never the
tree's. It still names the default scanners that are missing. After
consent the tree's own configuration is read, as the run itself does.

These run the real delegate, not a stub: a stubbed `run` is how the first
version passed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("secure_code_audit")

from maintainability_audit import _security_delegate  # noqa: E402


def _hostile_tree(root: Path, marker: Path) -> None:
    (root / "app.py").write_text("x = 1\n", encoding="utf-8")
    command = [sys.executable, "-c", f"open({str(marker)!r}, 'w').write('executed')"]
    (root / "secure-code-agent.json").write_text(
        json.dumps({"scanners": {"bandit": {"command": command}}}), encoding="utf-8")


def test_the_preflight_before_consent_does_not_run_the_trees_command(tmp_path: Path) -> None:
    tree, marker = tmp_path / "tree", tmp_path / "marker"
    tree.mkdir()
    _hostile_tree(tree, marker)

    _security_delegate.scanner_gaps(tree)

    assert not marker.exists(), "the audited tree's configured command ran before consent"


def test_the_chat_door_before_consent_does_not_run_it_either(tmp_path: Path, monkeypatch) -> None:
    """The door that called it, end to end."""
    from maintainability_audit import _mcp_gate

    tree, marker = tmp_path / "tree", tmp_path / "marker"
    tree.mkdir()
    _hostile_tree(tree, marker)
    monkeypatch.setattr(_mcp_gate, "scanner_gaps", _security_delegate.scanner_gaps)
    monkeypatch.setattr(_mcp_gate, "run_tests_pending", lambda root: False)
    monkeypatch.setattr(_mcp_gate, "consented_without_command", lambda root: False)

    _mcp_gate._choose_next(tree)

    assert not marker.exists()
