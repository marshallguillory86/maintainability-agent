"""Adapters for tools that report only what breached their threshold.

Split out when ``_adapters`` reached 766 lines against this project's own
500-line limit — found by running the audit on itself with its own
configuration, which had never actually happened before.

The division is the one the whole design turns on. A verdict emitter reports only units failing *its own* configured
threshold, so its output encodes that threshold and can never become a
rate — measured on eslint: 1 finding at complexity 5, 0 at 15, on
identical code.
"""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from xml.etree import ElementTree

from ._adapters import BaseAdapter, Extraction, _npx
from ._generic import parse_checkstyle
from ._metric_adapters import expand_files
from ._metrics_types import Finding
from ._runner import Invocation, ToolResult


class VultureAdapter(BaseAdapter):
    """Dead code, as located findings.

    A verdict emitter: it reports what it believes unused and says nothing
    about the population, so it can never supply a denominator.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="vulture", emits="verdict", executable="vulture",
            concepts=("dead-code",), findings_exit_codes=(0, 3),
            extra_args=("--min-confidence", "80"), exclude_flag="--exclude",
            exclude_dialect="vulture",
        )

    def _read(self, result: ToolResult) -> Extraction:
        findings = []
        for line in result.stdout.splitlines():
            # path:line: unused function 'name' (90% confidence)
            parts = line.split(":", 2)
            if len(parts) < 3 or not parts[1].isdigit():
                continue
            findings.append(Finding(
                concept="dead-code", path=parts[0], line=int(parts[1]),
                message=parts[2].strip(), tool=self.slug,
            ))
        return Extraction(findings=tuple(findings))



class RuffAdapter(BaseAdapter):
    """~800 lint rules, as located findings.

    A verdict emitter, so it contributes findings and never a rate — but
    the findings are most of why anyone would run it. The goal is improving
    code, not only scoring it, and "unused import at line 12" is directly
    actionable in a way no aggregate is.

    A project's own rule selection therefore shapes its *findings*, which is
    correct: that is their policy about their code. It cannot shape their
    *score*, which is also correct: two repositories must be comparable
    regardless of how each configured its linter (P2).
    """

    def __init__(self) -> None:
        super().__init__(
            slug="ruff", emits="verdict", executable="ruff",
            concepts=("style", "complexity", "dead-code"),
            findings_exit_codes=(0, 1), exclude_flag="--exclude",
            exclude_dialect="gitignore",
            extra_args=("check", "--output-format", "json", "--no-cache"),
        )

    def _read(self, result: ToolResult) -> Extraction:
        payload = json.loads(result.stdout or "[]")
        if not isinstance(payload, list):
            raise ValueError(f"expected a JSON array of diagnostics, got {type(payload).__name__}")
        findings = tuple(
            Finding(
                concept=_ruff_concept(item.get("code") or ""),
                path=item.get("filename", ""),
                line=(item.get("location") or {}).get("row"),
                message=item.get("message", ""),
                tool=self.slug,
                rule=item.get("code"),
            )
            for item in payload
        )
        return Extraction(findings=findings)


# Ruff rule prefixes mapped onto this project's concern vocabulary, so a
# finding lands under the concern a user asked about. Anything unmapped is
# style, which is the honest default for a linter rule nobody classified.
_RUFF_CONCEPTS = (("C90", "complexity"), ("F401", "dead-code"), ("F841", "dead-code"),
                  ("ERA", "dead-code"), ("D", "documentation"))


def _ruff_concept(code: str) -> str:
    for prefix, concern in _RUFF_CONCEPTS:
        if code.startswith(prefix):
            return concern
    return "style"



class PydocstyleAdapter(BaseAdapter):
    """Docstring convention violations, as located findings.

    Complements interrogate rather than repeating it: interrogate measures
    how *much* is documented, this reports where the documentation
    breaches convention. Coverage and conformance are different questions.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="pydocstyle", emits="verdict", executable="pydocstyle",
            concepts=("documentation", "style"), findings_exit_codes=(0, 1),
            exclude_flag="--match-dir", exclude_separator="|", exclude_dialect="files",
        )

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        """Explicit targets, because `--match-dir` cannot say "skip this".

        It is an *include* filter over directory names: handing it `lib`
        would tell pydocstyle to look only at directories called lib,
        which is the opposite of the intent and would also match
        `src/lib`. So the classified trees are honoured by choosing what
        to name instead, the same way the no-flag adapters do.

        `--match-dir` is dropped entirely rather than kept for the
        operator's patterns: the target list already honours those, and
        an include regex sitting beside an explicit file list can only
        narrow it further in ways nobody asked for.
        """
        targets = tuple(paths) if paths else expand_files(root, excludes, suffixes=(".py",))
        return Invocation(
            argv=(self.executable, *self.extra_args, *targets),
            findings_exit_codes=self.findings_exit_codes,
        )

    def _read(self, result: ToolResult) -> Extraction:
        # Two lines per finding: "path:line in scope `name`:" then an
        # indented "Dxxx: message". Parsed as a pair rather than by regex
        # over the whole text, so a message containing a colon cannot
        # shift the location.
        findings = []
        lines = (result.stdout or result.stderr).splitlines()
        for index, line in enumerate(lines):
            if ":" not in line or line.startswith(" ") or index + 1 >= len(lines):
                continue
            head, _, _ = line.partition(" in ")
            path, _, number = head.rpartition(":")
            if not number.strip().isdigit():
                continue
            detail = lines[index + 1].strip()
            code, _, message = detail.partition(":")
            findings.append(Finding(
                concept="documentation", path=path, line=int(number),
                message=message.strip() or detail, tool=self.slug, rule=code.strip(),
            ))
        return Extraction(findings=tuple(findings))



