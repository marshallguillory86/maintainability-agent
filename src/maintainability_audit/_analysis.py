"""Running the analyzer pool, and reporting what it covered — ADR 006.

Ties the three pieces together: `_catalog` decides which tools are permitted
and wanted, `_runner` proves which are actually usable and executes them, and
`_adapters` reads what they said. What comes back is a **coverage record** —
every tool attempted, its outcome, its version, and what it produced.

The coverage record is not an appendix. A score computed from four tools and
one computed from forty are not the same measurement, so coverage sits beside
the score or the score cannot be interpreted. This is P8, and it is the
concept whose absence let a repository with six shallow built-in checks report
5.0/A+: "twelve analyzers found nothing" and "one detector found nothing" were
indistinguishable in the output.

Nothing here can fail an audit. Every tool that is missing, broken, slow or
unreadable becomes a stated outcome, because a tool that did not run is not a
clean result.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._adapters import Extraction, Finding, Measurement, adapter_for, measurements_only
from ._catalog import CONCERNS, PolicyError, resolve_pool, settings_from
from ._runner import Outcome, Probe, run


@dataclass(frozen=True)
class ToolCoverage:
    """One tool's contribution, or its stated absence."""

    slug: str
    outcome: str
    version: str | None = None
    detail: str = ""
    measurements: int = 0
    findings: int = 0
    concepts: tuple[str, ...] = ()
    duration_seconds: float = 0.0
    parse_error: str | None = None
    raw: str = ""
    truncated: bool = False

    @property
    def contributed(self) -> bool:
        return self.outcome == Outcome.RAN and not self.parse_error


@dataclass
class Analysis:
    """Everything the external analyzers produced, plus what they did not."""

    coverage: list[ToolCoverage] = field(default_factory=list)
    measurements: list[Measurement] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    depth: str = ""
    license_policy: str = ""
    concerns: tuple[str, ...] = ()
    # Set when the pool could not be resolved at all — a broken config,
    # a missing catalog. Distinct from "every tool was unavailable".
    error: str | None = None

    def measured_concepts(self) -> set[str]:
        """Concerns something actually examined.

        Derived from which tools *ran*, not from what they emitted. A tool
        that ran and found nothing examined its concern — reporting that
        as unexamined would be the absence-as-value defect this project
        exists to remove, arriving one layer out: "vulture found no dead
        code" is a result, and "nobody looked for dead code" is a gap, and
        collapsing them is exactly the mistake that produced the A+.
        """
        return {
            concept
            for item in self.coverage
            if item.contributed
            for concept in item.concepts
        }

    def gaps(self) -> list[str]:
        """Concerns the operator asked for that nothing spoke to.

        The honest gap is per concern, not per language: multi-language
        tools reach nearly everything, so "no coverage" is rare and
        misleading, while "nothing examined testing or types" is the fact
        a reader needs.
        """
        wanted = set(CONCERNS) if "all" in self.concerns else set(self.concerns)
        return sorted(wanted - self.measured_concepts())


def analyze(root: Path, config: dict[str, Any], probe: Probe | None = None) -> Analysis:
    """Run the configured analyzer pool over `root`.

    Never raises. A configuration this cannot resolve is recorded as an
    error on the result rather than thrown, so a bad analyzer block
    degrades the audit instead of ending it.
    """
    try:
        settings = settings_from(config)
        pool, _ = resolve_pool(config)
    except PolicyError as error:
        return Analysis(error=str(error))

    analysis = Analysis(
        depth=settings["depth"],
        license_policy=settings["license_policy"],
        concerns=tuple(settings["concerns"]),
    )
    probe = probe or Probe()
    timeout = int(settings["timeout_seconds"])
    # The same exclusions the built-in scan honours. Without them every
    # analyzer walks .venv and node_modules and reports vendored code as
    # the user's: vulture returned 517 dead-code findings here, all 517
    # inside .venv.
    excludes = tuple(config.get("paths", {}).get("exclude_patterns", ()))

    for tool in pool:
        adapter = adapter_for(tool["slug"])
        if adapter is None:
            # Selected but unwritten: the catalog and the adapter set are
            # allowed to disagree, and saying so beats pretending.
            analysis.coverage.append(ToolCoverage(
                slug=tool["slug"], outcome="no-adapter",
                detail="selected by policy but no adapter is implemented",
                concepts=tuple(tool["measures"]),
            ))
            continue
        analysis.coverage.append(_run_one(root, adapter, probe, timeout, analysis, excludes))

    analysis.coverage.sort(key=lambda item: item.slug)
    return analysis


def _run_one(root: Path, adapter: Any, probe: Probe, timeout: int,
             analysis: Analysis, excludes: tuple[str, ...] = ()) -> ToolCoverage:
    """One tool, start to finish. Cannot raise.

    The broad catch is deliberate and sits here rather than in the
    adapter. `BaseAdapter.parse` handles the *expected* shape-drift
    exceptions, which keeps its own failures diagnosable; this is the
    backstop for everything else — a bug in an adapter, an exotic OS
    error, a tool that returns something nobody anticipated. The module
    promises that no analyzer can fail an audit, and a promise with an
    unguarded path is not one.
    """
    try:
        return _attempt(root, adapter, probe, timeout, analysis, excludes)
    except Exception as error:  # noqa: BLE001 - the backstop is the point
        return ToolCoverage(
            slug=adapter.slug, outcome="failed", concepts=tuple(adapter.concepts),
            detail=(
                f"{adapter.slug} raised {type(error).__name__}: {error}. This is a "
                "defect in the adapter, not in the repository being audited; the "
                "concern it covers is reported unexamined."
            ),
        )


