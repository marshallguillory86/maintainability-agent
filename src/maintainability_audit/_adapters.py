"""Turning analyzer output into measurements and findings — ADR 006, ADR 008.

An adapter knows one tool: how to ask for its version, how to invoke it, and
how to read what comes back. It knows nothing about the rubric, scores or
thresholds, for the same reason scanners may not import scoring — an adapter
that could see the rubric would eventually be tuned to it.

**Two shapes, and the difference decides what a tool may contribute.**

*Metric emitters* report a value for every unit, threshold-free: lizard gives
cyclomatic complexity for every function, radon a maintainability index for
every file. They can supply numerators **and denominators**.

*Verdict emitters* report only units that breached the tool's own configured
threshold. Measured on eslint: the same one-function file at complexity 11
yields 1 finding at threshold 5 and **0 findings at threshold 15**. At the
higher threshold nothing in the output reveals that a function exists at all,
so no denominator can be formed from it — and consuming those verdicts would
make the score a function of the repository's lint config, which falsifies
P2. So a verdict emitter contributes located findings and never a rate.

Adapters **describe** invocations; only ``_runner`` executes them. That keeps
timeout, isolation and version capture in one auditable place.
"""

from __future__ import annotations

import csv
import io
import json
import shutil
import tempfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field, replace
from importlib import metadata
from pathlib import Path
from typing import Protocol

from ._runner import Invocation, ToolResult


@dataclass(frozen=True)
class Measurement:
    """One value, for one unit, from one tool.

    ``unit`` is the thing measured — a function or a file — identified the way
    the report identifies it, so measurements from different tools about the
    same function can be combined.
    """

    concept: str
    unit: str
    value: float
    tool: str
    path: str
    line: int | None = None


@dataclass(frozen=True)
class Finding:
    """A located problem a tool named, with no rate attached."""

    concept: str
    path: str
    line: int | None
    message: str
    tool: str
    rule: str | None = None


# How much raw output to keep inline per tool. Enough for a language model
# to reason over the shape of a result, bounded so a report stays a
# document. The full text is written beside the report when a sidecar
# directory is supplied.
RAW_INLINE_LIMIT = 64_000


@dataclass(frozen=True)
class Extraction:
    """Everything one adapter produced from one run."""

    measurements: tuple[Measurement, ...] = ()
    findings: tuple[Finding, ...] = ()
    # Set when a tool ran successfully but its output could not be read.
    # Distinct from "ran and found nothing", which is a real result; this
    # is a gap, and reporting it as clean is the failure ADR 006 exists
    # to prevent.
    parse_error: str | None = None
    # What the tool actually said, kept whether or not the parser
    # understood it.
    #
    # Two consumers with different constraints. The scoring engine is
    # deliberately conservative: it reads only measurements, refuses
    # threshold-contaminated verdicts as rates, and maps everything onto
    # nine concerns. That is lossy by design. A language model reading the
    # report is bound by none of it, and can see what the engine
    # structurally cannot -- that forty unused-import findings cluster in
    # one module, that every complexity warning sits on one code path,
    # that a whole rule category is missing because nobody enabled it.
    #
    # Retained on parse failure especially. A parse error means *this
    # agent* could not read the output; a model usually can, and
    # discarding it would throw away the one artifact that still had
    # value.
    raw: str = ""
    truncated: bool = False


class Adapter(Protocol):
    """What every tool integration must provide."""

    slug: str
    emits: str  # "metric" | "verdict" | "both"
    concepts: tuple[str, ...]

    def version_argv(self) -> tuple[str, ...]:
        """How to ask this tool what it is. Doubles as the availability probe."""

    def invocation(self, root: Path, paths: Iterable[str] | None) -> Invocation:
        """How to run it over a tree."""

    def parse(self, result: ToolResult) -> Extraction:
        """Read its output. Never raises; unreadable output is a parse_error."""


