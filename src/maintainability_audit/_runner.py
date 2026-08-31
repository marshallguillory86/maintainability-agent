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

import functools
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
    # Where to run. Tools that write output to a fixed filename in the
    # working directory need somewhere that is not the tree under audit,
    # or the audit changes what later tools see.
    cwd: Path | None = None
    # Extra environment for the child, merged over the stripped default.
    # Analyzers leave this None and inherit the code-loading-stripped env;
    # the only caller that sets it is the opted-in test suite, whose
    # operator-configured `NAME=VALUE prog` prefix names env the operator
    # explicitly chose for their own command (Decision 9's opt-in). It is
    # not the audited tree choosing what the child loads.
    env: dict[str, str] | None = None


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


def locate(executable: str) -> str | None:
    """Find a tool, looking in the agent's own environment first.

    Python analyzers install alongside the agent, so a package in a
    virtualenv has lizard and radon in the same ``bin`` directory as the
    interpreter running this code — and that directory is usually *not*
    on the caller's ``PATH``. Searching it first is what makes the tools
    that ship with the package actually reachable; without it a normal
    `maintainability-audit --analyzers` finds almost nothing and reports
    an honest but useless "not installed" for every one of them.
    """
    own_bin = Path(sys.executable).parent
    candidate = own_bin / executable
    if candidate.is_file():
        return str(candidate)
    return shutil.which(executable)


# Variables that make an interpreter or a linter load code from
# somewhere the operator did not choose. `PYTHONPATH` and `NODE_PATH`
# put a directory on an import path; `PYTHONSTARTUP` names a file
# executed before anything else; the `LD_`/`DYLD_` pair inject shared
# objects into the child; the `JAVA*`/`CLASSPATH` group is the same rule
# for the JVM analyzers (PMD, Checkstyle, SpotBugs) — every JVM launch
# reads the option vars at startup, and `-javaagent:` in one of them
# loads an agent jar, which is code execution just as surely as a
# `PYTHONPATH` import. An audited tree that sets any of them in the
# environment this process inherited would be choosing what its own
# analyzer runs (D39, Decision 9).
_CODE_LOADING_VARS = (
    "PYTHONPATH",
    "PYTHONSTARTUP",
    "PYTHONHOME",
    "PYTHONEXECUTABLE",
    "NODE_PATH",
    "NODE_OPTIONS",
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "JAVA_TOOL_OPTIONS",
    "_JAVA_OPTIONS",
    "JDK_JAVA_OPTIONS",
    "CLASSPATH",
)


def analyzer_env() -> dict[str, str]:
    """The environment an analyzer child gets.

    Not a sandbox, and not claimed as one: the child is a normal local
    process and this package does not contain it. What this removes is
    the narrower thing Decision 9 rules out — a path that makes the
    analyzer *load code* the operator did not choose. `PATH` stays,
    because the tool has to be found.
    """
    env = {k: v for k, v in os.environ.items() if k not in _CODE_LOADING_VARS}
    registry = _user_npm_registry()
    if registry is not None:
        # A user who enables `acquire_tools` chooses to fetch a tool; the
        # audited tree does not get to choose *where from*. npm reads a
        # `.npmrc` from the working directory, so a repo shipping
        # `registry=https://evil/` silently redirects that fetch. Forcing
        # the registry through the environment -- which npm ranks above a
        # project `.npmrc` -- pins it to the value the user configured for
        # themselves, read below where the tree cannot vote. Marshall's
        # call, 2026-08-29: let the user pull tools, do not let the tree
        # pick the source.
        env["npm_config_registry"] = registry
    return env


@functools.lru_cache(maxsize=1)
def _user_npm_registry() -> str | None:
    """The user's own npm registry, resolved where the tree cannot vote.

    Read with `npm config get` from a fresh empty directory, so a
    `.npmrc` in the repository under audit -- or in whatever directory
    the audit happens to run from -- has no say in the answer. Returns
    ``None`` when npm is absent (a Python-only audit never fetches a Node
    tool) or cannot say, and the environment is then left untouched.
    """
    npm = shutil.which("npm")
    if npm is None:
        return None
    neutral = tempfile.mkdtemp(prefix="ma-npm-")
    try:
        completed = subprocess.run(  # noqa: S603 - argv list, never a shell
            [npm, "config", "get", "registry"],
            cwd=neutral, capture_output=True, text=True, timeout=30,
            env={k: v for k, v in os.environ.items() if k not in _CODE_LOADING_VARS},
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        os.rmdir(neutral)
    value = completed.stdout.strip()
    return value or None if completed.returncode == 0 else None


def _probe(slug: str, argv: tuple[str, ...]) -> ToolResult:
    executable = argv[0]
    resolved = locate(executable)
    if resolved is None:
        return ToolResult(
            slug=slug,
            outcome=Outcome.NOT_INSTALLED,
            detail=f"{executable} is not installed or not on PATH",
        )

    result = run(slug, Invocation(argv=(resolved, *argv[1:])),
                 timeout_seconds=PROBE_TIMEOUT_SECONDS)
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
        version=version_line(banner),
        exit_code=result.exit_code,
        duration_seconds=result.duration_seconds,
    )


#: A terminal colour/style escape. complexipy paints its version
#: (`\x1b[1;36m7.0\x1b[0m...`), and a painted version stored as the pin is
#: a pin that changes with a tool's colour choices, not its version. The
#: determinism suite stripped these before comparing, which hid that the
#: stored value carried them; stripping at capture makes the recorded pin
#: the version and nothing else (Grok e88b429 audit).
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def version_line(banner: str) -> str:
    """The line of a version banner that actually names a version.

    P1 pins analyzer versions, and some tools (PMD) print ASCII art
    before theirs — recording the art as the version made the pin a
    decoration. The first line containing a dotted number wins; a
    banner with none falls back to its first line, which is all the
    tool offered.
    """
    lines = _ANSI_ESCAPE.sub("", banner).splitlines()
    named = next(
        (line.strip() for line in lines if re.search(r"\d\.\d", line)),
        lines[0] if lines else "",
    )
    return named[:120]


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


def _is_findings_exit_with_empty_body(completed: subprocess.CompletedProcess) -> bool:
    """A non-zero "found something" exit that produced nothing at all.

    Ruff and flake8 exit 1 to report findings, Checkstyle a non-zero
    count; any of them exiting non-zero with an empty body did nothing
    usable, and RAN would price that as a clean run (e88b429 #13). Exit 0
    with an empty body is a real "looked, found nothing" and is not this.
    """
    return (completed.returncode != 0
            and not completed.stdout.strip()
            and not completed.stderr.strip())


def run(
    slug: str,
    invocation: Invocation,
    *,
    cwd: Path | None = None,
    timeout_seconds: int = 120,
) -> ToolResult:
    """Execute one tool. Never raises; every failure becomes an outcome."""
    started = time.monotonic()
    argv = list(invocation.argv)
    resolved = locate(argv[0])
    if resolved:
        argv[0] = resolved
    try:
        completed = subprocess.run(  # noqa: S603 - argv is built by adapters, never a shell string
            argv,
            cwd=str(cwd or invocation.cwd) if (cwd or invocation.cwd) else None,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env={**analyzer_env(), **(invocation.env or {})},
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
    if _is_findings_exit_with_empty_body(completed):
        return ToolResult(
            slug=slug,
            outcome=Outcome.NOT_WORKING,
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            duration_seconds=duration,
            detail=(
                f"{invocation.argv[0]} exited {completed.returncode} with no output; "
                "a findings exit that produced nothing is not a clean run"
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