class EslintAdapter(BaseAdapter):
    """JavaScript and TypeScript lint findings.

    A verdict emitter, and one that cannot run at all without a project
    configuration: eslint flat config is mandatory from v9, and invoked
    in a tree without one it exits having done nothing. That is reported
    as unavailable-no-config rather than as a clean result, which is the
    honest answer and the one that tells the user what to do.

    Running under the project's own config is deliberate. Their rule
    selection shapes their findings — that is their policy about their
    code — and cannot shape their score, because a verdict emitter
    contributes no rate.
    """

    _CONFIGS = (
        "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
        "eslint.config.ts", ".eslintrc.json", ".eslintrc.js", ".eslintrc.yml",
    )
    _CONCEPTS = (("complexity", "complexity"), ("max-depth", "complexity"),
                 ("max-params", "structure"), ("max-lines", "structure"),
                 ("no-unused-vars", "dead-code"))

    def __init__(self) -> None:
        super().__init__(
            slug="eslint", emits="verdict", executable="eslint",
            concepts=("style", "complexity", "structure", "dead-code"),
            findings_exit_codes=(0, 1), exclude_flag="--ignore-pattern",
        )

    def version_argv(self) -> tuple[str, ...]:
        return _npx("eslint", "--version")

    def has_config(self, root: Path) -> bool:
        return any((root / name).exists() for name in self._CONFIGS)

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        ignore: tuple[str, ...] = ()
        for pattern in excludes:
            ignore += ("--ignore-pattern", f"{pattern.rstrip('/')}/**")
        # eslint's ignore patterns are gitignore syntax, where a bare
        # `lib` matches any directory of that name at any depth — the
        # name-list behaviour again. A leading slash roots it.
        for tree in getattr(excludes, "trees", ()):
            ignore += ("--ignore-pattern", f"/{tree}", "--ignore-pattern", f"/{tree}/**")
        targets = tuple(paths) if paths else (str(root),)
        return Invocation(
            argv=(*_npx("eslint"), *targets, "--format", "json", *ignore),
            findings_exit_codes=self.findings_exit_codes,
        )

    def _read(self, result: ToolResult) -> Extraction:
        payload = json.loads(result.stdout or "[]")
        if not isinstance(payload, list):
            raise ValueError(f"expected a JSON array of results, got {type(payload).__name__}")
        findings = tuple(
            Finding(
                concept=self._concept(message.get("ruleId") or ""),
                path=entry.get("filePath", ""),
                line=message.get("line"),
                message=message.get("message", ""),
                tool=self.slug,
                rule=message.get("ruleId"),
            )
            for entry in payload
            for message in entry.get("messages", [])
        )
        return Extraction(findings=findings)

    def _concept(self, rule: str) -> str:
        for prefix, concept in self._CONCEPTS:
            if rule.startswith(prefix):
                return concept
        return "style"


