"""The JVM analyzer track: PMD, Checkstyle, and SpotBugs (decision 9).

Split verbatim out of ``_verdict_adapters`` when the three JVM adapters
pushed that file past this project's own 500-line limit — found, as
before, by running the audit on itself. Two shapes live here:
source-read (PMD pins two design rules, Checkstyle runs the bundled
Google style guide) and artifact-read (SpotBugs analyzes bytecode that
already exists and never triggers a build, ADR 012). All three are
verdict emitters: they report breaches of their own rulesets and can
never supply a rate (P2).
"""

from __future__ import annotations

import dataclasses
import json
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from ._adapters import BaseAdapter, Extraction
from ._generic import parse_checkstyle
from ._metric_adapters import expand_files
from ._metrics_types import Finding
from ._runner import Invocation, ToolResult


class PmdAdapter(BaseAdapter):
    """PMD over Java source, pinned to two rules, read from SARIF.

    Decision 9's first JVM adapter. The invocation names exactly two
    rule references — cognitive and cyclomatic complexity from PMD's
    design category — so every finding maps onto a concept this project
    already scores and two runs over the same tree emit the same output
    (no cache, no network, no repository config required). A verdict
    emitter: PMD reports breaches of its own thresholds and can never
    supply a rate (P2). PMD's CLI has no exclude flag this project
    trusts, so exclusion is applied by never naming the file: explicit
    `.java` targets from ``expand_files``, the same rule as cohesion,
    complexipy and multimetric.
    """

    _RULESET = (
        "category/java/design.xml/CognitiveComplexity,"
        "category/java/design.xml/CyclomaticComplexity"
    )
    _CONCEPTS = {
        "CognitiveComplexity": "cognitive_complexity",
        "CyclomaticComplexity": "cyclomatic_complexity",
    }

    def __init__(self) -> None:
        super().__init__(
            slug="pmd", emits="verdict", executable="pmd",
            # "complexity" is the concern the two concepts serve, and
            # the honest landing place for a rule the map does not name
            # (audit L on 549fcad: never default onto a concept the
            # adapter does not declare).
            concepts=("complexity", "cognitive_complexity",
                      "cyclomatic_complexity"),
            # PMD exits 4 when rule violations were found; that is a
            # result, not a failure.
            findings_exit_codes=(0, 4),
            # This integration names only .java files, whatever the
            # catalog says PMD upstream can read.
            languages=("java",),
        )

    def has_targets(self, root: Path, excludes: Sequence[str] = ()) -> bool:
        """Whether any .java file survives the exclusions.

        Spawning ``pmd check`` with no ``--dir`` exits 2 — an error,
        not a clean zero (audit M on 549fcad). Nothing to examine must
        stay a coverage fact, never a spawned failure.
        """
        return bool(expand_files(root, excludes, suffixes=(".java",)))

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        targets = (
            tuple(paths) if paths
            else expand_files(root, excludes, suffixes=(".java",))
        )
        dirs: tuple[str, ...] = ()
        for target in targets:
            dirs += ("--dir", target)
        return Invocation(
            argv=(
                "pmd", "check", *dirs,
                "--rulesets", self._RULESET,
                "--format", "sarif",
                "--no-cache", "--no-progress",
            ),
            findings_exit_codes=self.findings_exit_codes,
        )

    def _read(self, result: ToolResult) -> Extraction:
        payload = json.loads(result.stdout or "{}")
        if not isinstance(payload, dict) or "runs" not in payload:
            raise ValueError("expected a SARIF object with runs")
        findings = tuple(
            Finding(
                concept=self._CONCEPTS.get(rule, "complexity"),
                path=self._path_of(entry),
                line=self._line_of(entry),
                message=(entry.get("message") or {}).get("text", ""),
                tool=self.slug,
                rule=rule,
            )
            for run in payload["runs"]
            for entry in run.get("results", [])
            for rule in [entry.get("ruleId") or ""]
        )
        return Extraction(findings=findings)

    @staticmethod
    def _path_of(entry: dict) -> str:
        locations = entry.get("locations") or [{}]
        uri = (((locations[0].get("physicalLocation") or {})
                .get("artifactLocation") or {}).get("uri") or "")
        return uri.removeprefix("file://")

    @staticmethod
    def _line_of(entry: dict) -> int | None:
        locations = entry.get("locations") or [{}]
        region = (locations[0].get("physicalLocation") or {}).get("region") or {}
        line = region.get("startLine")
        return int(line) if isinstance(line, int) else None


