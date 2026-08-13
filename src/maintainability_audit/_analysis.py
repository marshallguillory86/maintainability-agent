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
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ._adapters import Extraction, measurements_only
from ._built_ins import BUILT_IN_SOURCES
from ._catalog import CONCERNS, PolicyError, concepts_for, resolve_pool, settings_from
from ._corroborate import agreement, combine, single_source_concepts
from ._discovery import CATALOG_LANGUAGE, discover
from ._generic import declared_adapter
from ._metrics_types import KNOWN_SOURCE_SUFFIXES, Finding, Measurement
from ._runner import Outcome, Probe, run
from ._tool_adapters import adapter_for


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
    # Which tier produced this: "analyzer" for an external tool, "built-in"
    # for one of this package's own detectors. Built-ins belong in the
    # record because they reach concepts no adapter emits — per-file line
    # counts, configured risk patterns, competing libraries, churn and
    # ownership — and because they are the only source at all when no
    # analyzer is installed. Omitting them made the coverage section
    # describe a fraction of what actually examined the code.
    tier: str = "analyzer"
    # The catalog languages this tool reads, in the catalog's vocabulary.
    # Carried on the record because coverage is claimed per language: a
    # Python-only linter covers nothing for C++ at any language mix, and
    # that fact is unrecoverable once the pool is out of scope.
    languages: tuple[str, ...] = ()
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
    # Languages present in the tree, display name -> catalog slug, from
    # the discovery pass. Empty when nothing recognisable was found, in
    # which case per-language coverage has nothing to key on and the
    # repository-wide answer stands alone.
    languages: dict[str, str] = field(default_factory=dict)
    # The subset of those languages the scan actually scored, i.e. whose
    # extensions are in `include_extensions`. Coverage describes what was
    # scored: a language the scan never opened is reported by the
    # unread-source rule and must not also rewrite the coverage claim.
    scored_languages: tuple[str, ...] = ()
    # Set when the pool could not be resolved at all — a broken config,
    # a missing catalog. Distinct from "every tool was unavailable".
    error: str | None = None

    def _concerns_from(self, tier: str) -> set[str]:
        """Concerns examined by one tier of source."""
        # Adapters declare *concepts* (cyclomatic_complexity) while users
        # select *concerns* (complexity), so the two vocabularies are
        # mapped rather than compared directly. Comparing them made
        # `metrics` and `structure` read as unexamined the moment concepts
        # were split out — a gap report that invents gaps is as bad as one
        # that hides them.
        measured = {
            concept
            for item in self.coverage
            if item.contributed and item.tier == tier
            for concept in item.concepts
        }
        return {
            concern
            for concern in CONCERNS
            if measured & set(concepts_for(concern))
        } | (measured & set(CONCERNS))

    def coverage_by_language(self) -> dict[str, set[str]]:
        """Concerns examined, per language present in the tree.

        The honest unit. `json` holds 6 Python files among 305 C++ ones,
        and a repository-wide union let that one file claim `types` for
        the whole tree — a reader concludes their C++ is type-checked.

        Deliberately not a share threshold. "mypy covers types for
        Python" is true at 2% Python and at 98%, so there is no cutoff to
        tune and no way for a rule fitted to one repository to distort
        another. `test_the_answer_does_not_depend_on_the_language_mix`
        holds exactly that.
        """
        covered: dict[str, set[str]] = {name: set() for name in self.languages}
        for item in self.coverage:
            if not item.contributed or item.tier != "analyzer":
                continue
            concerns = self._concerns_of(item.concepts)
            for name, slug in self.languages.items():
                # No declared languages means the catalog does not say,
                # and an unstated capability is not evidence of absence:
                # the tool counts wherever it ran, as it did before.
                if not item.languages or slug in item.languages:
                    covered[name] |= concerns
        return covered

    def gaps_by_language(self) -> dict[str, set[str]]:
        """Concerns nothing examined, per language.

        "types unexamined" is false for a tree containing Python.
        "types unexamined for C++" is true and is what a reader acts on.
        """
        wanted = set(CONCERNS) if "all" in self.concerns else set(self.concerns)
        return {
            name: wanted - covered
            for name, covered in self.coverage_by_language().items()
        }

    def _concerns_of(self, concepts: tuple[str, ...]) -> set[str]:
        """The concerns a set of emitted concepts speaks to."""
        emitted = set(concepts)
        return {
            concern for concern in CONCERNS
            if emitted & set(concepts_for(concern))
        } | (emitted & set(CONCERNS))

    def measured_concepts(self) -> set[str]:
        """Concerns an *external analyzer* examined.

        Derived from which tools *ran*, not from what they emitted. A tool
        that ran and found nothing examined its concern — reporting that
        as unexamined would be the absence-as-value defect this project
        exists to remove, arriving one layer out: "vulture found no dead
        code" is a result, and "nobody looked for dead code" is a gap, and
        collapsing them is exactly the mistake that produced the A+.

        Deliberately analyzer-tier only. The built-in detectors always run,
        so counting them here would make almost nothing a gap and would
        quietly convert "no independent tool examined this" into "covered"
        — the same collapse, re-entering through the door marked fallback.
        `single_source_concerns` carries what the built-ins did reach.

        **Composed across languages, not unioned.** A concern is claimed
        for the repository only where every language present has it. The
        union is what overstated: one Python file among three hundred C++
        ones made `types` a repository-wide claim. Where a concern holds
        for some languages and not others, `coverage_by_language` is the
        statement that is true.
        """
        per_language = self.coverage_by_language()
        # Only over languages the scan scored. Intersecting across *every*
        # language present erased a healthy Python library's coverage
        # because it held one shell script that no tool reads — one
        # unscanned file rewriting the answer for six hundred scanned
        # ones, which is the edge case distorting the norm.
        scored = [
            covered for name, covered in per_language.items()
            if name in self.scored_languages
        ]
        if not scored:
            return self._concerns_from("analyzer")
        return set.intersection(*scored)

    def single_source_concerns(self) -> list[str]:
        """Concerns only the built-in detectors reached.

        Not a gap — something did look — but not corroborated either, and
        a reader weighing a finding is owed that distinction (ADR 006 §3).
        """
        wanted = set(CONCERNS) if "all" in self.concerns else set(self.concerns)
        return sorted((wanted & self._concerns_from("built-in")) - self.measured_concepts())

    def gaps(self) -> list[str]:
        """Concerns the operator asked for that nothing spoke to.

        The honest gap is per concern, not per language: multi-language
        tools reach nearly everything, so "no coverage" is rare and
        misleading, while "nothing examined testing or types" is the fact
        a reader needs.
        """
        wanted = set(CONCERNS) if "all" in self.concerns else set(self.concerns)
        return sorted(wanted - self.measured_concepts() - set(self.single_source_concerns()))


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
    # What languages are actually here. Without this, six Python-only
    # tools ran over a single C file, produced nothing between them, and
    # the coverage section reported documentation, style, types and
    # dead-code as *examined* — a tool with no input examining a concern.
    inventory = discover(root, config)
    analysis.languages = {
        name: CATALOG_LANGUAGE[name] for name in inventory.languages
        if name in CATALOG_LANGUAGE
    }
    included = set((config.get("paths") or {}).get("include_extensions", ()))
    analysis.scored_languages = tuple(
        name for name in analysis.languages
        if any(KNOWN_SOURCE_SUFFIXES.get(suffix) == name for suffix in included)
    )

    for tool in pool:
        if not inventory.applicable(tool.get("languages")):
            present = ", ".join(sorted(inventory.languages)) or "no recognised source"
            analysis.coverage.append(ToolCoverage(
                slug=tool["slug"], outcome="not-applicable",
                detail=(
                    f"reads {', '.join(tool['languages'][:4])}; this tree is "
                    f"{present}, so it had nothing to examine"
                ),
                concepts=tuple(tool["measures"]),
            ))
            continue
        # A hand-written adapter where the output is genuinely bespoke, a
        # declared one where the tool emits a standard format. Composing
        # the two here keeps `_adapters` and `_generic` independent.
        adapter = adapter_for(tool["slug"]) or declared_adapter(tool["slug"])
        if adapter is None:
            # Selected but unwritten: the catalog and the adapter set are
            # allowed to disagree, and saying so beats pretending.
            analysis.coverage.append(ToolCoverage(
                slug=tool["slug"], outcome="no-adapter",
                detail="selected by policy but no adapter is implemented",
                concepts=tuple(tool["measures"]),
            ))
            continue
        recorded = _run_one(root, adapter, probe, timeout, analysis, excludes)
        analysis.coverage.append(replace(
            recorded, languages=tuple(str(n).lower() for n in tool.get("languages") or ())))

    analysis.coverage.extend(built_in_coverage())
    analysis.coverage.sort(key=lambda item: (item.tier != "built-in", item.slug))
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

    needs_config = getattr(adapter, "has_config", None)
    if needs_config is not None and not needs_config(root):
        # eslint cannot run without a flat config and will exit having done
        # nothing. Recording that as "ran, found nothing" would be a clean
        # result nobody earned.
        return ToolCoverage(
            slug=adapter.slug, outcome="no-config", version=recorded,
            concepts=tuple(adapter.concepts),
            detail=(
                f"{adapter.slug} needs a project configuration and none was found; "
                "add one to have its findings reported"
            ),
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


def measurement_document(analysis: Analysis, root: Path) -> dict[str, Any]:
    """Combined readings, their spread, and the distribution behind them.

    Three kinds of data survive here, deliberately. The **score** needs
    counts and populations; the **report** carries the measurements too,
    because a distribution is what a reader — human or model — can
    actually reason with. "Seven functions failed" supports a sentence;
    "seven failed, worst 45, median 6, and two tools disagree by 60%"
    supports a plan.

    Per-unit readings are summarised rather than listed: a thousand
    functions is a dataset, not a document. The full set stays in the
    findings and the retained raw output.
    """
    combined = combine(analysis.measurements, root)
    spreads = agreement(combined)
    single = single_source_concepts(combined)

    per_concept: dict[str, Any] = {}
    for concept in sorted({item.concept for item in combined}):
        readings = [item for item in combined if item.concept == concept]
        values = sorted(item.value for item in readings)
        corroborated = [item for item in readings if item.corroborated]
        per_concept[concept] = {
            "units": len(readings),
            "tools": sorted({tool for item in readings for tool in item.tools}),
            "corroborated_units": len(corroborated),
            # A lone reading carries a counting convention nobody checked.
            "single_source": concept in single,
            # Mean relative disagreement between tools, absent when only
            # one spoke — zero would read as perfect agreement, which is
            # absence-as-value wearing a statistics hat.
            "tool_disagreement": round(spreads[concept], 3) if concept in spreads else None,
            "distribution": _distribution(values),
        }
    return per_concept


def _distribution(values: list[float]) -> dict[str, float]:
    """Enough shape to reason about, without shipping the raw vector."""
    if not values:
        return {}
    return {
        "min": round(values[0], 2),
        "median": round(values[len(values) // 2], 2),
        "p90": round(values[min(int(len(values) * 0.9), len(values) - 1)], 2),
        "max": round(values[-1], 2),
    }


def built_in_coverage() -> list[ToolCoverage]:
    """The built-in detectors, recorded as the source they are.

    They always run and always contribute, so their outcome is fixed.
    Listing them beside the analyzers is what makes the coverage section
    a statement about *everything that examined the code* rather than
    about the external half of it.
    """
    return [
        ToolCoverage(slug=slug, outcome=Outcome.RAN.value, tier="built-in",
                     concepts=concepts, detail=note)
        for slug, concepts, note in BUILT_IN_SOURCES
    ]


def _coverage_entry(item: ToolCoverage) -> dict[str, Any]:
    """One source's row, carrying only the fields it actually has."""
    entry: dict[str, Any] = {
        "tool": item.slug, "tier": item.tier, "concepts": list(item.concepts),
    }
    if item.version:
        entry["version"] = item.version
    if item.contributed:
        entry["measurements"] = item.measurements
        entry["findings"] = item.findings
        entry["seconds"] = item.duration_seconds
    if item.parse_error:
        entry["parse_error"] = item.parse_error
    elif item.detail:
        # Shipped even when the source contributed. Detail used to mean
        # "why this failed"; for a built-in it means "where this stands
        # against the external tools", which a successful run needs to
        # state more than a failed one does.
        entry["detail"] = item.detail
    return entry


def coverage_document(analysis: Analysis) -> dict[str, Any]:
    """The coverage section, as it appears in a report.

    Grouped by outcome because the reader's question is "what did and did
    not run", not "what happened to each of forty tools in catalog order".
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in analysis.coverage:
        key = "parse-error" if item.parse_error else item.outcome
        grouped[key].append(_coverage_entry(item))

    ran = [item for item in analysis.coverage if item.contributed]
    return {
        # Both tiers, because a reader asking what examined this code is
        # owed the whole answer. Built-ins are single-source by
        # definition; analyzers may corroborate each other.
        "sources": {
            "built_in": sum(1 for i in analysis.coverage if i.tier == "built-in"),
            "analyzers": sum(1 for i in ran if i.tier == "analyzer"),
        },
        "selection": {
            "concerns": list(analysis.concerns),
            "depth": analysis.depth,
            "license_policy": analysis.license_policy,
        },
        # Two reports with different coverage are not comparable, so this
        # is stated beside the score rather than filed behind it.
        "tools_attempted": sum(1 for i in analysis.coverage if i.tier == "analyzer"),
        "tools_contributed": sum(1 for i in ran if i.tier == "analyzer"),
        "by_outcome": dict(grouped),
        # The languages this coverage claim is *about*. Without it,
        # `concepts_covered: [types]` reads as "this repository is
        # type-checked" on a tree that is 98% unread C++.
        "scored_languages": sorted(analysis.scored_languages),
        "concepts_covered": sorted(analysis.measured_concepts()),
        # The precise statement. mypy covers types for Python and nothing
        # for C++, at any language mix — no threshold, so a rule fitted
        # to one repository cannot distort another.
        "by_language": {
            name: sorted(covered)
            for name, covered in sorted(analysis.coverage_by_language().items())
        },
        "gaps_by_language": {
            name: sorted(missing)
            for name, missing in sorted(analysis.gaps_by_language().items())
            if missing
        },
        # Examined, but by one source that cannot corroborate itself.
        # Between covered and unexamined, and reported as its own thing so
        # neither number overstates.
        "concepts_single_source": analysis.single_source_concerns(),
        # A concern nobody examined is Unknown, never clean. Naming it is
        # the difference between a gap and a silence.
        "concepts_unexamined": analysis.gaps(),
        "error": analysis.error,
    }
