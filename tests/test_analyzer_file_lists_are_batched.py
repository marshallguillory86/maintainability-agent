"""An analyzer that takes a file list reads every file, in batches.

A file list has to fit on a command line, and `expand_files` cut it at a
quarter of ARG_MAX and logged the cut. Stated, but still a partial
reading: in the 4.0.0 corpus run FFmpeg's analyzers saw 1,543 of 4,687
files and webpack's 1,426 of 11,409, and the measurements of the largest
repositories — in the corpus and in anyone's audit — described a fraction
of them while the report described the tree.

The list is no longer cut. It is split into batches that each fit, the
tool runs once per batch, and what each run reads is merged.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from maintainability_audit import _analysis, _metric_adapters, _runner
from maintainability_audit._adapters import BaseAdapter, Extraction
from maintainability_audit._metrics_types import Measurement
from maintainability_audit._runner import Outcome, ToolResult
from maintainability_audit._tool_adapters import ADAPTERS

BUDGET = 2048


def _big_tree(root: Path) -> list[str]:
    (root / "pkg").mkdir(parents=True)
    (root / "jvm").mkdir()
    for i in range(300):
        (root / "pkg" / f"module_{i:04d}.py").write_text("x = 1\n", encoding="utf-8")
    for i in range(40):
        (root / "jvm" / f"Type{i:03d}.java").write_text("class T {}\n", encoding="utf-8")
    return sorted(str(p) for p in root.rglob("*") if p.is_file())


def test_nothing_is_cut_from_the_file_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(_runner, "_ARGV_BYTE_BUDGET", BUDGET)
    _big_tree(tmp_path)

    assert len(_metric_adapters.expand_files(tmp_path, (), suffixes=(".py",))) == 300


def test_batches_cover_every_file_once_and_each_fits(tmp_path: Path) -> None:
    files = tuple(f"/very/long/path/to/a/source/file_{i:05d}.py" for i in range(500))

    batches = _runner.batches(files, budget=BUDGET)

    assert len(batches) > 1
    assert [name for batch in batches for name in batch] == list(files)
    assert all(sum(len(n.encode()) + 1 for n in batch) <= BUDGET for batch in batches)


def test_every_file_list_adapter_names_every_file_across_its_runs(tmp_path: Path, monkeypatch) -> None:
    """Derived from the registry: any adapter that names files names all of them."""
    monkeypatch.setattr(_runner, "_ARGV_BYTE_BUDGET", BUDGET)
    every = _big_tree(tmp_path)
    naming = []
    for slug, make in ADAPTERS.items():
        adapter = make()
        runs = adapter.invocations(tmp_path, ())
        named = [arg for run in runs for arg in run.argv if arg in every]
        if not named:
            continue
        naming.append(slug)
        suffixes = {Path(name).suffix for name in named}
        expected = [f for f in every if Path(f).suffix in suffixes]
        assert sorted(named) == expected, f"{slug} named {len(named)} of {len(expected)}"
        assert len(runs) > 1, f"{slug} named every file in one argv over the budget"

    assert len(naming) >= 4, f"too few file-list adapters found to mean anything: {naming}"


class _PerFile(BaseAdapter):
    """Reads one measurement per file it was handed, from its stdout."""

    def __init__(self, files: tuple[str, ...]) -> None:
        super().__init__(slug="per-file", emits="metric", executable="per-file",
                         concepts=("lines",), exclude_dialect="files")
        self._files = files

    def target_files(self, root: Path, excludes=()) -> tuple[str, ...]:
        return self._files

    def _read(self, result: ToolResult) -> Extraction:
        return Extraction(measurements=tuple(
            Measurement(concept="lines", unit=name, value=1.0, tool=self.slug, path=name)
            for name in result.stdout.split()))


def test_the_analysis_merges_what_every_batch_read(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(_runner, "_ARGV_BYTE_BUDGET", BUDGET)
    files = tuple(str(tmp_path / f"file_{i:05d}.py") for i in range(400))
    for name in files:
        Path(name).write_text("x\n", encoding="utf-8")
    calls = []

    def fake_run(slug, invocation, **kwargs):
        calls.append(invocation)
        return ToolResult(slug=slug, outcome=Outcome.RAN, stdout=" ".join(invocation.argv[1:]),
                          exit_code=0, duration_seconds=0.5)

    monkeypatch.setattr(_analysis, "run", fake_run)
    probe = SimpleNamespace(check=lambda slug, argv: SimpleNamespace(
        usable=True, version="1", outcome=Outcome.RAN, detail=""))
    analysis = _analysis.Analysis()

    coverage = _analysis._attempt(tmp_path, _PerFile(files), probe, 60, analysis)

    assert len(calls) > 1
    assert sorted(m.unit for m in analysis.measurements) == sorted(files)
    assert coverage.measurements == len(files)
    assert coverage.duration_seconds == 0.5 * len(calls)