@dataclass
class BaseAdapter:
    """Shared plumbing so an adapter is mostly its parser.

    Subclasses set the class attributes and implement ``_read``. The
    exception handling lives here so no adapter can forget it: a tool whose
    output shape changed must degrade to a stated gap, never to silence.
    """

    slug: str = ""
    emits: str = "metric"
    concepts: tuple[str, ...] = ()
    executable: str = ""
    version_flag: str = "--version"
    findings_exit_codes: tuple[int, ...] = (0,)
    extra_args: tuple[str, ...] = field(default_factory=tuple)

    def version_argv(self) -> tuple[str, ...]:
        return (self.executable, self.version_flag)

    def installed_version(self) -> str | None:
        """The version from package metadata, when the CLI cannot say."""
        if not self.distribution:
            return None
        try:
            return f"{self.distribution} {metadata.version(self.distribution)}"
        except metadata.PackageNotFoundError:
            return None

    # How this tool spells "skip these". Empty means it has no exclusion
    # flag and must be filtered another way.
    exclude_flag: str = ""
    exclude_separator: str = ","
    # Installed distribution name, for tools whose CLI has no version flag.
    # multimetric is one: `--version` is not an option, so it exits 2 with
    # usage text and a CLI-only probe reports a working tool as broken.
    # P1 now depends on recording which version ran, so a tool that cannot
    # say must be asked another way rather than left blank.
    distribution: str = ""

    def exclusions(self, excludes: Sequence[str]) -> tuple[str, ...]:
        """Translate the audit's exclude patterns into this tool's dialect.

        Without this, every analyzer walks `.venv`, `node_modules` and
        `build` and reports third-party code as the user's. Measured
        before it was added: vulture returned 517 dead-code findings on
        this repository and **all 517 were inside `.venv`**. A report that
        blames a user for a vendored library is worse than no report.
        """
        if not excludes or not self.exclude_flag:
            return ()
        return (self.exclude_flag, self.exclude_separator.join(excludes))

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        targets = tuple(paths) if paths else (str(root),)
        return Invocation(
            argv=(self.executable, *self.extra_args, *self.exclusions(excludes), *targets),
            findings_exit_codes=self.findings_exit_codes,
        )

    def parse(self, result: ToolResult) -> Extraction:
        if not result.usable:
            return Extraction(parse_error=result.detail or f"{self.slug} did not run")
        try:
            return self._with_raw(self._read(result), result)
        except (ValueError, KeyError, IndexError, TypeError, AttributeError,
                json.JSONDecodeError) as error:
            # Output shapes drift between tool releases, and a message-text
            # parser drifts faster. Failing to a stated gap keeps a version
            # bump from quietly turning findings into a clean result.
            return self._with_raw(
                Extraction(
                    parse_error=(
                        f"{self.slug} ran but its output could not be read "
                        f"({type(error).__name__}: {error}). Pin the tool version or "
                        "update the adapter. The raw output is retained: a reader, "
                        "human or model, can still use it."
                    )
                ),
                result,
            )

    @staticmethod
    def _with_raw(extraction: Extraction, result: ToolResult) -> Extraction:
        """Attach what the tool said, bounded but never dropped."""
        text = result.stdout or result.stderr
        return replace(
            extraction,
            raw=text[:RAW_INLINE_LIMIT],
            truncated=len(text) > RAW_INLINE_LIMIT,
        )

    def _read(self, result: ToolResult) -> Extraction:
        raise NotImplementedError


def _rows(text: str) -> list[list[str]]:
    return [row for row in csv.reader(io.StringIO(text)) if row]


