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

from maintainability_audit._adapters import BaseAdapter, Extraction
from maintainability_audit._analysis import (
    Analysis,
    ToolCoverage,
    analyze,
)
from maintainability_audit._documents import coverage_document
from maintainability_audit._metrics_types import Finding, Measurement
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
        # What selection composed (D15): both empty here because this
        # analysis carries no coverage rows at all.
        "runnable": [],
        "inventory_filtered": [],
    }


def test_every_attempted_tool_appears_with_an_outcome() -> None:
    """No tool may be silently dropped from the record."""
    analysis = Analysis(coverage=[
        _ran("lizard", ("complexity",)),
        ToolCoverage(slug="jscpd", outcome=Outcome.NOT_INSTALLED.value, detail="absent"),
        ToolCoverage(slug="pmd", outcome="no-adapter", detail="not implemented"),
    ])
    document = coverage_document(analysis)

    listed = {entry["tool"] for entries in document["by_outcome"].values()
              for entry in entries if entry["tier"] == "analyzer"}
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
    from maintainability_audit import _analysis, _selection

    class Exploding(BaseAdapter):
        def __init__(self) -> None:
            super().__init__(slug="boom", emits="metric", executable="boom",
                             concepts=("complexity",))

        def version_argv(self) -> tuple[str, ...]:
            raise RuntimeError("adapter is broken")

    monkeypatch.setattr(_selection, "adapter_for", lambda _slug: Exploding())
    monkeypatch.setattr(
        _analysis, "resolve_pool",
        lambda _c: ([{"slug": "boom", "measures": ["complexity"]}], []),
    )

    analysis = analyze(tmp_path, {"analyzers": {"concerns": ["complexity"]}})

    # Built-in detectors are always in the record, so the broken analyzer
    # is the single *analyzer*-tier entry rather than the only entry.
    analyzers = [item for item in analysis.coverage if item.tier == "analyzer"]
    assert len(analyzers) == 1
    only = analyzers[0]
    assert not only.contributed
    assert "RuntimeError" in only.detail
    assert "defect in the adapter" in only.detail
    # Not a gap — the built-in declaration-size detector still looked —
    # but no *analyzer* corroborated it, which is the fact under test.
    assert "complexity" not in analysis.measured_concepts()
    assert analysis.single_source_concerns() == ["complexity"]


def test_analyzer_findings_reach_the_report(tmp_path: Path) -> None:
    """Coverage without findings is worse than not running the tools.

    It reports that nine analyzers examined the repository and then tells
    the reader nothing they saw — thorough-looking and useless. This is
    the payload, and it was missing on the first pass: `_analysis`
    collected findings and nothing wrote them anywhere.
    """
    from maintainability_audit._documents import findings_document

    analysis = Analysis(findings=[
        Finding(concept="dead-code", path=str(tmp_path / "a.py"), line=7,
                message="unused import 'os'", tool="ruff", rule="F401"),
    ])
    document = findings_document(analysis, tmp_path)

    assert len(document) == 1
    only = document[0]
    assert only["path"] == "a.py", "paths are repo-relative or the report is unreadable"
    assert (only["line"], only["tool"], only["rule"]) == (7, "ruff", "F401")
    assert only["message"]


def test_findings_are_ordered_so_two_runs_diff_cleanly(tmp_path: Path) -> None:
    """Stable ordering, or every run's diff is noise."""
    from maintainability_audit._documents import findings_document

    def _finding(path: str, line: int, tool: str) -> Finding:
        return Finding(concept="style", path=str(tmp_path / path), line=line,
                       message="m", tool=tool)

    scrambled = Analysis(findings=[
        _finding("b.py", 1, "ruff"), _finding("a.py", 9, "ruff"),
        _finding("a.py", 2, "vulture"), _finding("a.py", 2, "ruff"),
    ])
    order = [(f["path"], f["line"], f["tool"]) for f in findings_document(scrambled, tmp_path)]

    assert order == sorted(order)


