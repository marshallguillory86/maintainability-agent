"""D232: running MCP servers are registered so ``--update`` can stop stale ones.

After an upgrade the old server kept serving old code and /mcp reloads
nothing. ``_mcp_servers`` keeps one record per server under
``<home>/.local/share/maintainability-agent/servers`` and stops, by SIGTERM,
those running an older version that are not mid-audit.

Seams: ``alive``, ``is_server`` and ``kill`` are injected fakes, so no real
process is signalled. ``home`` is always ``tmp_path``.
"""

from __future__ import annotations

import importlib
import json
import os
import signal
from pathlib import Path

import pytest

from maintainability_audit import mcp_server


def _ms():
    return importlib.import_module("maintainability_audit._mcp_servers")


def _servers(home: Path) -> Path:
    return home / ".local" / "share" / "maintainability-agent" / "servers"


class _Kill:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def __call__(self, pid: int, sig: int) -> None:
        self.calls.append((pid, sig))


def _stop(home: Path, installed: str, *, alive=True, server=True):
    kill = _Kill()
    result = _ms().stop_stale(home, installed, alive=lambda pid: alive,
                              is_server=lambda pid: server, kill=kill)
    return result, kill


def test_register_writes_pid_and_version(tmp_path) -> None:
    path = _ms().register(tmp_path, 4242, "4.4.0")
    assert path == _servers(tmp_path) / "4242.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {"pid": 4242, "version": "4.4.0"}


def test_unregister_removes_record_and_tolerates_absence(tmp_path) -> None:
    ms = _ms()
    path = ms.register(tmp_path, 7, "1.0.0")
    ms.unregister(tmp_path, 7)
    assert not path.exists()
    ms.unregister(tmp_path, 7)  # absent: no error


def test_busy_marker_exists_only_inside_block(tmp_path) -> None:
    marker = _servers(tmp_path) / "9.busy"
    with _ms().busy(tmp_path, 9):
        assert marker.exists()
    assert not marker.exists()


def test_busy_marker_removed_when_body_raises(tmp_path) -> None:
    marker = _servers(tmp_path) / "9.busy"
    with pytest.raises(RuntimeError), _ms().busy(tmp_path, 9):
        raise RuntimeError("audit blew up")
    assert not marker.exists()


def test_stale_live_server_is_sigtermed_and_record_removed(tmp_path) -> None:
    ms = _ms()
    path = ms.register(tmp_path, 100, "4.4.0")
    result, kill = _stop(tmp_path, "4.5.0")
    assert kill.calls == [(100, signal.SIGTERM)]
    assert result.stopped == (100,) and result.busy == () and result.gone == ()
    assert not path.exists()


def test_current_version_server_is_untouched(tmp_path) -> None:
    path = _ms().register(tmp_path, 100, "4.5.0")
    result, kill = _stop(tmp_path, "4.5.0")
    assert kill.calls == []
    assert (result.stopped, result.busy, result.gone) == ((), (), ())
    assert path.exists()


def test_dead_pid_record_is_removed_and_reported_gone(tmp_path) -> None:
    path = _ms().register(tmp_path, 100, "4.4.0")
    result, kill = _stop(tmp_path, "4.5.0", alive=False)
    assert kill.calls == []
    assert result.gone == (100,)
    assert not path.exists()


def test_busy_server_is_left_alone_and_reported_busy(tmp_path) -> None:
    ms = _ms()
    path = ms.register(tmp_path, 100, "4.4.0")
    with ms.busy(tmp_path, 100):
        result, kill = _stop(tmp_path, "4.5.0")
    assert kill.calls == []
    assert result.busy == (100,) and result.stopped == ()
    assert path.exists()


def test_reused_pid_is_never_killed(tmp_path) -> None:
    path = _ms().register(tmp_path, 100, "4.4.0")
    result, kill = _stop(tmp_path, "4.5.0", server=False)
    assert kill.calls == []
    assert result.gone == (100,) and result.stopped == ()
    assert not path.exists()


def test_garbage_record_is_removed_without_crashing(tmp_path) -> None:
    ms = _ms()
    ms.register(tmp_path, 1, "4.4.0")  # makes the directory
    bad = _servers(tmp_path) / "555.json"
    bad.write_text("{not json", encoding="utf-8")
    result, kill = _stop(tmp_path, "4.5.0")
    assert not bad.exists()
    assert 555 not in result.stopped
    assert (555, signal.SIGTERM) not in kill.calls


def test_stop_stale_without_servers_dir_is_empty(tmp_path) -> None:
    result, kill = _stop(tmp_path, "4.5.0")
    assert (result.stopped, result.busy, result.gone) == ((), (), ())
    assert kill.calls == []


# mcp_server wiring ---------------------------------------------------------

def test_main_registers_during_run_and_unregisters_after(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    record = _servers(tmp_path) / f"{os.getpid()}.json"
    seen: dict = {}

    class _Stub:
        def run(self, transport: str) -> None:
            seen["during"] = json.loads(record.read_text(encoding="utf-8"))

    monkeypatch.setattr(mcp_server, "create_server", lambda **_kw: _Stub())
    assert mcp_server.main(["--allow-root", str(tmp_path)]) == 0
    assert seen["during"] == {"pid": os.getpid(), "version": mcp_server.VERSION}
    assert not record.exists()


def test_main_unregisters_when_run_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    record = _servers(tmp_path) / f"{os.getpid()}.json"

    seen: dict = {}

    class _Stub:
        def run(self, transport: str) -> None:
            seen["registered"] = record.exists()
            raise RuntimeError("transport died")

    monkeypatch.setattr(mcp_server, "create_server", lambda **_kw: _Stub())
    with pytest.raises(RuntimeError):
        mcp_server.main(["--allow-root", str(tmp_path)])
    assert seen["registered"] is True
    assert not record.exists()


def test_audit_tool_holds_busy_marker_while_auditing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    marker = _servers(tmp_path) / f"{os.getpid()}.busy"
    seen: dict = {}

    def fake_audit(*_args, **_kwargs):
        seen["busy"] = marker.exists()
        return {"audit_ran": False}

    class _Ledger:
        def current(self):
            return ()

    monkeypatch.setattr(mcp_server, "audit_repository", fake_audit)
    monkeypatch.setattr(mcp_server, "_apply_call_consents", lambda *a, **k: None)
    mcp_server._run_audit_tool(
        _Ledger(), RuntimeError, str(tmp_path), None, None, None, None, None,
        None, False, True, "run", None, None, None)
    assert seen["busy"] is True
    assert not marker.exists()
