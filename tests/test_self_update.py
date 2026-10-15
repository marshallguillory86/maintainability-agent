"""The updater is a product command: it never downgrades and re-syncs the skill.

Written by the Claude Sonnet test seat (Codex at its usage limit); Codex reviews.
Defect: the updater downgraded and never re-synced the skill (2026-09-22/10-15).

Seams: ``maintainability_audit._runner.run`` is replaced with a recording fake
(``_FakeRunner``) so no process is spawned, no network is touched and no real
home or launchd is involved. The implementation must call it as
``_runner.run(...)`` (module attribute) so the patch is seen. A child
``python -c`` version read is recognised by ``-c`` in argv and answered from a
scripted before/after sequence. ``_self_update`` is imported inside each test
so a missing module is a failure, not a collection error.
"""

from __future__ import annotations

import importlib
import plistlib
import re
import sys
from pathlib import Path

import pytest

from maintainability_audit import _runner
from maintainability_audit.cli import main

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"
LABEL = "io.github.marshallguillory86.maintainability-agent.update"
LEGACY = "com.marshallguillory.maintainability-agent-update"
PY = "/fake/venv/bin/python"
UV = "/fake/bin/uv"


def _su():
    return importlib.import_module("maintainability_audit._self_update")


class _FakeRunner:
    """Stands in for ``_runner.run``; records argv, answers version reads."""

    def __init__(self, versions: list[str]) -> None:
        self.versions = list(versions)
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, slug, invocation, **kwargs):
        argv = tuple(invocation.argv)
        self.calls.append(argv)
        out = ""
        if "-c" in argv:
            out = self.versions.pop(0) + "\n"
        return _runner.ToolResult(slug=slug, outcome=_runner.Outcome.RAN,
                                  stdout=out, exit_code=0)

    def with_flag(self, flag: str) -> list[tuple[str, ...]]:
        return [c for c in self.calls if flag in c]


@pytest.fixture
def fake(monkeypatch):
    def make(versions: list[str]) -> _FakeRunner:
        runner = _FakeRunner(versions)
        monkeypatch.setattr(_runner, "run", runner)
        return runner
    return make


def _marker(home: Path) -> Path:
    return home / ".local" / "share" / "maintainability-agent" / ".pending-restart"


def _text(result) -> str:
    return " ".join(str(v) for v in vars(result).values()) if hasattr(result, "__dict__") else str(result)


# 1 -- the CLI flag ---------------------------------------------------------

def test_update_flag_dispatches_to_self_update(monkeypatch) -> None:
    su = _su()
    seen = []

    def fake_update(python, uv, home):
        seen.append((python, uv, home))
        return su.UpdateResult(before="1.0.0", after="1.0.0", skill_synced=False,
                               restart_needed=False, error=None,
                               message="already up to date")

    monkeypatch.setattr(su, "update", fake_update)
    assert main(["--update"]) == 0
    assert len(seen) == 1


# 2 -- install command ------------------------------------------------------

def test_uv_install_argv(fake, tmp_path) -> None:
    runner = fake(["4.4.0", "4.4.0"])
    _su().update(PY, UV, tmp_path)
    assert [UV, "pip", "install", "--python", PY, "--upgrade",
            "maintainability-agent"] in [list(c) for c in runner.calls]


def test_pip_install_argv_without_uv(fake, tmp_path) -> None:
    runner = fake(["4.4.0", "4.4.0"])
    _su().update(PY, None, tmp_path)
    assert [PY, "-m", "pip", "install", "--upgrade",
            "maintainability-agent"] in [list(c) for c in runner.calls]


def test_no_http_client_or_pypi_json_in_module() -> None:
    source = (PACKAGE / "_self_update.py").read_text(encoding="utf-8")
    for banned in ("urllib", "http.client", "requests", "pypi.org/pypi"):
        assert banned not in source, banned


def test_module_does_not_import_subprocess() -> None:
    source = (PACKAGE / "_self_update.py").read_text(encoding="utf-8")
    assert not re.search(r"\bsubprocess\b", source)


# 3 -- version reads --------------------------------------------------------

def test_versions_read_before_and_after_via_child_python(fake, tmp_path) -> None:
    runner = fake(["4.4.0", "4.4.0"])
    result = _su().update(PY, UV, tmp_path)
    reads = runner.with_flag("-c")
    assert len(reads) == 2
    for argv in reads:
        assert argv[0] == PY
        assert "importlib.metadata" in argv[argv.index("-c") + 1]
        assert "maintainability-agent" in argv[argv.index("-c") + 1]
    # before is read before the install, after is read after it
    install_index = next(i for i, c in enumerate(runner.calls) if "install" in c)
    read_indexes = [i for i, c in enumerate(runner.calls) if "-c" in c]
    assert read_indexes[0] < install_index < read_indexes[1]
    assert (result.before, result.after) == ("4.4.0", "4.4.0")


