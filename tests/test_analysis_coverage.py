"""Coverage: what ran, what did not, and what nobody examined — ADR 006, P8.

A score from four tools and a score from forty are not the same measurement,
so coverage sits beside the score or the score cannot be interpreted. Its
absence is what let a repository with six shallow built-in checks report
5.0/A+: "twelve analyzers found nothing" and "one detector found nothing"
looked identical in the output.

The subtlest property here, and one this code got wrong on the first pass:
**a tool that ran and found nothing has examined its concern.** Deriving
coverage from emitted output rather than from what executed collapses "vulture
found no dead code" into "nobody looked for dead code" — the absence-as-value
defect, one layer out from where it was originally fixed.
"""

from __future__ import annotations

from pathlib import Path

from maintainability_audit._adapters import BaseAdapter, Extraction, Finding, Measurement
from maintainability_audit._analysis import (
    Analysis,
    ToolCoverage,
    analyze,
    coverage_document,
)
from maintainability_audit._runner import Outcome


def _ran(slug: str, concepts: tuple[str, ...], **kwargs) -> ToolCoverage:
    return ToolCoverage(slug=slug, outcome=Outcome.RAN.value, concepts=concepts, **kwargs)


def test_a_tool_that_found_nothing_still_covered_its_concern() -> None:
    """The bug this file exists to prevent.

    Coverage is about what executed, never about what came back. A clean
    result is a result.
    """
    analysis = Analysis(concerns=("dead-code",), coverage=[
        _ran("vulture", ("dead-code",), measurements=0, findings=0),
    ])

    assert "dead-code" in analysis.measured_concepts()
    assert analysis.gaps() == [], "a clean scan is not an unexamined concern"


def test_a_tool_that_did_not_run_covers_nothing() -> None:
    """The other half. Absence of a tool is not absence of a problem."""
    analysis = Analysis(concerns=("dead-code",), coverage=[
        ToolCoverage(slug="vulture", outcome=Outcome.NOT_INSTALLED.value,
                     concepts=("dead-code",), detail="not on PATH"),
    ])

    assert analysis.measured_concepts() == set()
    assert analysis.gaps() == ["dead-code"]


def test_a_tool_whose_output_could_not_be_read_covers_nothing() -> None:
    """A parse error is a gap, not a clean result.

    The tool executed, but nothing was learned from it, and treating that
    as coverage would credit an examination that did not happen.
    """
    analysis = Analysis(concerns=("complexity",), coverage=[
        _ran("lizard", ("complexity",), parse_error="output shape changed"),
    ])

    assert analysis.gaps() == ["complexity"]


def test_gaps_are_named_so_silence_is_never_read_as_health() -> None:
    analysis = Analysis(concerns=("all",), coverage=[_ran("lizard", ("complexity",))])
    document = coverage_document(analysis)

    assert "complexity" in document["concepts_covered"]
    for absent in ("testing", "types", "dead-code"):
        assert absent in document["concepts_unexamined"]


def test_coverage_states_the_selection_that_produced_it() -> None:
    """Depth and policy change the pool, so they change the meaning.

    Two reports with different selections are not comparable, and a
    reader cannot tell without being told.
    """
    document = coverage_document(Analysis(
        concerns=("complexity",), depth="baseline", license_policy="permissive",
    ))

    assert document["selection"] == {
        "concerns": ["complexity"], "depth": "baseline", "license_policy": "permissive",
    }


def test_every_attempted_tool_appears_with_an_outcome() -> None:
    """No tool may be silently dropped from the record."""
    analysis = Analysis(coverage=[
        _ran("lizard", ("complexity",)),
        ToolCoverage(slug="jscpd", outcome=Outcome.NOT_INSTALLED.value, detail="absent"),
        ToolCoverage(slug="pmd", outcome="no-adapter", detail="not implemented"),
    ])
    document = coverage_document(analysis)

    listed = {entry["tool"] for entries in document["by_outcome"].values() for entry in entries}
    assert listed == {"lizard", "jscpd", "pmd"}
    assert document["tools_attempted"] == 3
    assert document["tools_contributed"] == 1


def test_a_broken_config_degrades_the_audit_instead_of_ending_it(tmp_path: Path) -> None:
    """An analyzer block nobody can parse must not take the audit down.

    The built-in scan is still worth running, and a thrown exception here
    would lose it.
    """
    analysis = analyze(tmp_path, {"analyzers": {"depth": "nonsense"}})

    assert analysis.error
    assert "unknown depth" in analysis.error
    assert analysis.coverage == []


def test_a_verdict_emitter_contributes_no_measurements_through_analysis() -> None:
    """The enforcement point, exercised through the real collection path.

    Unit-testing `measurements_only` proves the helper; this proves the
    caller actually uses it.
    """
    from maintainability_audit._analysis import _collect

    analysis = Analysis()
    verdict = BaseAdapter(slug="v", emits="verdict", executable="v", concepts=("style",))
    extraction = Extraction(
        measurements=(Measurement(concept="style", unit="u", value=1.0, tool="v", path="a.py"),),
        findings=(Finding(concept="style", path="a.py", line=1, message="x", tool="v"),),
    )

    _collect(extraction, verdict, analysis)

    assert analysis.measurements == []
    assert len(analysis.findings) == 1


def test_a_broken_adapter_cannot_fail_the_audit(tmp_path: Path, monkeypatch) -> None:
    """The module promises no analyzer can fail an audit.

    A promise with an unguarded path is not one, and writing this test is
    what showed the code had one: an unexpected exception type from an
    adapter would have propagated and taken the whole run down.

    What must never happen is the other failure — a broken adapter
    yielding a *clean* result. The concern it covers is reported
    unexamined.
    """
    from maintainability_audit import _analysis

    class Exploding(BaseAdapter):
        def __init__(self) -> None:
            super().__init__(slug="boom", emits="metric", executable="boom",
                             concepts=("complexity",))

        def version_argv(self) -> tuple[str, ...]:
            raise RuntimeError("adapter is broken")

    monkeypatch.setattr(_analysis, "adapter_for", lambda _slug: Exploding())
    monkeypatch.setattr(
        _analysis, "resolve_pool",
        lambda _c: ([{"slug": "boom", "measures": ["complexity"]}], []),
    )

    analysis = analyze(tmp_path, {"analyzers": {"concerns": ["complexity"]}})

    assert len(analysis.coverage) == 1
    only = analysis.coverage[0]
    assert not only.contributed
    assert "RuntimeError" in only.detail
    assert "defect in the adapter" in only.detail
    assert analysis.gaps() == ["complexity"], "a broken adapter covers nothing"
