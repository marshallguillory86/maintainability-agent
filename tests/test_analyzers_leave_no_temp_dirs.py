"""An analyzer leaves nothing behind in the system temp directory (D235).

Four adapters — jscpd, complexipy, checkstyle, spotbugs — made a scratch
directory with `tempfile.mkdtemp` in their constructors and never removed
it. Every adapter object built left a directory, whether or not its tool
ever ran: the registry is built on every audit and many times in every
test run, so one machine's temp directory held 74,535 of them (21,294
`jscpd-`, 20,185 `complexipy-`, 16,952 `checkstyle-`, 16,104 `spotbugs-`)
on a disk at 98%, and removing them freed 13.5 GB.

A scratch directory is now made only when a tool is about to run, and is
removed once its output has been read, whatever the outcome.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from maintainability_audit import _analysis
from maintainability_audit._generic import DECLARED, declared_adapter
from maintainability_audit._runner import Outcome, ToolResult
from maintainability_audit._tool_adapters import ADAPTERS

SCRATCH_ADAPTERS = ("jscpd", "complexipy", "checkstyle", "spotbugs")


@pytest.fixture
def temp_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The system temp directory, redirected to one this test can count."""
    root = tmp_path / "system-temp"
    root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(root))
    return root


def test_building_every_adapter_makes_no_directory(temp_root: Path) -> None:
    adapters = [make() for make in ADAPTERS.values()] + [declared_adapter(slug) for slug in DECLARED]

    assert len(adapters) > 10
    assert list(temp_root.iterdir()) == []


@pytest.mark.parametrize("slug", SCRATCH_ADAPTERS)
def test_a_run_removes_its_scratch_directory_whatever_the_outcome(
        slug: str, temp_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "A.java").write_text("class A {}\n", encoding="utf-8")
    (tree / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tree / "build" / "classes").mkdir(parents=True)
    (tree / "build" / "classes" / "A.class").write_bytes(b"\xca\xfe\xba\xbe")
    monkeypatch.setattr(_analysis, "run", lambda tool, invocation, **k: ToolResult(
        slug=tool, outcome=Outcome.RAN, stdout="", stderr="", exit_code=0))
    probe = SimpleNamespace(check=lambda tool, argv: SimpleNamespace(
        usable=True, version="1", outcome=Outcome.RAN, detail=""))

    _analysis._run_one(tree, ADAPTERS[slug](), probe, 60, _analysis.Analysis())

    assert list(temp_root.iterdir()) == []


def test_no_test_makes_a_temp_directory_it_never_removes() -> None:
    """The suite's own share of the same leak: `mkdtemp` is never cleaned up.

    `tmp_path` is pytest's and is pruned; `TemporaryDirectory` removes
    itself. A bare `mkdtemp` in a test leaves one directory per run.
    """
    tests = Path(__file__).resolve().parent
    offenders = sorted(
        path.name for path in tests.glob("*.py")
        if path.name != Path(__file__).name and "mkdtemp(" in path.read_text(encoding="utf-8")
    )
    assert offenders == [], f"these tests leave a temp directory behind: {offenders}"


def test_every_test_writes_its_temp_files_under_pytests_own_base(
        tmp_path: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    """A test that builds an adapter and calls it piecemeal never reaches the
    release in `_run_one`; the suite left 29 directories that way after the
    adapters were fixed. So no test can write to the system temp directory —
    and not into `tmp_path` either, which is often the tree under audit."""
    temp = Path(tempfile.gettempdir()).resolve()
    assert temp.is_relative_to(tmp_path_factory.getbasetemp().resolve())
    assert not temp.is_relative_to(tmp_path.resolve())