class Flake8Adapter(BaseAdapter):
    """flake8's default line format, kept as located findings.

    Not a DeclaredAdapter, deliberately: flake8's stock output is
    `path:row:col: CODE message`, which is none of the four standard
    formats, and JSON output requires a plugin this project will not ask
    users to install. One small parser beats a prerequisite.

    A verdict emitter like ruff, and for the same reason: its output is
    shaped by the project's own selected rules, so it contributes
    findings and can never supply a rate (P2).
    """

    _LINE = re.compile(r"^(?P<path>.+?):(?P<row>\d+):\d+:\s+(?P<code>\S+)\s+(?P<text>.*)$")
    # flake8's rule families, on ruff's precedent: C9xx is mccabe
    # complexity, F401/F841 are unused code. Everything unmapped is
    # style, the honest default for a lint rule nobody classified.
    _CONCEPTS = (("C9", "complexity"), ("F401", "dead-code"), ("F841", "dead-code"))

    def __init__(self) -> None:
        super().__init__(
            slug="flake8", emits="verdict", executable="flake8",
            concepts=("style", "complexity", "dead-code"),
            findings_exit_codes=(0, 1), exclude_flag="--exclude",
            # flake8 matches each --exclude entry by fnmatch against the
            # normalised path, the same engine lizard uses.
            exclude_dialect="fnmatch",
        )

    def _read(self, result: ToolResult) -> Extraction:
        findings = []
        for line in result.stdout.splitlines():
            match = self._LINE.match(line)
            if not match:
                continue
            code = match.group("code")
            concept = next(
                (concern for prefix, concern in self._CONCEPTS if code.startswith(prefix)),
                "style",
            )
            findings.append(Finding(
                concept=concept, path=match.group("path"), line=int(match.group("row")),
                message=match.group("text"), tool=self.slug, rule=code,
            ))
        return Extraction(findings=tuple(findings))


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

    Decision 9's second JVM adapter, written under the 549fcad audit's
    do-not-copy list. The bundled ``/google_checks.xml`` loads from the
    tool's own classpath — deterministic for a pinned Checkstyle
    version, no repository config, no network. Findings are read
    through the shared JVM interchange parser in ``_generic`` and then
    routed onto this project's concerns per rule: metrics rules are
    complexity, size rules are structure, and everything else is the
    convention layer (style) this integration exists to add beside
    PMD's two complexity rules. A verdict emitter: it reports breaches
    of its ruleset and can never supply a rate (P2). Explicit ``.java``
    targets from ``expand_files`` carry the exclusions, and
    ``has_targets`` keeps an empty list from ever spawning the CLI.
    """

    # Rule-source markers onto concerns. Checkstyle rule sources are
    # dotted class paths (…checks.metrics.CyclomaticComplexityCheck,
    # …checks.sizes.MethodLengthCheck); the package name is the
    # taxonomy the tool itself uses.
    _CONCERN_MARKERS = (
        (".metrics.", "complexity"),
        ("Complexity", "complexity"),
        (".sizes.", "structure"),
        ("Length", "structure"),
        (".coupling.", "structure"),
    )

    def __init__(self) -> None:
        super().__init__(
            slug="checkstyle", emits="verdict", executable="checkstyle",
            concepts=("style", "complexity", "structure"),
            # google_checks emits warnings (exit 0); a stricter ruleset
            # exits non-zero on error-severity findings, which is a
            # result, not a failure.
            findings_exit_codes=(0, 1, 2),
            languages=("java",),
        )

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

    def _concern(self, rule: str) -> str:
        for marker, concern in self._CONCERN_MARKERS:
            if marker in rule:
                return concern
        return "style"