def _attempt(root: Path, adapter: Any, probe: Probe, timeout: int,
             analysis: Analysis, excludes: tuple[str, ...] = ()) -> ToolCoverage:
    available = probe.check(adapter.slug, adapter.version_argv())
    # A tool whose CLI has no version flag is still a tool. Falling back to
    # package metadata keeps the version record complete, which P1 now
    # depends on -- determinism is promised for *pinned* versions, so a
    # blank version is a hole in the promise rather than a cosmetic gap.
    # Metadata first where a distribution is declared: it is the tool a
    # `--help` probe cannot name, and recording a usage banner as the
    # version would put noise where P1 expects a pinned identifier.
    recorded = adapter.installed_version() or available.version
    if not available.usable:
        return ToolCoverage(
            slug=adapter.slug, outcome=available.outcome.value,
            detail=available.detail, concepts=tuple(adapter.concepts),
        )

    result = run(adapter.slug, adapter.invocation(root, excludes=excludes),
                 timeout_seconds=timeout)
    extraction = adapter.parse(result)
    _collect(extraction, adapter, analysis)

    return ToolCoverage(
        slug=adapter.slug,
        outcome=result.outcome.value,
        version=recorded,
        detail=result.detail,
        measurements=len(measurements_only(extraction, adapter)),
        findings=len(extraction.findings),
        concepts=tuple(adapter.concepts),
        duration_seconds=round(result.duration_seconds, 3),
        parse_error=extraction.parse_error,
        raw=extraction.raw,
        truncated=extraction.truncated,
    )


def _collect(extraction: Extraction, adapter: Any, analysis: Analysis) -> None:
    # `measurements_only` is the enforcement point, not a formality: a
    # verdict emitter that started returning measurements would silently
    # reintroduce threshold-contaminated rates.
    analysis.measurements.extend(measurements_only(extraction, adapter))
    analysis.findings.extend(extraction.findings)


def _relative(path: str, root: Path) -> str:
    """Repo-relative, so findings read and diff like the rest of the report.

    Tools are handed absolute paths and hand them back. Left as-is the
    report is unreadable, and two runs from different checkout
    directories produce diffs that are entirely path noise.
    """
    try:
        return str(Path(path).resolve().relative_to(root.resolve()))
    except (ValueError, OSError):
        return path


def findings_document(analysis: Analysis, root: Path) -> list[dict[str, Any]]:
    """Every located finding the analyzers produced, report-shaped.

    The point of running the tools. Coverage says *that* they ran;
    without this the report says nine analyzers examined the repository
    and then tells the reader nothing they found — which is worse than
    not running them, because it looks thorough.

    Sorted by path and line so the list is stable between runs and
    diffable, and carrying the producing tool so a reader can go back to
    the raw output behind any row.
    """
    return sorted(
        (
            {
                "concept": finding.concept,
                "path": _relative(finding.path, root),
                "line": finding.line,
                "message": finding.message,
                "tool": finding.tool,
                "rule": finding.rule,
            }
            for finding in analysis.findings
        ),
        key=lambda item: (item["path"], item["line"] or 0, item["tool"], item["message"]),
    )


def coverage_document(analysis: Analysis) -> dict[str, Any]:
    """The coverage section, as it appears in a report.

    Grouped by outcome because the reader's question is "what did and did
    not run", not "what happened to each of forty tools in catalog order".
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in analysis.coverage:
        entry: dict[str, Any] = {"tool": item.slug, "concepts": list(item.concepts)}
        if item.version:
            entry["version"] = item.version
        if item.contributed:
            entry["measurements"] = item.measurements
            entry["findings"] = item.findings
            entry["seconds"] = item.duration_seconds
        if item.parse_error:
            entry["parse_error"] = item.parse_error
        elif item.detail and not item.contributed:
            entry["detail"] = item.detail
        grouped["parse-error" if item.parse_error else item.outcome].append(entry)

    ran = [item for item in analysis.coverage if item.contributed]
    return {
        "selection": {
            "concerns": list(analysis.concerns),
            "depth": analysis.depth,
            "license_policy": analysis.license_policy,
        },
        # Two reports with different coverage are not comparable, so this
        # is stated beside the score rather than filed behind it.
        "tools_attempted": len(analysis.coverage),
        "tools_contributed": len(ran),
        "by_outcome": dict(grouped),
        "concepts_covered": sorted(analysis.measured_concepts()),
        # A concern nobody examined is Unknown, never clean. Naming it is
        # the difference between a gap and a silence.
        "concepts_unexamined": analysis.gaps(),
        "error": analysis.error,
    }
