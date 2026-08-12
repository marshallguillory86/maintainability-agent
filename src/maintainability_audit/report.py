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

from ._analysis import (
    analyze,
    coverage_document,
    findings_document,
    measurement_document,
)
from ._metrics_types import FileMetric, FunctionMetric
from .deadcode import dead_declarations
from .declarations import DECLARATION_SUFFIXES
from .duplication import duplicate_blocks, risk_findings
from .evidence import REPORT_SCHEMA_VERSION, SCHEMA_VERSION_KEY
from .git_tools import run_git
from .history import history_section
from .idioms import divergent_idioms
from .metrics import collect_metrics, hard_gate_failures, is_test_path
from .scoring import score_report
from .similarity import near_duplicate_findings
from .source import SourceIndex


def _count_status(metrics: list, status: str) -> int:
    return sum(1 for metric in metrics if metric.status == status)


def _split_by_test_path(metrics: list) -> tuple[list, list]:
    prod = [metric for metric in metrics if not is_test_path(metric.path)]
    test = [metric for metric in metrics if is_test_path(metric.path)]
    return prod, test


def report_summary(
    files: list[Path],
    file_metrics: list[FileMetric],
    function_metrics: list[FunctionMetric],
    duplicate_count: int,
    risk_count: int,
    gate_count: int,
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
    summary = report_summary(files, file_metrics, function_metrics, duplicate_count, risk_count, len(gates))
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
        return {"coverage": None, "findings": [], "measurements": {}}
    analysis = analyze(root, config)
    return {
        "coverage": coverage_document(analysis),
        "findings": findings_document(analysis, root),
        "measurements": measurement_document(analysis, root),
    }


def _add_full_counts(
    summary: dict[str, Any],
    root: Path,
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
    summary["near_duplicate_count"] = len(near_duplicates)
    summary["dead_code_count"] = len(dead)
    summary["idiom_concern_count"] = len(idioms)
    summary["has_readme"] = any(root.glob("README*"))
    summary["has_changelog"] = any(root.glob("CHANGELOG*"))
    summary["has_docs_dir"] = (root / "docs").is_dir()


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
        "git_branch": run_git(["branch", "--show-current"], root),
        "git_status_short": git_status,
        "mode": "changed-only" if only_paths is not None else "full",
        "changed_revspec": changed_revspec,
        # Beside the score, never behind it: two reports with different
        # analyzer coverage are not comparable (P8).
        "analyzer_coverage": analyzer["coverage"],
        # What the analyzers actually found. Coverage without findings
        # would report that nine tools examined the repository and then
        # tell the reader nothing they saw.
        "analyzer_findings": analyzer["findings"],
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


def build_report(
    root: Path,
    config: dict[str, Any],
    only_paths: set[str] | None = None,
    changed_revspec: str | None = None,
    external_findings: list[dict[str, Any]] | None = None,
    run_analyzers: bool = False,
) -> dict[str, Any]:
    """Assemble one report.

    ``run_analyzers`` invokes the external analyzer pool (ADR 006). Off by
    default while adapters are still being written: turning it on changes
    what every existing caller measures, and a coverage section listing
    five unimplemented adapters is worse than none. The CLI exposes it as
    ``--analyzers``.
    """
    analyzer = _analyzer_sections(root, config, run_analyzers)
    # One index for the whole audit: each file is read once and parsed
    # once, rather than once per scanner.
    source = SourceIndex()
    files, file_metrics, function_metrics = collect_metrics(root, config, only_paths, source)
    thresholds = config["thresholds"]
    dupes = duplicate_blocks(root, files, int(thresholds["duplicate_block_lines"]), source)
    near_duplicates = near_duplicate_findings(root, files, source)
    dead = dead_declarations(root, files, source)
    idioms = divergent_idioms(root, files, config, source)
    risks = risk_findings(root, files, config, source)
    git_status = run_git(["status", "--short"], root)
    gates, summary = _compute_gates_and_summary(
        root, config, git_status, files, file_metrics, function_metrics, len(dupes), len(risks)
    )
    missing_files = [path for path in config.get("expected_files", []) if not (root / path).exists()]
    largest_files = sorted(file_metrics, key=lambda metric: metric.lines, reverse=True)[:25]

    _add_full_counts(summary, root, near_duplicates, dead, idioms)
    report = _assemble(
        root, analyzer, summary, gates, missing_files, largest_files,
        file_metrics, function_metrics, risks, dupes, near_duplicates, dead, idioms,
        external_findings, git_status, only_paths, changed_revspec, config,
    )
    report["score"] = score_report(report)
    return report
