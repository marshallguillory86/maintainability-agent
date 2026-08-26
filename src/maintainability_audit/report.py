"""Assembling the audit report: summary counters, gates, and the JSON body.

Extracted from ``metrics.py`` (2026-08-06). This is the top of the
dependency graph — it pulls together the file scan (``metrics``), the
declaration scan (``declarations``), the corpus scans (``duplication``),
and the score (``scoring``) into the single dict every renderer consumes.
Nothing else in the package imports it, so it is the right place for the
orchestration to live.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path, PurePosixPath
from typing import Any

from ._analysis import analyze
from ._built_ins import record_built_in_counts
from ._discovery import Provenance, discover
from ._documents import (
    coverage_document,
    findings_document,
    measurement_document,
    unidentified_source_paths,
)
from ._economics import economic_context_from, economic_impact, reorder_by_exposure
from ._environment import environment_work_order
from ._metrics_types import FileMetric, FunctionMetric
from ._pillars import pillar_report
from ._practice import practice_level
from ._pressures import (
    ExternalPressures,
    analyzer_pressures,
    analyzer_production_pressures,
)
from ._semantic import semantic_findings
from ._semantic_policy import load_semantic_policy
from ._semantic_ts import discover_type_analysis
from ._work_order import work_order
from .config import analyzers_run_default
from .deadcode import dead_declarations
from .declarations import DECLARATION_SUFFIXES
from .duplication import duplicate_blocks, risk_findings
from .evidence import REPORT_SCHEMA_VERSION, SCHEMA_VERSION_KEY
from .git_tools import probe_git
from .history import history_section
from .idioms import divergent_idioms
from .metrics import (
    collect_metrics,
    hard_gate_failures,
    is_test_path,
    undetected_declarations,
    unread_source,
)
from .scoring import score_report
from .similarity import near_duplicate_findings
from .source import SourceIndex


def _count_status(metrics: list, status: str) -> int:
    return sum(1 for metric in metrics if metric.status == status)


def _split_by_test_path(metrics: list) -> tuple[list, list]:
    prod = [metric for metric in metrics if not is_test_path(metric.path)]
    test = [metric for metric in metrics if is_test_path(metric.path)]
    return prod, test


def _band_pressures(
    file_metrics: list[FileMetric],
    function_metrics: list[FunctionMetric],
    thresholds: dict[str, Any],
) -> dict[str, float | None]:
    """Per-unit measurements through the band matrix (ADR 008, 3.2).

    Computed here because this is the last point that still holds every
    declaration's actual numbers; the summary otherwise reduces them to
    counts, and counts cannot tell complexity 16 from 45. Classes are
    excluded from the declaration population: their complexity is the sum
    of branches already charged to their methods, and their line budget
    uses different threshold keys than `CONCEPTS` anchors on.
    """
    from ._bands import CONCEPTS, population_pressure, unit_pressure

    def declarations(metrics: list[FunctionMetric]) -> float | None:
        pressures = [
            unit_pressure({
                "cyclomatic_complexity": float(m.complexity),
                "declaration_lines": float(m.lines),
                "cognitive_complexity": float(m.cognitive),
            }, thresholds)
            for m in metrics if m.kind != "class"
        ]
        known = [value for value in pressures if value is not None]
        return sum(known) / len(known) if known else None

    def file_size(metrics: list[FileMetric]) -> float | None:
        return population_pressure(
            CONCEPTS["file_lines"], [float(m.lines) for m in metrics], thresholds
        )

    prod_files = [m for m in file_metrics if not is_test_path(m.path)]
    prod_funcs = [m for m in function_metrics if not is_test_path(m.path)]
    return {
        "declaration_band_pressure": declarations(function_metrics),
        "production_declaration_band_pressure": declarations(prod_funcs),
        "file_band_pressure": file_size(file_metrics),
        "production_file_band_pressure": file_size(prod_files),
    }


def report_summary(
    files: list[Path],
    file_metrics: list[FileMetric],
    function_metrics: list[FunctionMetric],
    duplicate_count: int,
    risk_count: int,
    gate_count: int,
    thresholds: dict[str, Any] | None = None,
) -> dict[str, int]:
    prod_files, test_files = _split_by_test_path(file_metrics)
    prod_funcs, test_funcs = _split_by_test_path(function_metrics)
    return {
        "files_scanned": len(files),
        # Denominators. Scoring works in rates, so it needs the size of
        # the population a finding count is drawn from — 20 oversized
        # functions mean something different in a 50-file repo than in
        # Django.
        "declarations_scanned": len(function_metrics),
        "production_files_scanned": len(prod_files),
        "production_declarations_scanned": len(prod_funcs),
        "file_warnings": _count_status(file_metrics, "warn"),
        "file_failures": _count_status(file_metrics, "fail"),
        "function_warnings": _count_status(function_metrics, "warn"),
        "function_failures": _count_status(function_metrics, "fail"),
        "production_file_warnings": _count_status(prod_files, "warn"),
        "production_file_failures": _count_status(prod_files, "fail"),
        "production_function_warnings": _count_status(prod_funcs, "warn"),
        "production_function_failures": _count_status(prod_funcs, "fail"),
        # Source files only. A Markdown file under tests/ is
        # documentation, and an audit found that any path-matching file —
        # including an empty one — bought testability points. Suffix
        # filtering closes the empty-artifact hole; the scorer separately
        # requires the files to contain declarations.
        "test_file_count": sum(
            1 for metric in test_files if PurePosixPath(metric.path).suffix in DECLARATION_SUFFIXES
        ),
        "test_function_warnings": _count_status(test_funcs, "warn"),
        "test_function_failures": _count_status(test_funcs, "fail"),
        "duplicate_blocks": duplicate_count,
        "risk_findings": risk_count,
        "hard_gate_failures": gate_count,
        # Banded pressures, beside the counts they refine rather than
        # replacing them: the counts still drive the binary gates, and a
        # consumer of an old report simply finds these absent.
        **(_band_pressures(file_metrics, function_metrics, thresholds)
           if thresholds is not None else {}),
    }


def _compute_gates_and_summary(
    root: Path,
    config: dict[str, Any],
    git_status: str,
    files: list[Path],
    file_metrics: list[FileMetric],
    function_metrics: list[FunctionMetric],
    duplicate_count: int,
    risk_count: int,
) -> tuple[list[str], dict[str, int]]:
    # The gate list shown to users still includes every failure
    # (prod + test). But scoring uses a production-only gate count so
    # a long test function never drags testability/analyzability down.
    failed_files = [metric for metric in file_metrics if metric.status == "fail"]
    failed_functions = [metric for metric in function_metrics if metric.status == "fail"]
    prod_failed_files = [metric for metric in failed_files if not is_test_path(metric.path)]
    prod_failed_functions = [metric for metric in failed_functions if not is_test_path(metric.path)]
    gates = hard_gate_failures(root, config, git_status, failed_files, failed_functions, duplicate_count)
    production_gates = hard_gate_failures(
        root, config, git_status, prod_failed_files, prod_failed_functions, duplicate_count
    )
    summary = report_summary(files, file_metrics, function_metrics, duplicate_count,
                             risk_count, len(gates), thresholds=config["thresholds"])
    summary["production_hard_gate_failures"] = len(production_gates)
    return gates, summary


def _function_hotspots(function_metrics: list[FunctionMetric]) -> list[dict[str, Any]]:
    flagged = [metric for metric in function_metrics if metric.status in {"warn", "fail"}]
    flagged.sort(key=lambda metric: (metric.status != "fail", -metric.complexity, -metric.lines))
    return [asdict(metric) for metric in flagged[:50]]


def _analyzer_sections(
    root: Path, config: dict[str, Any], run_analyzers: bool
) -> dict[str, Any]:
    """The three analyzer sections, or their empty forms.

    Extracted because `build_report` reached complexity 15 against this
    project's own limit. Four conditionals all asking the same question
    belong behind one, and the empty forms are stated here rather than
    repeated at each call site.
    """
    if not run_analyzers:
        return {"coverage": None, "findings": [], "measurements": {},
                "pressures": None, "environment": []}
    analysis = analyze(root, config)
    return {
        "coverage": coverage_document(analysis),
        # ADR 006 §2c: what did not run and what it would take, for the
        # user to act on. Emitted here because only the analysis knows
        # which tools were *selected*; the agent never runs the commands.
        "environment": environment_work_order(analysis.coverage),
        "findings": findings_document(analysis, root),
        # Path spellings normalization refused (zero or several matches)
        # — visible, so a refusal is never mistaken for an identification.
        "unidentified_source_paths": unidentified_source_paths(analysis, root),
        "measurements": measurement_document(analysis, root),
        # The analyzers' reading of the scorer's own dimensions, and the
        # primary source for every dimension it covers (ADR 006 §1).
        # Where it is None the built-in detector's reading stands, so a
        # dimension nobody measured is unmeasured rather than clean.
        # Both populations, because the scorer keeps both and the
        # production aspects are the ones that actually read this.
        "pressures": ExternalPressures(
            all_code=analyzer_pressures(analysis.measurements, config["thresholds"]),
            production=analyzer_production_pressures(
                analysis.measurements, config["thresholds"]),
            # The raw readings ride along so the scorer can price
            # per-concept tool disagreement into the range (3.4).
            measurements=tuple(analysis.measurements),
        ),
    }


def _add_full_counts(
    summary: dict[str, Any],
    root: Path,
    config: dict[str, Any],
    near_duplicates: list[Any],
    dead: list[Any],
    idioms: list[Any],
) -> None:
    """Counts the rubric reads, taken before display lists are truncated.

    Separated because `build_report` ran to 99 lines against this
    project's own 80-line limit. These are one job: everything the scorer
    needs that the display lists would otherwise have capped.

    Taken before truncation to 25 deliberately -- a rate computed from a
    capped list would flatten exactly the repositories the score exists
    to distinguish.
    """
    # What the scan could not read, before anything is scored on what it
    # could. A repository whose source is invisible to `include_extensions`
    # still produces files, declarations and a tidy-looking rate — drawn
    # from its Markdown and its scripts.
    breakdown, read = unread_source(root, config)
    summary["unread_source"] = breakdown
    summary["unread_source_files"] = sum(entry["files"] for entry in breakdown)
    summary["read_source_files"] = read
    # Opened, but not parseable for declarations. Between read and
    # unread, and the state that made a 40-file Java repository report
    # that it was smaller than the calibration set.
    blind = undetected_declarations(root, config)
    summary["undetected_declarations"] = blind
    summary["undetected_declaration_files"] = sum(entry["files"] for entry in blind)
    summary["near_duplicate_count"] = len(near_duplicates)
    summary["dead_code_count"] = len(dead)
    summary["idiom_concern_count"] = len(idioms)
    summary["has_readme"] = any(root.glob("README*"))
    summary["has_changelog"] = any(root.glob("CHANGELOG*"))
    summary["has_docs_dir"] = (root / "docs").is_dir()


def _add_inventory(summary: dict[str, Any], inventory: Any) -> None:
    """What the tree is made of, beside what was measured in it.

    Counted, not just excluded. "600 files were not yours" is a fact a
    reader needs in order to interpret every number beside it, and
    silently dropping them would replace one kind of dishonesty with
    another.
    """
    counts = inventory.counts()
    summary["languages"] = dict(sorted(inventory.languages.items(),
                                       key=lambda item: (-item[1], item[0])))
    summary["generated_files"] = counts[Provenance.GENERATED.value]
    summary["vendored_files"] = counts[Provenance.VENDORED.value]
    summary["classifications"] = inventory.classifications


def _provenance(
    root: Path, git_status: str, only_paths: set[str] | None, changed_revspec: str | None
) -> dict[str, Any]:
    """Which tree this report describes, and how much of it was examined.

    Grouped because `_assemble` crossed this project's own 80-line
    function limit when the commit was added, and because these five
    fields answer one question — *what was audited* — that the rest of
    the document assumes an answer to.
    """
    return {
        # Probed: a directory that is not a repository is a supported
        # audit target, so a failing git command is an expected answer
        # rather than the D37 fault.
        "git_branch": probe_git(["branch", "--show-current"], root),
        # The commit this report describes. Without it a scan history is
        # a list of scores with no anchor, and recurrence — "cleared,
        # then returned, in these commits" — has nothing to name.
        "git_commit": probe_git(["rev-parse", "HEAD"], root),
        "git_status_short": git_status,
        "mode": "changed-only" if only_paths is not None else "full",
        "changed_revspec": changed_revspec,
    }


def _assemble(
    root: Path,
    analyzer: dict[str, Any],
    summary: dict[str, Any],
    gates: list[str],
    missing_files: list[str],
    largest_files: list[Any],
    file_metrics: list[Any],
    function_metrics: list[Any],
    risks: list[Any],
    dupes: list[Any],
    near_duplicates: list[Any],
    dead: list[Any],
    idioms: list[Any],
    external_findings: list[dict[str, Any]] | None,
    git_status: str,
    only_paths: set[str] | None,
    changed_revspec: str | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    """The report document, assembled in one place.

    Split from `build_report` when it reached 99 lines against this
    project's own 80-line limit. Scanning and assembly were two jobs
    sharing a function: everything above gathers evidence, this shapes
    it into the published contract.
    """
    return {
        # The report structure's own version, owned here and validated
        # by ``evidence.normalize_report_evidence``. Distinct from the
        # baseline file's ``version``, which numbers a different
        # artifact with a different lifecycle. See
        # docs/report-contract.md for the compatibility policy.
        SCHEMA_VERSION_KEY: REPORT_SCHEMA_VERSION,
        "root": str(root),
        **_provenance(root, git_status, only_paths, changed_revspec),
        # Beside the score, never behind it: two reports with different
        # analyzer coverage are not comparable (P8).
        "analyzer_coverage": analyzer["coverage"],
        "environment_work_order": analyzer["environment"],
        # What the analyzers actually found. Coverage without findings
        # would report that nine tools examined the repository and then
        # tell the reader nothing they saw.
        "analyzer_findings": analyzer["findings"],
        "unidentified_source_paths": analyzer.get("unidentified_source_paths", []),
        # Measurements and their distributions, kept alongside the counts
        # the score consumes. Collapsing everything into counts would
        # discard the shape a reader needs.
        "analyzer_measurements": analyzer["measurements"],
        "summary": summary,
        "hard_gate_failures": gates,
        "missing_files": missing_files,
        "largest_files": [asdict(metric) for metric in largest_files],
        "function_hotspots": _function_hotspots(function_metrics),
        "duplicate_blocks": dupes[:25],
        # Feeds the near_duplication rubric aspect (rate over production
        # declarations, banded — not median-normalized, since most repos
        # sit at zero). NOT evidence about authorship: the 0.6.0 claim
        # that this rate separates AI-written from human code is
        # retracted (matched control, p = 0.546; docs/studies.md "Does
        # this detect AI-written code?").
        "near_duplicates": near_duplicates[:25],
        # Feeds the dead_code rubric aspect. Also not evidence about
        # authorship (p = 0.266 against the matched control).
        "dead_code": dead[:25],
        # Quiet by design: zero findings across the whole reference
        # corpus, one on a repo genuinely running two HTTP clients. High
        # precision, low recall — the right trade here.
        "divergent_idioms": idioms,
        "risk_findings": [asdict(finding) for finding in risks[:100]],
        # Churn, hotspots (churn x cognitive complexity) and change
        # coupling from the repo's own log. Feeds the churn_hotspots,
        # change_coupling and knowledge_concentration aspects of the
        # scoring rubric. None — not empty — when the clone is shallow:
        # "no history" and "no changes" are opposite findings, and the
        # rubric renormalizes those aspects away rather than guessing.
        "history": history_section(root, file_metrics, function_metrics),
        "external_findings": external_findings or [],
    }


def _attach_semantics(report: dict[str, Any], root: Path, config: dict[str, Any]) -> None:
    """ADR 003 option C, after the score is sealed and before the work
    order reads it: semantic results are findings and prompt material,
    never rubric input — nothing from here reaches `score_report`.
    """
    semantic = semantic_findings(
        root,
        policy=load_semantic_policy(config),
        type_analysis=discover_type_analysis(root),
    )
    report["semantic_findings"] = semantic["findings"]
    report["semantic_coverage"] = semantic["coverage"]


def build_report(
    root: Path,
    config: dict[str, Any],
    only_paths: set[str] | None = None,
    changed_revspec: str | None = None,
    external_findings: list[dict[str, Any]] | None = None,
    run_analyzers: bool | None = None,
) -> dict[str, Any]:
    """Assemble one report.

    ``run_analyzers`` invokes the external analyzer pool (ADR 006) and is
    tri-state at this seam, the same as MCP's (D1): ``None`` — the
    default — obeys the config's ``analyzers.run``, so a direct caller
    holding a configured repository's config gets the configured pool,
    not a silent fallback. Explicit ``True``/``False`` wins for one call.
    A complete concept set moves the point estimate; a partial one stays
    on the built-in fallback and the range widens to contain both.
    """
    if run_analyzers is None:
        run_analyzers = analyzers_run_default(config)
    analyzer = _analyzer_sections(root, config, run_analyzers)
    # Before anything is measured: what languages are here, and whose
    # code is it. Everything downstream reads this rather than guessing
    # from directory names, which is what let a vendored tree and 10,759
    # generated files into a repository's score.
    inventory = discover(root, config)
    not_ours = {
        path for path, verdict in inventory.provenance.items()
        if verdict in (Provenance.GENERATED, Provenance.VENDORED)
    }
    # One index for the whole audit: each file is read once and parsed
    # once, rather than once per scanner.
    source = SourceIndex()
    files, file_metrics, function_metrics = collect_metrics(
        root, config, only_paths, source, excluded=not_ours)
    thresholds = config["thresholds"]
    dupes = duplicate_blocks(root, files, int(thresholds["duplicate_block_lines"]), source)
    near_duplicates = near_duplicate_findings(root, files, source)
    dead = dead_declarations(root, files, source)
    idioms = divergent_idioms(root, files, config, source)
    risks = risk_findings(root, files, config, source)
    git_status = probe_git(["status", "--short"], root)
    gates, summary = _compute_gates_and_summary(
        root, config, git_status, files, file_metrics, function_metrics, len(dupes), len(risks)
    )
    missing_files = [path for path in config.get("expected_files", []) if not (root / path).exists()]
    largest_files = sorted(file_metrics, key=lambda metric: metric.lines, reverse=True)[:25]

    _add_full_counts(summary, root, config, near_duplicates, dead, idioms)
    _add_inventory(summary, inventory)
    report = _assemble(
        root, analyzer, summary, gates, missing_files, largest_files,
        file_metrics, function_metrics, risks, dupes, near_duplicates, dead, idioms,
        external_findings, git_status, only_paths, changed_revspec, config,
    )
    # After assembly, because the history section is the last input the
    # built-in coverage rows need. Without it those rows shipped zeros.
    if analyzer["coverage"]:
        record_built_in_counts(analyzer["coverage"], report)
    report["score"] = score_report(report, analyzer["pressures"])
    # After scoring, because condition rolls up the aspect scores. The two
    # axes stay separate all the way out (ADR 007 §2): practice says
    # whether anything is enforced, condition says what the analyzers
    # found, and no field anywhere offers their mean.
    report["practice"] = practice_level(root).as_dict()
    report["pillars"] = pillar_report(report["score"], report["practice"])
    _attach_semantics(report, root, config)
    # Last, because every item's delta is a rubric recomputation and the
    # rubric needs the scored report to recompute against.
    report["work_order"] = work_order(report)
    # ADR 004 v1, after scoring on purpose: nothing money-shaped exists
    # until the score document is final, so no path from these numbers
    # into the estimate or the grade can exist to be misused.
    context = economic_context_from(config)
    if context is not None:
        report["economic_impact"] = economic_impact(report, context)
        reorder_by_exposure(report)
    return report
