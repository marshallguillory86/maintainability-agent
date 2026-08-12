"""Invoking external analyzers — ADR 006.

The only module besides ``git_tools`` permitted to spawn a process. Timeout,
isolation, version capture and failure classification live here so that
adapters describe invocations rather than performing them, and so the
determinism promise has one place to be audited.

**Availability is proven by invocation, never inferred.** Presence on ``PATH``
is not availability: measured on a developer machine, ``/usr/bin/java`` exists
and ``command -v java`` succeeds, but it is the macOS stub with no JDK behind
it and PMD refused to launch through it.

Exit codes are no better alone, in both directions. Many linters exit non-zero
to report findings, so treating that as failure discards real evidence; and a
launcher can exit zero having done nothing, so treating that as success invents
it. Either mistake ends the same way — a tool recorded as having run, found
nothing, and contributed a clean result. That is the same failure
as the hello-world A+, arriving through a new door: absence of output read as
absence of problems. So a tool counts as available only when it has been
executed and its output validated against an expected shape.

Nothing here ever fails the audit. A tool that is missing, broken, slow or
unparseable yields an outcome the report states plainly, because a tool that
did not run is not a clean result.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

# A version probe answers "does this actually work here?" and should cost
# almost nothing. Anything slower than this is a broken installation --
# a JVM stub prompting for a download, a shim waiting on a network call --
# and waiting longer only delays the same answer.
PROBE_TIMEOUT_SECONDS = 20


class Outcome(StrEnum):
    """What happened when a tool was asked to run.

    Every value except ``RAN`` means the tool contributed no evidence, and
    each is distinguished because they call for different responses: a
    missing tool needs installing, a failing one needs reporting upstream,
    a timing-out one needs a longer budget or a smaller scope.
    """

    RAN = "ran"
    NOT_INSTALLED = "not-installed"
    NOT_WORKING = "not-working"
    TIMED_OUT = "timed-out"
    FAILED = "failed"


@dataclass(frozen=True)
class Invocation:
    """How to run one tool. Described by adapters, executed only here."""

    argv: tuple[str, ...]
    # Some analyzers signal findings with a non-zero exit. That is not a
    # failure, and treating it as one would silently discard every finding
    # the tool produced.
    findings_exit_codes: tuple[int, ...] = (0,)
    parse_stderr: bool = False


@dataclass(frozen=True)
class ToolResult:
    """The outcome of one tool, always reportable.

    ``detail`` is written for a human deciding what to do next, so it names
    the tool and the remedy rather than echoing a stack trace.
    """

    slug: str
    outcome: Outcome
    version: str | None = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_seconds: float = 0.0
    detail: str = ""

    @property
    def usable(self) -> bool:
        return self.outcome is Outcome.RAN


@dataclass
class Probe:
    """Cached availability answers.

    A probe costs a process spawn, and a run asks about the same tool once
    per concern it measures. Cached per instance rather than globally so a
    test can install a tool mid-suite and a long-lived process does not
    pin a stale answer forever.
    """

    _answers: dict[str, ToolResult] = field(default_factory=dict)

    def check(self, slug: str, argv: tuple[str, ...]) -> ToolResult:
        """Is `slug` usable here? Runs `argv` and inspects what comes back."""
        if slug in self._answers:
            return self._answers[slug]
        self._answers[slug] = _probe(slug, argv)
        return self._answers[slug]


def _probe(slug: str, argv: tuple[str, ...]) -> ToolResult:
    executable = argv[0]
    if shutil.which(executable) is None:
        return ToolResult(
            slug=slug,
            outcome=Outcome.NOT_INSTALLED,
            detail=f"{executable} is not on PATH",
        )

    result = run(slug, Invocation(argv=argv), timeout_seconds=PROBE_TIMEOUT_SECONDS)
    if result.outcome is not Outcome.RAN:
        return result

    # The exit code cannot be the whole test: a launcher can exit zero
    # having done nothing. A working version probe says something; a stub
    # either says nothing or says it cannot find a runtime.
    banner = (result.stdout or result.stderr).strip()
    if not banner:
        return ToolResult(
            slug=slug,
            outcome=Outcome.NOT_WORKING,
            exit_code=result.exit_code,
            detail=f"{executable} exited {result.exit_code} but produced no version output",
        )
    if _looks_like_a_stub(banner):
        return ToolResult(
            slug=slug,
            outcome=Outcome.NOT_WORKING,
            exit_code=result.exit_code,
            detail=f"{executable} is present but not functional: {banner.splitlines()[0]}",
        )
    return ToolResult(
        slug=slug,
        outcome=Outcome.RAN,
        version=banner.splitlines()[0][:120],
        exit_code=result.exit_code,
        duration_seconds=result.duration_seconds,
    )


# Phrases a launcher prints when the real runtime is absent. Matching text is
# unavoidable here: the stub's whole misbehaviour is reporting success, so
# there is no structured signal left to read.
_STUB_MARKERS = (
    "unable to locate",
    "no java runtime",
    "not found",
    "command not found",
    "is not recognized",
    "please visit",
)


def _looks_like_a_stub(banner: str) -> bool:
    lowered = banner.lower()
    return any(marker in lowered for marker in _STUB_MARKERS)


def run(
    slug: str,
    invocation: Invocation,
    *,
    cwd: Path | None = None,
    timeout_seconds: int = 120,
) -> ToolResult:
    """Execute one tool. Never raises; every failure becomes an outcome."""
    started = time.monotonic()
    try:
        completed = subprocess.run(  # noqa: S603 - argv is built by adapters, never a shell string
            list(invocation.argv),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            slug=slug,
            outcome=Outcome.TIMED_OUT,
            duration_seconds=time.monotonic() - started,
            detail=(
                f"{invocation.argv[0]} exceeded {timeout_seconds}s. Raise "
                "analyzers.timeout_seconds or narrow the scan."
            ),
        )
    except OSError as error:
        # Covers the gap between `which` succeeding and exec failing: a
        # dangling symlink, a file without the execute bit, a broken
        # interpreter line.
        return ToolResult(
            slug=slug,
            outcome=Outcome.NOT_WORKING,
            duration_seconds=time.monotonic() - started,
            detail=f"{invocation.argv[0]} could not be executed: {error}",
        )

    duration = time.monotonic() - started
    if completed.returncode not in invocation.findings_exit_codes:
        return ToolResult(
            slug=slug,
            outcome=Outcome.FAILED,
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            duration_seconds=duration,
            detail=(
                f"{invocation.argv[0]} exited {completed.returncode}: "
                f"{(completed.stderr or completed.stdout).strip().splitlines()[:1] or ['no output']}"
            ),
        )
    return ToolResult(
        slug=slug,
        outcome=Outcome.RAN,
        stdout=completed.stdout,
        stderr=completed.stderr,
        exit_code=completed.returncode,
        duration_seconds=duration,
    )