def test_a_path_outside_the_root_is_kept_rather_than_mangled(tmp_path: Path) -> None:
    """Relativising must not corrupt what it cannot place.

    A tool may report a path outside the tree — a config elsewhere, a
    symlink target. Losing it would be worse than showing it absolute.
    """
    from maintainability_audit._documents import findings_document

    outside = Analysis(findings=[
        Finding(concept="style", path="/elsewhere/x.py", line=1, message="m", tool="ruff"),
    ])

    assert findings_document(outside, tmp_path)[0]["path"] == "/elsewhere/x.py"


def _no_analyzers(**extra: object) -> dict[str, object]:
    """A config that selects the built-in tier and nothing else.

    Built by denying whatever the default pool resolves to, so the test
    keeps meaning "no external tool ran" when the catalog changes rather
    than quietly admitting a newly-added analyzer.
    """
    from maintainability_audit._catalog import resolve_pool

    pool, _ = resolve_pool({})
    return {"analyzers": {"deny_tools": [tool["slug"] for tool in pool], **extra}}


def test_the_built_in_detectors_appear_in_the_coverage_record(tmp_path: Path) -> None:
    """A reader asking what examined this code is owed the whole answer.

    The built-ins were demoted, not deleted (ADR 006 §2). While they were
    absent from coverage, the section described the external half of the
    work and silently implied the other half did not happen — a report
    that under-claims its own evidence is still a report that misleads.
    """
    from maintainability_audit._built_ins import BUILT_IN_SOURCES

    (tmp_path / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    document = coverage_document(analyze(tmp_path, _no_analyzers()))

    listed = {entry["tool"]: entry for entries in document["by_outcome"].values()
              for entry in entries if entry["tier"] == "built-in"}
    assert set(listed) == {slug for slug, _, _ in BUILT_IN_SOURCES}
    assert document["sources"] == {"built_in": len(BUILT_IN_SOURCES), "analyzers": 0}
    # The tool counts stay a statement about the analyzer pool, or
    # "3 of 12 tools ran" would quietly become "11 of 20".
    assert document["tools_attempted"] == 0


def test_a_concern_only_a_built_in_reached_is_neither_covered_nor_a_gap(
    tmp_path: Path,
) -> None:
    """Three states, not two: corroborated, single-source, unexamined.

    Collapsing single-source into covered would let a fallback stand in
    for independent evidence. Collapsing it into a gap would claim
    nobody looked when something did. Both are the same lie in opposite
    directions, so the report carries all three.
    """
    (tmp_path / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    analysis = analyze(tmp_path, _no_analyzers(concerns=["duplication"]))

    assert analysis.measured_concepts() == set()
    assert analysis.single_source_concerns() == ["duplication"]
    assert analysis.gaps() == []


def test_no_built_in_claims_to_be_unique_when_an_adapter_exists() -> None:
    """The uniqueness claims are held to the registry, not to memory.

    Each built-in's note says either "no adapter emits this" or names the
    tools that do. Those notes were written against the adapter list on
    one particular day; the day an adapter for churn or file_lines lands,
    the note becomes false and nothing else would notice.
    """
    from maintainability_audit._built_ins import BUILT_IN_SOURCES
    from maintainability_audit._generic import DECLARED
    from maintainability_audit._tool_adapters import ADAPTERS

    emitted = {concept for factory in ADAPTERS.values()
               for concept in factory().concepts}
    emitted |= {concern for spec in DECLARED.values() for concern in spec.concerns}

    claimed_unique = {
        concept
        for _, concepts, note in BUILT_IN_SOURCES
        for concept in concepts
        if "no adapter emits" in note
    }
    assert claimed_unique and not claimed_unique & emitted, (
        f"an adapter now emits {sorted(claimed_unique & emitted)}; the built-in's "
        "note claims nothing external does"
    )

    # And the converse: a built-in that names its external equivalents
    # must actually have them, or the demotion is on paper only.
    shared = {
        concept
        for _, concepts, note in BUILT_IN_SOURCES
        for concept in concepts
        if "no adapter emits" not in note and "config" not in note
    }
    assert shared <= emitted, f"claimed covered but nothing emits {sorted(shared - emitted)}"


def test_a_built_in_row_reports_the_population_it_examined(tmp_path: Path) -> None:
    """`0 measurements, 0 findings` is the defect, inside the table built to stop it.

    Coverage rows are assembled before the scan finishes, so every
    built-in shipped zeros — a detector that examined 981 declarations
    and found 16 problems appeared to have examined nothing. Read from
    the same summary the scorer consumes, so the table cannot disagree
    with the score computed beside it.
    """
    from maintainability_audit._built_ins import BUILT_IN_COUNTS, record_built_in_counts

    coverage = {"by_outcome": {"ran": [
        {"tool": "declaration-size", "tier": "built-in", "measurements": 0, "findings": 0},
        {"tool": "lizard", "tier": "analyzer", "measurements": 7, "findings": 0},
    ]}}
    report = {
        "summary": {"declarations_scanned": 981, "function_failures": 11,
                    "function_warnings": 5},
        "history": {"files_changed": 3, "qualifying_hotspots": 1, "code_coupling_pairs": 2},
    }

    record_built_in_counts(coverage, report)
    rows = {row["tool"]: row for row in coverage["by_outcome"]["ran"]}

    assert rows["declaration-size"]["measurements"] == 981
    assert rows["declaration-size"]["findings"] == 16, "failures and warnings both count"
    assert rows["lizard"]["measurements"] == 7, "an analyzer row is not rewritten"
    # Every built-in that reports counts must have a source for them, or
    # it silently keeps its zeros.
    from maintainability_audit._built_ins import BUILT_IN_SOURCES

    assert {slug for slug, _, _ in BUILT_IN_SOURCES} - set(BUILT_IN_COUNTS) == {"history"}


def test_history_without_a_git_tree_is_unmeasured_not_quiet(tmp_path: Path) -> None:
    """A shallow clone has no churn to report and no right to say zero."""
    from maintainability_audit._built_ins import record_built_in_counts

    coverage = {"by_outcome": {"ran": [
        {"tool": "history", "tier": "built-in", "measurements": 0, "findings": 0},
    ]}}
    record_built_in_counts(coverage, {"summary": {}, "history": None})
    # Regrouped, not just relabelled — every renderer reads the bucket.
    row = coverage["by_outcome"]["no-history"][0]

    assert row["outcome"] == "no-history"
    assert "unmeasured rather than absent" in row["detail"]


def test_a_row_whose_outcome_changes_moves_to_that_outcomes_group() -> None:
    """The grouping is the display; changing a field under it is not enough.

    `by_outcome` buckets rows before the history section is known, so
    setting `entry["outcome"] = "no-history"` left the row sitting in the
    `ran` bucket. Every renderer reads the bucket key, not the field, so
    a shallow clone of `kilo` printed `history ... ran, 0 measurements` —
    "looked and found no churn" instead of "could not look". Found by
    running the tool on a real repository, which is what the validation
    sample is for.
    """
    from maintainability_audit._built_ins import record_built_in_counts

    coverage = {"by_outcome": {"ran": [
        {"tool": "history", "tier": "built-in", "measurements": 0, "findings": 0},
        {"tool": "file-size", "tier": "built-in", "measurements": 0, "findings": 0},
    ]}}
    record_built_in_counts(coverage, {"summary": {"files_scanned": 9}, "history": None})

    assert [row["tool"] for row in coverage["by_outcome"]["no-history"]] == ["history"]
    assert [row["tool"] for row in coverage["by_outcome"]["ran"]] == ["file-size"]
