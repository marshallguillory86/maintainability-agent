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
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
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

    def invocation(self, root: Path, paths: Iterable[str] | None = None) -> Invocation:
        targets = tuple(paths) if paths else (str(root),)
        return Invocation(
            argv=(self.executable, *self.extra_args, *targets),
            findings_exit_codes=self.findings_exit_codes,
        )

    def parse(self, result: ToolResult) -> Extraction:
        if not result.usable:
            return Extraction(parse_error=result.detail or f"{self.slug} did not run")
        try:
            return self._read(result)
        except (ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            # Output shapes drift between tool releases, and a message-text
            # parser drifts faster. Failing to a stated gap keeps a version
            # bump from quietly turning findings into a clean result.
            return Extraction(
                parse_error=(
                    f"{self.slug} ran but its output could not be read "
                    f"({type(error).__name__}: {error}). Pin the tool version or "
                    "update the adapter."
                )
            )

    def _read(self, result: ToolResult) -> Extraction:
        raise NotImplementedError


def _rows(text: str) -> list[list[str]]:
    return [row for row in csv.reader(io.StringIO(text)) if row]


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
            extra_args=("--csv",),
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

    def invocation(self, root: Path, paths: Iterable[str] | None = None) -> Invocation:
        targets = tuple(paths) if paths else (str(root),)
        return Invocation(argv=(self.executable, "mi", "-j", *targets))

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

    def invocation(self, root: Path, paths: Iterable[str] | None = None) -> Invocation:
        # Invoked as a locally installed binary, never through `npx --yes`.
        # That would download a package mid-audit, which is a network action
        # and breaks P1 (no network). A jscpd that is not installed is
        # reported unavailable, which is the honest answer.
        return Invocation(
            argv=(self.executable, str(root), "--reporters", "json", "--silent",
                  "--output", str(root / ".jscpd-out")),
        )

    def _read(self, result: ToolResult) -> Extraction:
        payload = json.loads(result.stdout or "{}")
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
            extra_args=("--min-confidence", "80"),
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


ADAPTERS: dict[str, Callable[[], BaseAdapter]] = {
    "lizard": LizardAdapter,
    "radon": RadonAdapter,
    "jscpd": JscpdAdapter,
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
