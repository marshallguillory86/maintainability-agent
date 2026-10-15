# Written by the Claude Sonnet test seat (Codex at its usage limit); Codex reviews.
# His decision 2026-10-15: macOS is verified by an enforced local gate, not a CI runner.
"""The enforced local gate that is the macOS evidence.

`verify-macos` was removed from CI so each test runs once, on Linux. The
claim that macOS works now rests on a git pre-push hook that runs the
full suite on the maintainer's Mac. These tests pin the gate script, the
installer, and the contributor docs that point at them.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "local-gate.sh"
INSTALLER = ROOT / "tools" / "install-local-gate.sh"


def _logical_lines(path: Path) -> list[str]:
    """Script lines with backslash continuations joined, comments dropped."""
    text = path.read_text(encoding="utf-8").replace("\\\n", " ")
    return [
        " ".join(line.split()) for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def _temp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "tools").mkdir(parents=True)
    assert _git(repo, "init", "-q").returncode == 0
    for script in (GATE, INSTALLER):
        target = repo / "tools" / script.name
        shutil.copy(script, target)
        target.chmod(0o755)
    return repo


def _install(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(repo / "tools" / "install-local-gate.sh")],
        cwd=repo, capture_output=True, text=True, check=False)


# -- 1. the gate script ---------------------------------------------------

def test_the_gate_script_exists_and_is_executable() -> None:
    assert GATE.is_file(), "tools/local-gate.sh does not exist"
    assert os.access(GATE, os.X_OK), "tools/local-gate.sh is not executable"


def test_the_gate_fails_fast() -> None:
    lines = _logical_lines(GATE)
    assert "set -euo pipefail" in lines


def test_the_gate_runs_from_the_repository_root() -> None:
    text = GATE.read_text(encoding="utf-8")
    assert re.search(r"^\s*cd\s.*\.\.", text, re.MULTILINE), (
        "the gate must cd to the directory above its own location")
    assert "BASH_SOURCE" in text or "$0" in text


def test_the_gate_lints_then_runs_the_whole_suite_with_coverage_floor() -> None:
    lines = _logical_lines(GATE)
    lint = [i for i, line in enumerate(lines) if line == "python3 -m ruff check src tests tools"]
    suite = [i for i, line in enumerate(lines)
             if re.search(r"python3 -m pytest\b", line)]
    assert lint, f"no `python3 -m ruff check src tests tools` line: {lines}"
    assert suite, f"no `python3 -m pytest` line: {lines}"
    assert lint[0] < suite[0], "lint must run before the suite"
    command = lines[suite[0]]
    assert re.search(r"-n auto\b", command)
    assert "--cov=maintainability_audit" in command
    assert "--cov-fail-under=92" in command
    assert not re.search(r"tests/\S+\.py", command), (
        "the gate must run the whole suite, not named files")


# -- 2. the installer -----------------------------------------------------

def test_the_installer_exists_and_is_executable() -> None:
    assert INSTALLER.is_file(), "tools/install-local-gate.sh does not exist"
    assert os.access(INSTALLER, os.X_OK)


def test_the_installer_resolves_the_hooks_dir_through_git() -> None:
    """`--git-common-dir`/hooks is the repository's own hooks folder in every
    worktree. `--git-path hooks` follows a global core.hooksPath to a shared
    dispatcher, which the installer must never write into; that dispatcher
    runs `$(git rev-parse --git-common-dir)/hooks/<name>` itself."""
    text = INSTALLER.read_text(encoding="utf-8")
    assert "git rev-parse --git-common-dir" in text
    assert "--git-path hooks" not in text


def test_the_installer_writes_an_executable_pre_push_hook(tmp_path: Path) -> None:
    repo = _temp_repo(tmp_path)
    result = _install(repo)
    assert result.returncode == 0, result.stderr
    hook = repo / ".git" / "hooks" / "pre-push"
    assert hook.is_file()
    assert os.access(hook, os.X_OK)
    assert "tools/local-gate.sh" in hook.read_text(encoding="utf-8")


def test_the_installer_is_idempotent(tmp_path: Path) -> None:
    repo = _temp_repo(tmp_path)
    assert _install(repo).returncode == 0
    hook = repo / ".git" / "hooks" / "pre-push"
    first = hook.read_bytes()
    again = _install(repo)
    assert again.returncode == 0, again.stderr
    assert hook.read_bytes() == first


def test_the_installer_will_not_overwrite_a_foreign_hook(tmp_path: Path) -> None:
    repo = _temp_repo(tmp_path)
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    hook = hooks / "pre-push"
    hook.write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
    hook.chmod(0o755)
    before = hook.read_bytes()
    result = _install(repo)
    assert result.returncode != 0
    assert hook.read_bytes() == before


def test_the_installed_hook_blocks_a_push_when_the_gate_fails(tmp_path: Path) -> None:
    repo = _temp_repo(tmp_path)
    assert _install(repo).returncode == 0
    # Replace the copied gate with one that fails: the hook must propagate.
    gate = repo / "tools" / "local-gate.sh"
    gate.write_text("#!/usr/bin/env bash\nexit 7\n", encoding="utf-8")
    gate.chmod(0o755)
    hook = repo / ".git" / "hooks" / "pre-push"
    result = subprocess.run(
        [str(hook), "origin", "file:///nowhere"], cwd=repo, input="",
        capture_output=True, text=True, check=False)
    assert result.returncode != 0


def test_the_installed_hook_passes_when_the_gate_passes(tmp_path: Path) -> None:
    repo = _temp_repo(tmp_path)
    assert _install(repo).returncode == 0
    gate = repo / "tools" / "local-gate.sh"
    gate.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    gate.chmod(0o755)
    hook = repo / ".git" / "hooks" / "pre-push"
    result = subprocess.run(
        [str(hook), "origin", "file:///nowhere"], cwd=repo, input="",
        capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


# -- 3. the contributor docs ---------------------------------------------

def test_contributing_tells_contributors_to_install_the_gate() -> None:
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "tools/install-local-gate.sh" in text


def test_contributing_says_the_pre_push_gate_verifies_macos() -> None:
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8").lower()
    assert "pre-push" in text
    assert "macos" in text
    assert any(
        "pre-push" in para.lower() and "macos" in para.lower()
        for para in text.split("\n\n")
    ), "the pre-push gate and macOS must be stated together"
