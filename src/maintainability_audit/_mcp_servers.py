"""Which MCP servers are running which version, so ``--update`` can stop stale ones.

A stdio MCP server holds the code it loaded at spawn. After an upgrade it
keeps serving the old version until it stops, and its host starts the new
one on the next call. 4.4.2 told the operator to run ``/mcp``, which in the
VS Code panel only lists servers (D232). Now each server records its pid and
version here, marks itself busy while an audit runs, and ``--update`` stops
the stale ones that are idle. A busy server is left alone; the next hourly
update stops it.
"""

from __future__ import annotations

import json
import os
import signal
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import _runner


@dataclass(frozen=True)
class Stopped:
    stopped: tuple[int, ...] = ()
    busy: tuple[int, ...] = ()
    gone: tuple[int, ...] = ()


def _servers(home: Path) -> Path:
    return home / ".local" / "share" / "maintainability-agent" / "servers"


def register(home: Path, pid: int, version: str) -> Path:
    folder = _servers(home)
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / f"{pid}.json"
    record.write_text(json.dumps({"pid": pid, "version": version}) + "\n", encoding="utf-8")
    return record


def unregister(home: Path, pid: int) -> None:
    (_servers(home) / f"{pid}.json").unlink(missing_ok=True)


@contextmanager
def busy(home: Path, pid: int) -> Iterator[None]:
    folder = _servers(home)
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / f"{pid}.busy"
    marker.touch()
    try:
        yield
    finally:
        marker.unlink(missing_ok=True)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _is_server(pid: int) -> bool:
    """The pid is still an MA MCP server, not a reused pid of something else."""
    result = _runner.run("mcp-servers", _runner.Invocation(argv=("ps", "-o", "command=", "-p", str(pid))),
                         timeout_seconds=10)
    command = result.stdout or ""
    return "maintainability" in command and "mcp" in command


def stop_stale(home: Path, installed: str, *,
               alive: Callable[[int], bool] = _alive,
               is_server: Callable[[int], bool] = _is_server,
               kill: Callable[[int, int], None] = os.kill) -> Stopped:
    folder = _servers(home)
    stopped: list[int] = []
    held: list[int] = []
    gone: list[int] = []
    for record in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            data = json.loads(record.read_text(encoding="utf-8"))
            pid, version = int(data["pid"]), str(data["version"])
        except (OSError, ValueError, KeyError, TypeError):
            record.unlink(missing_ok=True)
            continue
        if version == installed:
            continue
        if not alive(pid):
            record.unlink(missing_ok=True)
            gone.append(pid)
        elif (folder / f"{pid}.busy").exists():
            held.append(pid)
        elif not is_server(pid):
            record.unlink(missing_ok=True)
            gone.append(pid)
        else:
            kill(pid, signal.SIGTERM)
            record.unlink(missing_ok=True)
            stopped.append(pid)
    return Stopped(tuple(stopped), tuple(held), tuple(gone))