SOURCE_SUFFIXES = (".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".rb", ".php")
# A tool asked about thousands of files still has to fit on a command line.
# Beyond this the list is capped -- and the cap is a stated limit rather
# than a silent truncation, because a shortened file list is a shortened
# audit.
MAX_EXPANDED_FILES = 400


def expand_files(
    root: Path, excludes: Sequence[str], suffixes: Sequence[str] = SOURCE_SUFFIXES
) -> tuple[str, ...]:
    """Explicit file paths, honouring exclusions without a tool flag.

    Some analyzers have no `--exclude` at all. Handing them a directory
    means they walk `.venv` and `node_modules` and report vendored code as
    the user's, so the exclusion is applied here by choosing what to name.
    """
    skip = tuple(e.rstrip("/") for e in excludes)
    return tuple(
        str(path)
        for path in sorted(root.rglob("*"))
        if path.suffix in suffixes
        and path.is_file()
        and not any(part in skip for part in path.parts)
    )[:MAX_EXPANDED_FILES]


def _npx(tool: str, *args: str) -> tuple[str, ...]:
    """Invoke a Node tool, using a local install when there is one.

    Prefers a globally installed binary and falls back to ``npx --yes``,
    which fetches the package if absent. That fetch is a network action, so
    P1 separates analysis from acquisition: the analysis never touches the
    network and never transmits the code being audited, while acquiring a
    tool may. The version that ran is recorded either way.

    Install ahead of time (``npm install -g jscpd``) to pin a version or to
    build air-gapped; the local binary is then used directly.
    """
    if shutil.which(tool):
        return (tool, *args)
    return ("npx", "--yes", tool, *args)


class LizardAdapter(BaseAdapter):
    """Cyclomatic complexity, length and parameter count, for every function.

    The workhorse: one binary covering C, C++, C#, Java, Fortran, Go, Rust,
    Kotlin, Swift, PHP, Ruby, Scala, JS and TS with no per-language setup, and
    the same four metrics everywhere. Threshold-free, so it supplies the
    denominators verdict emitters cannot.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="lizard", emits="metric", executable="lizard",
            concepts=("complexity", "structure", "metrics"),
            extra_args=("--csv",), exclude_flag="--exclude",
        )

    def _read(self, result: ToolResult) -> Extraction:
        measurements: list[Measurement] = []
        for row in _rows(result.stdout):
            # nloc,ccn,token,param,length,location,file,name,args,start,end
            if len(row) < 8:
                continue
            path, name = row[6], row[7]
            unit = f"{path}::{name}"
            for concept, index in (("complexity", 1), ("metrics", 0), ("structure", 3)):
                measurements.append(Measurement(
                    concept=concept, unit=unit, value=float(row[index]),
                    tool=self.slug, path=path,
                    line=int(row[9]) if len(row) > 9 and row[9].isdigit() else None,
                ))
        return Extraction(measurements=tuple(measurements))


class RadonAdapter(BaseAdapter):
    """Maintainability Index per file — the academic MI formula.

    A different concept from cyclomatic complexity and worth keeping
    separate: MI folds volume, complexity and comment ratio into one number,
    so it disagrees with raw CCN in informative ways.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="radon", emits="metric", executable="radon",
            concepts=("metrics",), extra_args=("mi", "-j"),
        )

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        targets = tuple(paths) if paths else (str(root),)
        # radon takes comma-separated glob *patterns*, so a bare directory
        # name has to become one or it matches nothing.
        ignore = ("-i", ",".join(f"{e.rstrip('/')}*" for e in excludes)) if excludes else ()
        return Invocation(argv=(self.executable, "mi", "-j", *ignore, *targets))

    def _read(self, result: ToolResult) -> Extraction:
        payload = json.loads(result.stdout or "{}")
        measurements = [
            Measurement(concept="metrics", unit=path, value=float(entry["mi"]),
                        tool=self.slug, path=path)
            for path, entry in payload.items()
            if isinstance(entry, dict) and "mi" in entry
        ]
        return Extraction(measurements=tuple(measurements))


