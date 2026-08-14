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

import json
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from importlib import metadata
from pathlib import Path
from typing import Protocol

from ._metrics_types import Finding, Measurement
from ._runner import Invocation, ToolResult

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


def measurements_only(extraction: Extraction, adapter: BaseAdapter) -> tuple[Measurement, ...]:
    """Measurements a verdict emitter is not allowed to contribute.

    Enforced here rather than trusted: an adapter marked ``verdict`` that
    started returning measurements would silently reintroduce
    threshold-contaminated rates, which is the defect the audit found in
    eslint and the reason the two shapes are distinguished at all.

    Lives with the base rather than the registry: it is a rule about what
    an adapter *may* do, not knowledge of which adapters exist.
    """
    if adapter.emits == "verdict":
        return ()
    return extraction.measurements

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
