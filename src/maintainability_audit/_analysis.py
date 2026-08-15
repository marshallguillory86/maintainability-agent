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

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ._adapters import Extraction, exclusions_for, measurements_only, set_tool_acquisition
from ._built_ins import BUILT_IN_SOURCES
from ._catalog import CONCERNS, PolicyError, concepts_for, resolve_pool, settings_from
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
    # `exclude_patterns` is what the operator configured, which is a
    # different question from whose code this is. A vendored tree nobody
    # listed is dropped by the score and was walked by every analyzer,
    # with the findings attributed to the user. `inventory.exclusions()`
    # below closes that.
    # What languages are actually here. Without this, six Python-only
    # tools ran over a single C file, produced nothing between them, and
    # the coverage section reported documentation, style, types and
    # dead-code as *examined* — a tool with no input examining a concern.
    # Before any probe: a fetch during the availability check is the
    # same unconfigured fetch as one during analysis.
    set_tool_acquisition(bool(settings.get("acquire_tools")))
    inventory = discover(root, config)
    excludes = exclusions_for(config, inventory)  # two inputs, see `Exclusions`
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
        recorded = _run_one(root, adapter, probe, timeout, analysis, excludes, inventory)
        analysis.coverage.append(replace(
            recorded, languages=tuple(str(n).lower() for n in tool.get("languages") or ())))

    analysis.coverage.extend(built_in_coverage())
    analysis.coverage.sort(key=lambda item: (item.tier != "built-in", item.slug))
    return analysis


def _run_one(root: Path, adapter: Any, probe: Probe, timeout: int,
             analysis: Analysis, excludes: Sequence[str] = (),
             inventory: Any = None) -> ToolCoverage:
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
        return _attempt(root, adapter, probe, timeout, analysis, excludes, inventory)
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
             analysis: Analysis, excludes: Sequence[str] = (),
             inventory: Any = None) -> ToolCoverage:
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
    # Filtered before the counts are taken, not after. Recording 48
    # measurements and reporting 6 describes an activity rather than a
    # result, which is the defect this project keeps finding.
    extraction = _ours_only_extraction(adapter.parse(result), root, adapter, excludes, inventory)
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


def _ours_only_extraction(
    extraction: Extraction, root: Path, adapter: Any,
    excludes: Sequence[str], inventory: Any,
) -> Extraction:
    """The backstop, applied per tool before its contribution is counted.

    A tool is not obliged to honour the exclusions it was handed —
    `test_adapters` already records that some ignore them. Naming the
    classified trees keeps a well-behaved tool from reading the files;
    this keeps a badly-behaved one from reporting them, and keeps the
    coverage record describing what survived rather than what was seen.
    """
    if inventory is None:
        return extraction
    told = (
        adapter.received_trees(excludes)
        if hasattr(adapter, "received_trees")
        else bool(getattr(excludes, "trees", ()))
    )
    return replace(
        extraction,
        measurements=tuple(ours_only(list(extraction.measurements), root, inventory, told)),
        findings=tuple(ours_only(list(extraction.findings), root, inventory, told)),
    )


def ours_only(
    items: list[Any], root: Path, inventory: Any, told_about_trees: bool = True
) -> list[Any]:
    """Drop measurements or findings about code the team did not write.

    Tools report paths however they like — absolute, relative, or
    relative to their own working directory — so each is reduced to a
    repository-relative posix path before it is looked up. A path that
    cannot be placed inside the tree is kept: an unrecognised location
    is not evidence of foreign code, and silently dropping it would be
    the same absence-as-value mistake in a new place.

    `told_about_trees` decides the fate of a tree-wide rate — jscpd's
    duplication percentage, interrogate's coverage — which carries an
    empty path and survives any path-exact filter. Told, the rate
    describes our code and stands. Untold, it counted somebody else's
    files and nothing after the fact can correct it, so it is dropped
    rather than adjusted: a corrected-looking number nobody computed is
    worse than no number.
    """
    not_ours = inventory.not_ours()
    if not not_ours:
        return list(items)
    return [
        item for item in items
        if _relative_path(item.path, root) not in not_ours
        and (told_about_trees or item.path != "")
    ]


def _relative_path(path: str, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.replace("\\", "/")


def _collect(extraction: Extraction, adapter: Any, analysis: Analysis) -> None:
    # `measurements_only` is the enforcement point, not a formality: a
    # verdict emitter that started returning measurements would silently
    # reintroduce threshold-contaminated rates.
    analysis.measurements.extend(measurements_only(extraction, adapter))
    analysis.findings.extend(extraction.findings)
