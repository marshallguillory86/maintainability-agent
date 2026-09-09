"""Finding a tool the operator installed the way we told them to — D142.

`locate` searched the interpreter's own `bin` and then `PATH`. That is
correct for a virtualenv, where `pip install lizard` writes beside the
interpreter. It is wrong for a **system** Python: the framework
directory is not writable, pip falls back to `--user`, and the console
script lands in the per-user scripts directory — on macOS
`~/Library/Python/3.11/bin`, which is on neither list and not on the
default `PATH`.

So the environment work order told an operator to run `pip install
lizard`, they ran it, and the next audit still reported the tool "not
installed or not on PATH". The remedy the product prescribes could not
fix the problem the product reports.

Found by running the audit against this repository through the MCP
server, the surface product intent calls primary. Nine analyzers were
invisible — the whole Python pool, `lizard` and `complexipy` among them
— so `declarations` fell to the built-in tier. The scan still passed its
gate and reported a **better** grade than the same scan with the pool
visible: B against C. A fallback that scores higher than the truth is
the worst direction for a silent failure, because nothing in the result
asks to be looked at.
"""
from __future__ import annotations

import stat
import sysconfig
from pathlib import Path

import pytest

from maintainability_audit import _runner


def _fake_tool(directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / name
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_a_tool_in_the_user_scripts_directory_is_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The case `pip install <tool>` actually produces on a system Python.

    Neither beside the interpreter nor on `PATH`, because that is
    precisely the combination that made the whole Python pool invisible
    on the MCP surface.
    """
    user_scripts = tmp_path / "user-base" / "bin"
    _fake_tool(user_scripts, "lizard")

    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(
        sysconfig, "get_path",
        lambda name, scheme=None, **kw: (
            str(user_scripts) if name == "scripts" else sysconfig.get_paths()[name]
        ),
    )

    found = _runner.locate("lizard")

    assert found is not None, (
        "a tool installed by `pip install lizard` on a system Python was not "
        "found; that is where pip puts it and it is on neither the "
        "interpreter's bin nor PATH"
    )
    assert Path(found) == user_scripts / "lizard"


def test_the_interpreters_own_bin_still_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covers existing behaviour: the venv co-install keeps precedence.

    It passes at the base — own-bin was already searched first — and is
    here because the D142 fix appends a second directory. Appending it
    ahead of `own_bin` would silently prefer a stale user-site copy over
    the pinned one shipped beside the agent, which is the version-drift
    the analyzer pinning exists to prevent.
    """
    own_bin = tmp_path / "venv" / "bin"
    user_scripts = tmp_path / "user-base" / "bin"
    _fake_tool(own_bin, "lizard")
    _fake_tool(user_scripts, "lizard")

    monkeypatch.setattr(_runner.sys, "executable", str(own_bin / "python3"))
    monkeypatch.setattr(
        sysconfig, "get_path",
        lambda name, scheme=None, **kw: (
            str(user_scripts) if name == "scripts" else sysconfig.get_paths()[name]
        ),
    )

    assert Path(_runner.locate("lizard")) == own_bin / "lizard"


def test_path_is_still_searched_when_neither_script_dir_has_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covers existing behaviour: `PATH` remains the last resort.

    Passes at the base. It is here because the fix changed the shape of
    the lookup from two steps to a loop plus a fallback, and dropping the
    fallback would strand every tool an operator installed with homebrew
    or a system package manager — `jscpd` and `pmd` on this machine.
    """
    elsewhere = tmp_path / "opt" / "bin"
    _fake_tool(elsewhere, "pmd")
    monkeypatch.setenv("PATH", str(elsewhere))

    assert Path(_runner.locate("pmd")) == elsewhere / "pmd"


def test_a_missing_tool_is_still_reported_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covers existing behaviour: absence is still absence.

    Passes at the base, and pins the direction the fix must not move.
    Widening the search until something is always found would turn "not
    installed" into a false positive, which is worse than the defect —
    the work order would name a tool that cannot run.
    """
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(
        sysconfig, "get_path",
        lambda name, scheme=None, **kw: (
            str(tmp_path / "also-empty") if name == "scripts"
            else sysconfig.get_paths()[name]
        ),
    )

    assert _runner.locate("a-tool-that-does-not-exist") is None


def test_a_broken_user_scheme_does_not_break_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covers existing behaviour: `PATH` resolution survives sysconfig.

    `get_preferred_scheme("user")` is interpreter-dependent and can raise
    on an unusual install. It is wrapped, because a tool the operator has
    on `PATH` must not become unfindable due to a lookup that exists only
    to find a *different* directory.
    """
    elsewhere = tmp_path / "opt" / "bin"
    _fake_tool(elsewhere, "radon")
    monkeypatch.setenv("PATH", str(elsewhere))

    def explode(*_args: object, **_kwargs: object) -> str:
        raise KeyError("no such scheme")

    monkeypatch.setattr(sysconfig, "get_preferred_scheme", explode)

    assert Path(_runner.locate("radon")) == elsewhere / "radon"


def test_the_agents_script_dirs_are_real_directories_not_guesses() -> None:
    """Whatever is searched must come from this interpreter, not a list.

    A hardcoded `~/Library/Python/3.11/bin` would be right on one machine
    and wrong on every other Python version and platform. Both entries
    are derived: one from `sys.executable`, one from `sysconfig`.
    """
    directories = _runner._agent_script_dirs()

    assert directories, "no script directory is searched at all"
    assert directories[0] == Path(_runner.sys.executable).parent
    assert all(isinstance(d, Path) for d in directories)
    assert len(set(directories)) == len(directories), (
        f"the same directory is searched twice: {directories}"
    )
