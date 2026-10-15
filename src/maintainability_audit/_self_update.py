"""Keep the local install current: ``--update`` and ``--install-updater``.

The updater used to be an untracked script beside the venv, run by a launch
agent. It trusted PyPI's ``info.version``, which lags a release, and on
2026-09-22 it *downgraded* 3.7.29 to 3.7.19; it never re-synced the skill the
README says to sync after every upgrade; and nothing tested it (D230).

Now it is a product command. The installer resolves the version — ``pip
install --upgrade`` picks the highest release the index lists and never moves
backwards — so this module holds no HTTP client and reads no release feed
(P1: analysis touches no network; updating is an operator action, like tool
acquisition). Every child process goes through ``_runner.run`` (rule 7). A
version that comes back lower than before is reported, never accepted
silently; a higher one re-syncs the skill and records that the MCP server,
which holds the code it loaded at spawn, needs a restart; stale servers
that are not mid-audit are stopped so their host restarts them (D232).
"""

from __future__ import annotations

import plistlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from . import _mcp_servers, _runner

PACKAGE = "maintainability-agent"
#: The launch agent, named for the product and the component (reverse DNS of
#: the project's home), replacing the personal-prefix label it had before.
LABEL = "io.github.marshallguillory86.maintainability-agent.update"
LEGACY_LABEL = "com.marshallguillory.maintainability-agent-update"
_VERSION_CODE = f"import importlib.metadata as m; print(m.version({PACKAGE!r}))"


@dataclass(frozen=True)
class UpdateResult:
    before: str
    after: str
    skill_synced: bool
    restart_needed: bool
    error: str | None
    message: str


def _key(version: str) -> tuple:
    """Release ordering for plain ``N.N.N`` versions; a suffix sorts before
    the release it precedes (``4.4.1rc1`` < ``4.4.1``)."""
    parts = []
    for piece in version.strip().split("."):
        number = re.match(r"\d+", piece)
        parts.append((int(number.group()) if number else 0, 1 if number and number.end() == len(piece) else 0))
    return tuple(parts)


def _state_dir(home: Path) -> Path:
    return home / ".local" / "share" / "maintainability-agent"


def _run(argv: list[str]) -> _runner.ToolResult:
    return _runner.run("self-update", _runner.Invocation(argv=tuple(argv)), timeout_seconds=600)


def _installed(python: str) -> str:
    return (_run([python, "-c", _VERSION_CODE]).stdout or "").strip()


def update(python: str, uv: str | None, home: Path) -> UpdateResult:
    before = _installed(python)
    if uv:
        argv = [uv, "pip", "install", "--python", python, "--upgrade", PACKAGE]
    else:
        argv = [python, "-m", "pip", "install", "--upgrade", PACKAGE]
    installed = _run(argv)
    after = _installed(python)
    if not installed.usable:
        return UpdateResult(before, after, False, False, f"install failed: {installed.detail}",
                            f"Update failed; still on {before}.")
    if _key(after) < _key(before):
        return UpdateResult(before, after, False, False,
                            f"version went down from {before} to {after}",
                            f"Refused: the install moved {before} to {after}, a downgrade.")
    if _key(after) == _key(before):
        return UpdateResult(before, after, False, False, None,
                            f"Already up to date ({after}).{_servers_note(home, after)}")
    _run([python, "-m", "maintainability_audit", "--install-skill"])
    state = _state_dir(home)
    state.mkdir(parents=True, exist_ok=True)
    (state / ".pending-restart").write_text(after + "\n", encoding="utf-8")
    return UpdateResult(before, after, True, True, None,
                        f"Updated {before} -> {after}; skill re-synced.{_servers_note(home, after)}")


def _servers_note(home: Path, installed: str) -> str:
    """Stop the MCP servers still on an older version (D232) and say so.
    A host starts a stopped stdio server again on its next call."""
    result = _mcp_servers.stop_stale(home, installed)
    note = ""
    if result.stopped:
        note += (f" Stopped {len(result.stopped)} MCP server(s) on an older version;"
                 f" the host starts {installed} on its next call.")
    if result.busy:
        note += (f" {len(result.busy)} busy with an audit kept running;"
                 " the next update stops it.")
    return note


def update_action() -> int:
    result = update(sys.executable, _runner.locate("uv"), Path.home())
    print(result.message, file=sys.stderr if result.error else sys.stdout)
    return 1 if result.error else 0


def install_updater(home: Path, *, launchctl: bool = True) -> int:
    """Write the hourly launch agent that runs ``--update``; remove the
    legacy one so two updaters never run."""
    agents = home / "Library" / "LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    legacy = agents / f"{LEGACY_LABEL}.plist"
    if legacy.exists():
        if launchctl:
            _run(["launchctl", "unload", str(legacy)])
        legacy.unlink()
    state = _state_dir(home)
    state.mkdir(parents=True, exist_ok=True)
    plist = agents / f"{LABEL}.plist"
    plist.write_bytes(plistlib.dumps({
        "Label": LABEL,
        "ProgramArguments": [sys.executable, "-m", "maintainability_audit", "--update"],
        "StartInterval": 3600,
        "RunAtLoad": True,
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "StandardOutPath": str(state / "update.out.log"),
        "StandardErrorPath": str(state / "update.err.log"),
    }))
    if launchctl:
        _run(["launchctl", "load", str(plist)])
    print(f"installed {plist}")
    return 0
