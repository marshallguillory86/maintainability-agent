"""The paths that actually run a tool — ADR 006.

The rest of the analysis suite exercises the record-keeping with
hand-built coverage objects. This drives the real execution path with stub
executables on `PATH`, because the branch that decides *what happened* is
the one that turns a broken tool into a clean result if it is wrong, and
a hand-built `ToolCoverage` can never catch that.

Stubs rather than real analyzers: a test that needs lizard installed is a
test that silently skips in CI, and a skipped test proves nothing while
looking like it proves something.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from maintainability_audit._adapters import BaseAdapter, Extraction
from maintainability_audit._analysis import analyze, coverage_document, measurement_document
from maintainability_audit._metrics_types import Measurement
from maintainability_audit._runner import ToolResult


def _stub(directory: Path, name: str, body: str) -> None:
    path = directory / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def stub_path(tmp_path, monkeypatch):
    binaries = tmp_path / "bin"
    binaries.mkdir()
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    return binaries


def _pool(monkeypatch, slugs: list[str], adapter_by_slug: dict[str, BaseAdapter]) -> None:
    from maintainability_audit import _analysis

    monkeypatch.setattr(
        _analysis, "resolve_pool",
        lambda _c: ([{"slug": s, "measures": ["complexity"]} for s in slugs], []),
    )
    monkeypatch.setattr(_analysis, "adapter_for", lambda slug: adapter_by_slug.get(slug))
    monkeypatch.setattr(_analysis, "declared_adapter", lambda _slug: None)


class _Echoing(BaseAdapter):
    """A metric emitter whose output is one measurement per stdout line."""

    def __init__(self, slug: str = "stubtool") -> None:
        super().__init__(slug=slug, emits="metric", executable=slug,
                         concepts=("complexity",))

    def _read(self, result: ToolResult) -> Extraction:
        return Extraction(measurements=tuple(
            Measurement(concept="complexity", unit=f"a.py::f{i}", value=float(i),
                        tool=self.slug, path="a.py")
            for i, _ in enumerate(result.stdout.split(), start=1)
        ))


def test_a_tool_selected_without_an_adapter_is_reported_not_skipped(
    tmp_path, monkeypatch
) -> None:
    """The catalog and the adapter set are allowed to disagree.

    Saying so beats pretending: a selected tool that silently vanished
    would overstate what ran.
    """
    _pool(monkeypatch, ["pmd"], {})
    analysis = analyze(tmp_path, {})

    assert len(analysis.coverage) == 1
    only = analysis.coverage[0]
    assert only.outcome == "no-adapter"
    assert not only.contributed
    assert "no adapter" in only.detail


def test_a_missing_executable_is_reported_with_its_outcome(tmp_path, monkeypatch) -> None:
    _pool(monkeypatch, ["stubtool"], {"stubtool": _Echoing()})
    analysis = analyze(tmp_path, {})

    assert analysis.coverage[0].outcome == "not-installed"
    assert not analysis.coverage[0].contributed
    assert analysis.gaps(), "a tool that never ran covers nothing"


def test_a_working_tool_contributes_and_is_recorded(tmp_path, stub_path, monkeypatch) -> None:
    _stub(stub_path, "stubtool", 'if [ "$1" = "--version" ]; then echo "stubtool 9.9"; '
                                 'else echo "one two three"; fi')
    _pool(monkeypatch, ["stubtool"], {"stubtool": _Echoing()})

    analysis = analyze(tmp_path, {})
    only = analysis.coverage[0]

    assert only.contributed
    assert only.version == "stubtool 9.9"
    assert only.measurements == 3
    assert len(analysis.measurements) == 3
    assert "complexity" in analysis.measured_concepts()


def test_a_tool_needing_config_it_cannot_find_is_not_a_clean_result(
    tmp_path, stub_path, monkeypatch
) -> None:
    """eslint's case, generalised.

    A tool that exits having done nothing because no configuration was
    present must not be recorded as having run and found nothing — that
    is a clean result nobody earned.
    """
    class _NeedsConfig(_Echoing):
        def has_config(self, root: Path) -> bool:
            return (root / "stub.config").exists()

    _stub(stub_path, "stubtool", 'echo "stubtool 1.0"')
    _pool(monkeypatch, ["stubtool"], {"stubtool": _NeedsConfig()})

    analysis = analyze(tmp_path, {})
    assert analysis.coverage[0].outcome == "no-config"
    assert not analysis.coverage[0].contributed
    assert "add one" in analysis.coverage[0].detail

    (tmp_path / "stub.config").write_text("{}", encoding="utf-8")
    assert analyze(tmp_path, {}).coverage[0].contributed


def test_a_timing_out_tool_is_recorded_rather_than_hanging(
    tmp_path, stub_path, monkeypatch
) -> None:
    _stub(stub_path, "stubtool", 'if [ "$1" = "--version" ]; then echo "stubtool 1.0"; '
                                 'else sleep 30; fi')
    _pool(monkeypatch, ["stubtool"], {"stubtool": _Echoing()})

    analysis = analyze(tmp_path, {"analyzers": {"timeout_seconds": 1}})

    assert analysis.coverage[0].outcome == "timed-out"
    assert not analysis.coverage[0].contributed


def test_the_measurement_document_summarises_rather_than_dumps(
    tmp_path, stub_path, monkeypatch
) -> None:
    """A thousand functions is a dataset, not a document.

    The distribution is what a reader can reason with; the full set stays
    in the findings and the retained raw output.
    """
    _stub(stub_path, "stubtool", 'if [ "$1" = "--version" ]; then echo "stubtool 1.0"; '
                                 'else echo "a b c d e"; fi')
    _pool(monkeypatch, ["stubtool"], {"stubtool": _Echoing()})

    analysis = analyze(tmp_path, {})
    document = measurement_document(analysis, tmp_path)

    assert set(document) == {"complexity"}
    entry = document["complexity"]
    assert entry["units"] == 5
    assert entry["tools"] == ["stubtool"]
    assert entry["single_source"] is True
    assert entry["tool_disagreement"] is None, (
        "one tool has no spread; zero would read as perfect agreement"
    )
    assert set(entry["distribution"]) == {"min", "median", "p90", "max"}


def test_coverage_survives_a_json_round_trip(tmp_path, stub_path, monkeypatch) -> None:
    """The coverage section ships inside the report, so it must serialise."""
    _stub(stub_path, "stubtool", 'if [ "$1" = "--version" ]; then echo "stubtool 1.0"; '
                                 'else echo "x"; fi')
    _pool(monkeypatch, ["stubtool"], {"stubtool": _Echoing()})

    document = coverage_document(analyze(tmp_path, {}))
    assert json.loads(json.dumps(document)) == document