class CheckstyleAdapter(BaseAdapter):
    """Checkstyle over Java source with its bundled Google ruleset.

    Decision 9's second JVM adapter, remeasured by the 742a49f audit:
    google_checks is a convention and Javadoc guide, so this
    integration claims exactly that — style and documentation — and
    leaves the complexity and structure pools to the tools that emit
    those concerns (H1: measures must name what the pinned invocation
    can actually produce). The bundled ``/google_checks.xml`` loads
    from the tool's own classpath; the working directory is a neutral
    scratch dir so the ruleset's optional ``checkstyle-suppressions.xml``
    lookup can never read the audited tree (M2 — project suppressions
    must not silently move findings, the eslint P2 rule). Findings are
    read through the shared JVM interchange parser in ``_generic``;
    Javadoc rules land on documentation and everything else is style.
    A verdict emitter: it reports breaches of its ruleset and can
    never supply a rate (P2). Explicit ``.java`` targets from
    ``expand_files`` carry the exclusions, and ``has_targets`` keeps
    an empty list from ever spawning the CLI.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="checkstyle", emits="verdict", executable="checkstyle",
            concepts=("style", "documentation"),
            # Checkstyle's real exit contract: the exit code is the
            # number of error-severity violations; -1 (invalid args)
            # and -2 (CheckstyleException) wrap to 255 and 254. Any
            # non-negative count is a run with findings; only the two
            # wrapped negatives are failures (audit M1 — (0, 1, 2) was
            # a different tool's folklore).
            findings_exit_codes=tuple(range(254)),
            languages=("java",),
        )
        self._work = Path(tempfile.mkdtemp(prefix="checkstyle-"))

    def has_targets(self, root: Path, excludes: Sequence[str] = ()) -> bool:
        """Whether any .java file survives the exclusions (never spawn empty)."""
        return bool(expand_files(root, excludes, suffixes=(".java",)))

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        targets = (
            tuple(paths) if paths
            else expand_files(root, excludes, suffixes=(".java",))
        )
        return Invocation(
            argv=("checkstyle", "-c", "/google_checks.xml",
                  "-f", "xml", *targets),
            findings_exit_codes=self.findings_exit_codes,
            # Neutral scratch dir: google_checks' SuppressionFilter
            # resolves its optional checkstyle-suppressions.xml against
            # the working directory, and the audited tree must not be
            # able to suppress its own findings (audit M2).
            cwd=self._work,
        )

    def _read(self, result: ToolResult) -> Extraction:
        try:
            base = parse_checkstyle(result.stdout, self.slug, "style")
        except ElementTree.ParseError as error:
            # Unreadable output is a stated gap, never a crash: the
            # shared plumbing converts ValueError to parse_error.
            raise ValueError(f"unreadable checkstyle XML: {error}") from error
        findings = tuple(
            dataclasses.replace(finding, concept=self._concern(finding.rule or ""))
            for finding in base.findings
        )
        return Extraction(findings=findings)

    @staticmethod
    def _concern(rule: str) -> str:
        # Javadoc rules are the documentation layer; every other
        # google_checks rule — naming, imports, whitespace, LineLength's
        # 100-column convention — is style. The 742a49f audit killed the
        # old substring markers: ".coupling." matched nothing, "Length"
        # filed a column convention under structure, and none of it was
        # tested against real rule sources (H2).
        return "documentation" if "Javadoc" in rule else "style"


class SpotBugsAdapter(BaseAdapter):
    """SpotBugs over bytecode that already exists — never a build (ADR 012).

    Decision 9's third JVM adapter, artifact-read where PMD and
    Checkstyle are source-read. Targets are compiled class directories
    — Maven's ``target/classes``, Gradle's ``build/classes`` (the
    ``java/main`` tree sits under it), plus ``analyzers.class_dirs`` —
    and never ``.java`` files. A Java tree without bytecode is a
    coverage fact carrying a build-then-rerun remedy, not a missing
    binary and never a spawned CLI error. Output is BugCollection XML;
    every category lands on the one concern this integration claims
    (style — SpotBugs is a bug-pattern tool, and its bug categories
    are not this project's complexity or structure evidence). Runs
    record staleness evidence: bytecode older than the newest source
    is said, because two runs with different staleness are not
    silently comparable (P8).
    """

    _DEFAULT_CLASS_DIRS = ("target/classes", "build/classes")
    # The remedy the environment work order carries when a Java tree
    # has no bytecode: the user builds, the agent never does.
    missing_targets_detail = (
        "no compiled classes found; a build (mvn compile or gradle "
        "classes) would widen coverage"
    )
    missing_targets_remedy = (
        "build the project first (e.g. mvn compile or gradle classes)",
        "re-run the audit once the class directories exist",
    )

    def __init__(self) -> None:
        super().__init__(
            slug="spotbugs", emits="verdict", executable="spotbugs",
            concepts=("style",),
            # -exitcode bit flags: 1 = bugs found, 2 = missing classes;
            # both (and their union) are results. Bit 4 is an analysis
            # error and stays a failure.
            findings_exit_codes=(0, 1, 2, 3),
            languages=("java",),
        )
        # Extra class directories from analyzers.class_dirs, threaded
        # in by the analysis loop; explicit call arguments still win.
        self.class_dirs: tuple[str, ...] = ()

    def version_argv(self) -> tuple[str, ...]:
        return ("spotbugs", "-version")

    def _target_dirs(
        self, root: Path, class_dirs: Sequence[str] | None = None,
    ) -> tuple[Path, ...]:
        extras = tuple(class_dirs) if class_dirs is not None else tuple(self.class_dirs)
        found = []
        for relative in (*self._DEFAULT_CLASS_DIRS, *extras):
            candidate = root / relative
            if candidate.is_dir() and any(candidate.rglob("*.class")):
                found.append(candidate)
        return tuple(found)

    def has_targets(
        self, root: Path, excludes: Sequence[str] = (),
        class_dirs: Sequence[str] | None = None,
    ) -> bool:
        """Whether compiled classes already exist. Sources are not targets."""
        del excludes  # class dirs are named outright, never swept from sources
        return bool(self._target_dirs(root, class_dirs))

    def staleness(
        self, root: Path, class_dirs: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """ADR 012's evidence: newest source mtime vs newest class mtime."""
        source_mtime = max(
            (path.stat().st_mtime for path in root.rglob("*.java")), default=0.0,
        )
        class_mtime = max(
            (
                path.stat().st_mtime
                for directory in self._target_dirs(root, class_dirs)
                for path in directory.rglob("*.class")
            ),
            default=0.0,
        )
        return {
            "stale": source_mtime > class_mtime,
            "source_mtime": source_mtime,
            "class_mtime": class_mtime,
        }

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
        class_dirs: Sequence[str] | None = None,
    ) -> Invocation:
        del paths, excludes  # bytecode dirs, never source sweeps
        dirs = self._target_dirs(root, class_dirs)
        return Invocation(
            argv=("spotbugs", "-textui", "-exitcode", "-xml:withMessages",
                  *(str(directory) for directory in dirs)),
            findings_exit_codes=self.findings_exit_codes,
        )

    def _read(self, result: ToolResult) -> Extraction:
        # BugCollection XML: one BugInstance per finding, located by its
        # SourceLine's sourcepath — the report names the source a human
        # can edit, never the .class artifact.
        try:
            root = ElementTree.fromstring(result.stdout or "<BugCollection/>")
        except ElementTree.ParseError as error:
            raise ValueError(f"unreadable BugCollection XML: {error}") from error
        findings = []
        for instance in root.iter("BugInstance"):
            line_node = instance.find("SourceLine")
            source_path = (line_node.get("sourcepath") or "") if line_node is not None else ""
            start = line_node.get("start") if line_node is not None else None
            category = instance.get("category") or ""
            findings.append(Finding(
                # Every SpotBugs category — STYLE included — lands on the
                # one declared concern; claiming more would repeat the
                # Checkstyle H1 overclaim.
                concept="style",
                path=source_path,
                line=int(start) if start and start.isdigit() else None,
                message=instance.get("type") or category,
                tool=self.slug,
                rule=instance.get("type"),
            ))
        return Extraction(findings=tuple(findings))