# 4 -- never downgrades -----------------------------------------------------

@pytest.mark.parametrize("before,after", [("4.4.1", "4.4.0"), ("4.10.0", "4.9.9")])
def test_downgrade_is_an_error_and_does_not_sync(fake, tmp_path, before, after) -> None:
    runner = fake([before, after])
    result = _su().update(PY, UV, tmp_path)
    assert result.error
    assert before in result.error and after in result.error
    assert result.skill_synced is False
    assert runner.with_flag("--install-skill") == []
    assert not _marker(tmp_path).exists()


def test_version_order_is_numeric_not_lexical(fake, tmp_path) -> None:
    """4.9.9 -> 4.10.0 is an upgrade (a string compare would call it a downgrade)."""
    runner = fake(["4.9.9", "4.10.0"])
    result = _su().update(PY, UV, tmp_path)
    assert not result.error
    assert runner.with_flag("--install-skill")


# 5 -- upgrade --------------------------------------------------------------

def test_upgrade_syncs_skill_writes_marker_and_says_restart(fake, tmp_path) -> None:
    runner = fake(["4.4.0", "4.5.0"])
    result = _su().update(PY, UV, tmp_path)
    assert [PY, "-m", "maintainability_audit", "--install-skill"] in [
        list(c) for c in runner.calls]
    assert result.skill_synced is True
    assert result.restart_needed is True
    assert not result.error
    assert _marker(tmp_path).read_text(encoding="utf-8").strip() == "4.5.0"
    assert "/mcp" in result.message


# 6 -- up to date -----------------------------------------------------------

def test_equal_versions_do_nothing_and_exit_zero(fake, tmp_path, capsys,
                                                 monkeypatch) -> None:
    runner = fake(["4.4.0", "4.4.0"])
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _su().update(PY, UV, tmp_path)
    assert result.skill_synced is False and result.restart_needed is False
    assert not result.error
    assert runner.with_flag("--install-skill") == []
    assert not _marker(tmp_path).exists()
    assert "up to date" in result.message.lower()


def test_update_command_exit_zero_when_up_to_date(fake, tmp_path, monkeypatch) -> None:
    fake(["4.4.0", "4.4.0"])
    monkeypatch.setenv("HOME", str(tmp_path))
    assert main(["--update"]) == 0


def test_update_command_exit_nonzero_on_downgrade(fake, tmp_path, monkeypatch) -> None:
    fake(["4.4.1", "4.4.0"])
    monkeypatch.setenv("HOME", str(tmp_path))
    assert main(["--update"]) != 0


# 7 -- launch agent ---------------------------------------------------------

def _plist(home: Path) -> dict:
    path = home / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    assert path.is_file()
    return plistlib.loads(path.read_bytes())


def test_install_updater_writes_launch_agent(fake, tmp_path) -> None:
    fake([])
    assert main(["--install-updater", "--home", str(tmp_path), "--no-launchctl"]) == 0
    data = _plist(tmp_path)
    assert data["Label"] == LABEL
    assert data["ProgramArguments"] == [sys.executable, "-m",
                                        "maintainability_audit", "--update"]
    assert data["StartInterval"] == 3600
    assert data["RunAtLoad"] is True
    assert data["ProcessType"] == "Background"


def test_install_updater_removes_legacy_agent(fake, tmp_path) -> None:
    fake([])
    agents = tmp_path / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    legacy = agents / f"{LEGACY}.plist"
    legacy.write_bytes(plistlib.dumps({"Label": LEGACY}))
    assert main(["--install-updater", "--home", str(tmp_path), "--no-launchctl"]) == 0
    assert not legacy.exists()
    assert (agents / f"{LABEL}.plist").is_file()


def test_no_launchctl_flag_calls_no_launchctl(fake, tmp_path) -> None:
    runner = fake([])
    main(["--install-updater", "--home", str(tmp_path), "--no-launchctl"])
    assert [c for c in runner.calls if Path(c[0]).name == "launchctl"] == []


def test_without_flag_launchctl_is_called_through_runner(fake, tmp_path) -> None:
    runner = fake([])
    main(["--install-updater", "--home", str(tmp_path)])
    assert [c for c in runner.calls if Path(c[0]).name == "launchctl"]
