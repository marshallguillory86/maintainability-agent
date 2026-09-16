"""This tool runs secure-code-agent for the security pillar (D177).

[ADR 007](adr-007-pillars-and-practice.md) delegates the security pillar to
`secure-code-agent`. Until 3.7.0 the delegation was a handoff: the other
tool wrote `security-pillar.json` and this one read it if it happened to be
there. Nothing ran it, so every audit that did not follow a manual or CI run
of the other tool reported the pillar as unmeasured — including every audit
through the chat door, which cannot run it at all. Decided 2026-09-13: the
pillar is complete, so the audit runs it.

**What the child writes.** Every report `secure-code-agent` can produce is
redirected into a temporary directory this process owns: the Markdown and
JSON reports, SARIF, the PR comment, the remediation prompt and the pillar
document itself. The pillar document and the remediation prompt — that
tool's work order — are read back before the directory goes (D179). The one write that cannot be redirected is its append-only
trend, `.secure-code/history.jsonl` in the audited tree, which it writes on
every run from its own configuration. Turning that off would mean handing
it a configuration from outside the tree, and `secure-code-agent` trusts an
outside configuration to name executables in the tree — so the override
would launder repository content past the other tool's own boundary. The
history is therefore declared, not suppressed.

**How the child is started.** Through `_runner.run`, like every analyzer and
the opted-in test command, so architecture rule 7 still holds: the tree can
reach one execution path, not a new one per feature. The command is the
interpreter doing the auditing, the way D144 and D166 bound theirs, so the
pillar is measured by the `secure-code-agent` installed beside this package
rather than whichever one `PATH` finds. It gets the runner's stripped
environment and a neutral working directory: not a sandbox, and not claimed
as one.

A run that produces no trustworthy document says why. Absence is never
silent, because silence is exactly what ADR 007 says must not read as safety.
"""
from __future__ import annotations

import importlib.util
import shlex
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._delegated_pillar import read_produced
from ._runner import Invocation, Outcome, run

#: The releases this audit runs, and the install command's requirement.
#:
#: **Not a package dependency.** 3.7.0 made it one, and within the day it
#: capped the tool below its current release — installing this package
#: downgraded a machine's secure-code-agent — and put the two tools' opposed
#: `mcp` pins into one environment. secure-code-agent's D3 and this project's
#: ADR 008 both hold the tools independently releasable. So the audit runs
#: whichever release is installed, when it falls in this range, and says so
#: when it does not. The ceiling is the next major: within 0.x the pillar
#: document is versioned by its own `schema_version`, which the reader checks.
#:
#: **The floor is 0.12.2, not the first release with this contract (D182).**
#: 0.12.1 writes the same schema v2 document, and matches `.scignore.yaml`
#: `paths:` globs against absolute finding paths. This audit always hands it an
#: absolute root, so under 0.12.1 every reviewed `paths:` suppression is ignored
#: and its finding counts as live in the pillar every skin shows (D179).
SUPPORTED_FLOOR = (0, 12, 2)
SUPPORTED_CEILING = (1,)
REQUIREMENT = "secure-code-agent>=0.12.2,<1"

#: How long the child may run before the pillar is reported as unmeasured.
DEFAULT_TIMEOUT_SECONDS = 300

_ENTRY = "import sys; from secure_code_audit.cli import main; sys.exit(main())"


@dataclass(frozen=True)
class DelegateRun:
    """What one run of the delegate produced, and why when it produced nothing."""

    document: dict[str, Any] | None
    reason: str | None = None
    environment: list[dict[str, str]] = field(default_factory=list)
    #: The delegate's own remediation prompt — its work order — read before
    #: the directory it was written into is deleted (D179).
    work_order: str | None = None


def _install_remedy(reason: str) -> dict[str, str]:
    """An environment work-order entry, bound to the auditing interpreter (D144)."""
    python = shlex.quote(sys.executable)
    return {
        "tool": "secure-code-agent",
        "reason": reason,
        "install": f"{python} -m pip install '{REQUIREMENT}'",
        "verify": f"{python} -m pip show secure-code-agent",
        "concepts": "security",
    }


def run_security_delegate(
    root: Path, *, changed_revspec: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> DelegateRun:
    """Run `secure-code-agent` over `root` and return its pillar document."""
    if importlib.util.find_spec("secure_code_audit") is None:
        reason = "secure-code-agent is not installed for the interpreter running this audit"
        return DelegateRun(None, reason, [_install_remedy(reason)])
    installed = _installed_version()
    if installed is None or not (SUPPORTED_FLOOR <= installed < SUPPORTED_CEILING):
        shown = ".".join(map(str, installed)) if installed else "an unreadable version"
        reason = (f"secure-code-agent {shown} is installed; this audit runs "
                  f"{REQUIREMENT.removeprefix('secure-code-agent')}")
        return DelegateRun(None, reason, [_install_remedy(reason)])
    with tempfile.TemporaryDirectory(prefix="ma-security-") as scratch:
        out = Path(scratch)
        pillar = out / "security-pillar.json"
        argv = [
            sys.executable, "-c", _ENTRY, str(root),
            "--security-pillar", str(pillar),
            "--output", str(out / "report.md"),
            "--json-output", str(out / "report.json"),
            "--sarif-output", str(out / "report.sarif"),
            "--comment-output", str(out / "comment.md"),
            "--prompt-output", str(out / "prompt.md"),
        ]
        if changed_revspec:
            argv += ["--changed-only", changed_revspec]
        # Exit 1 is the tool's gate verdict, not a failure to measure: the
        # pillar document is still written, and the pillar reports the gate.
        result = run("secure-code-agent", Invocation(
            argv=tuple(argv), findings_exit_codes=(0, 1), cwd=out,
        ), timeout_seconds=timeout_seconds)
        document = read_produced(pillar)
        if document is not None:
            return DelegateRun(document, work_order=_read_text(out / "prompt.md"))
        if result.outcome is Outcome.TIMED_OUT:
            return DelegateRun(None, f"secure-code-agent did not finish within {timeout_seconds}s")
        detail = _last_line(result.stderr) or _last_line(result.stdout) or result.detail
        # No install remedy here: the tool is installed and ran. A rejected
        # configuration or a crash is fixed in the repository or reported
        # upstream, and an install command would send the reader to the
        # wrong place.
        reason = (f"secure-code-agent exited {result.exit_code} without a pillar document"
                  + (f": {detail}" if detail else ""))
        return DelegateRun(None, reason)


def _installed_version() -> tuple[int, ...] | None:
    """The installed release as integers, or `None` when it cannot be read.

    No `packaging` import: this package has no runtime dependencies. A
    pre-release or local suffix is cut at the first non-numeric part, which
    compares a `0.13.0rc1` as `0.13.0` — conservative at the ceiling.
    """
    import importlib.metadata as metadata
    import re

    try:
        text = metadata.version("secure-code-agent")
    except metadata.PackageNotFoundError:
        return None
    parts = []
    for piece in text.split("."):
        match = re.match(r"\d+", piece)
        if not match:
            break
        parts.append(int(match.group()))
        if match.group() != piece:
            break
    return tuple(parts) or None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _last_line(text: str | None) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return lines[-1][:200] if lines else ""