class JscpdAdapter(BaseAdapter):
    """Copy-paste detection across ~150 formats.

    Emits both: a duplication *ratio* over the whole tree, which is a rate,
    and each clone as a located finding.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="jscpd", emits="both", executable="jscpd",
            concepts=("duplication",),
        )
        # jscpd writes its JSON to a file rather than stdout, so the adapter
        # picks the destination when it builds the invocation and reads it
        # back when parsing. A scratch directory rather than the scanned
        # tree: writing into the repository under audit would change what
        # the next tool sees.
        self._report_dir = Path(tempfile.mkdtemp(prefix="jscpd-"))

    def version_argv(self) -> tuple[str, ...]:
        return _npx("jscpd", "--version")

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        ignore = ("--ignore", ",".join(f"**/{e.rstrip('/')}/**" for e in excludes)) if excludes else ()
        return Invocation(
            argv=(*_npx("jscpd"), str(root), "--reporters", "json", "--silent",
                  *ignore, "--output", str(self._report_dir)),
        )

    def _read(self, result: ToolResult) -> Extraction:
        report = self._report_dir / "jscpd-report.json"
        raw = report.read_text(encoding="utf-8") if report.exists() else result.stdout
        payload = json.loads(raw or "{}")
        totals = payload.get("statistics", {}).get("total", {})
        measurements = []
        if "percentage" in totals:
            measurements.append(Measurement(
                concept="duplication", unit="<tree>",
                value=float(totals["percentage"]), tool=self.slug, path="",
            ))
        findings = tuple(
            Finding(concept="duplication",
                    path=clone.get("firstFile", {}).get("name", ""),
                    line=clone.get("firstFile", {}).get("start"),
                    message=f"{clone.get('lines', '?')} duplicated lines",
                    tool=self.slug)
            for clone in payload.get("duplicates", [])
        )
        return Extraction(measurements=tuple(measurements), findings=findings)


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


class InterrogateAdapter(BaseAdapter):
    """Docstring coverage as a percentage — a rate the tool computes itself."""

    def __init__(self) -> None:
        super().__init__(
            slug="interrogate", emits="metric", executable="interrogate",
            concepts=("documentation",), findings_exit_codes=(0, 1),
            exclude_flag="--exclude", exclude_separator=" ",
        )

    def _read(self, result: ToolResult) -> Extraction:
        # "RESULT: FAILED (minimum: 80.0%, actual: 63.3%)". The exit code is
        # the tool's own pass/fail against *its* default threshold and is
        # deliberately ignored -- the rubric owns thresholds, not the tool.
        text = result.stdout + result.stderr
        marker = "actual:"
        if marker not in text:
            raise ValueError("no coverage percentage in interrogate output")
        actual = text.split(marker, 1)[1].split("%", 1)[0].strip()
        return Extraction(measurements=(Measurement(
            concept="documentation", unit="<tree>",
            value=float(actual), tool=self.slug, path="",
        ),))


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


class ComplexipyAdapter(BaseAdapter):
    """Cognitive complexity per function — nesting-weighted reading cost.

    A different measurement from cyclomatic complexity, not a second
    opinion on it: cyclomatic counts branches and is blind to nesting, so
    five guard clauses and five levels of nesting score the same under it.
    Keeping both is the point — where they disagree is informative.

    Writes its JSON to a fixed filename in the working directory, so the
    invocation runs from a scratch directory to avoid dropping a file into
    the tree under audit.
    """

    def __init__(self) -> None:
        super().__init__(
            slug="complexipy", emits="metric", executable="complexipy",
            concepts=("complexity",), findings_exit_codes=(0, 1),
        )
        self._work = Path(tempfile.mkdtemp(prefix="complexipy-"))

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        # complexipy has no exclusion flag, so the filtering is done by
        # naming files rather than handing it a directory. Without this it
        # walks .venv and attributes vendored complexity to the user.
        targets = tuple(paths) if paths else expand_files(root.resolve(), excludes)
        return Invocation(
            argv=(self.executable, *targets, "--output-format", "json", "--quiet"),
            findings_exit_codes=self.findings_exit_codes,
            cwd=self._work,
        )

    def _read(self, result: ToolResult) -> Extraction:
        report = self._work / "complexipy-results.json"
        if not report.exists():
            raise ValueError("complexipy wrote no results file")
        entries = json.loads(report.read_text(encoding="utf-8"))
        measurements = tuple(
            Measurement(
                concept="complexity",
                unit=f"{entry['path']}::{entry['function_name']}",
                value=float(entry["complexity"]),
                tool=self.slug, path=entry["path"],
            )
            for entry in entries
            if isinstance(entry, dict) and "complexity" in entry
        )
        return Extraction(measurements=measurements)


class MultimetricAdapter(BaseAdapter):
    """Halstead, maintainability index and comment ratio, multi-language.

    Twenty-five metrics over C, C++, Java, JavaScript, Go, Ruby, PHP and
    Python. Only the ones this project has a concern for are lifted; the
    rest stay in the retained raw output where a reader can still use them.
    """

    _WANTED = (
        ("maintainability_index", "metrics"),
        ("cyclomatic_complexity", "complexity"),
        ("comment_ratio", "documentation"),
        ("halstead_difficulty", "metrics"),
    )

    # Takes file paths, not a directory: given a directory it returns a
    # single meaningless entry for the directory itself, which parsed as
    # "ran, found nothing".

    def __init__(self) -> None:
        super().__init__(
            slug="multimetric", emits="metric", executable="multimetric",
            concepts=("metrics", "complexity", "documentation"),
            version_flag="--help", distribution="multimetric",
        )

    def invocation(
        self, root: Path, paths: Iterable[str] | None = None,
        excludes: Sequence[str] = (),
    ) -> Invocation:
        targets = tuple(paths) if paths else expand_files(root, excludes)
        return Invocation(argv=(self.executable, *targets))

    def _read(self, result: ToolResult) -> Extraction:
        payload = json.loads(result.stdout or "{}")
        measurements = []
        for path, metrics in (payload.get("files") or {}).items():
            for key, concept in self._WANTED:
                if key in metrics:
                    measurements.append(Measurement(
                        concept=concept, unit=f"{path}::{key}",
                        value=float(metrics[key]), tool=self.slug, path=path,
                    ))
        if not measurements:
            # A metric emitter that produced nothing examined nothing. The
            # earlier version accepted this whenever an `overall` key was
            # present, which turned "given a directory it cannot read" into
            # a clean result -- absence-as-value, one more time.
            raise ValueError(
                "multimetric returned no per-file metrics; it takes file paths "
                "rather than a directory"
            )
        return Extraction(measurements=tuple(measurements))


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
            exclude_flag="--match-dir", exclude_separator="|",
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


ADAPTERS: dict[str, Callable[[], BaseAdapter]] = {
    "complexipy": ComplexipyAdapter,
    "multimetric": MultimetricAdapter,
    "pydocstyle": PydocstyleAdapter,
    "lizard": LizardAdapter,
    "radon": RadonAdapter,
    "jscpd": JscpdAdapter,
    "ruff": RuffAdapter,
    "vulture": VultureAdapter,
    "interrogate": InterrogateAdapter,
}


def adapter_for(slug: str) -> BaseAdapter | None:
    """The adapter for one catalog slug, or None if nobody wrote it yet.

    Returning None rather than raising: the catalog lists far more tools
    than have adapters, and a missing adapter is an ordinary, reportable
    state rather than an error.
    """
    factory = ADAPTERS.get(slug)
    return factory() if factory else None


def adapter_emits(slug: str) -> str | None:
    adapter = adapter_for(slug)
    return adapter.emits if adapter else None


def measurements_only(extraction: Extraction, adapter: BaseAdapter) -> tuple[Measurement, ...]:
    """Measurements a verdict emitter is not allowed to contribute.

    Enforced here rather than trusted: an adapter marked ``verdict`` that
    started returning measurements would silently reintroduce
    threshold-contaminated rates, which is the defect the audit found in
    eslint and the reason the two shapes are distinguished at all.
    """
    if adapter.emits == "verdict":
        return ()
    return extraction.measurements
