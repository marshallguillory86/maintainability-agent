"""Whether the code answering you is the code you installed.

`config.VERSION` is a source constant. Every surface reports it as
`agent_version`, which means the number is read from whatever code is
loaded — so it is always self-consistent and can never be wrong about
itself. A server running last week's code states last week's version
plainly, with nothing marking it stale, and a reader has no way to tell
that from a correct answer.

The installed distribution's metadata is the second opinion. It is
written to disk by the installer and read fresh on every call, so the
two disagree exactly when something is out of date — and *which* one is
ahead says which thing is out of date:

* **Loaded code behind the metadata.** A process started before an
  upgrade and is still serving the old module. The install is fine; the
  process is stale. Restart it.
* **Loaded code ahead of the metadata.** An editable install, whose
  `dist-info` froze at whatever version was current when
  `pip install -e .` ran. The source tree moves and the metadata does
  not, so `--version` keeps printing the right answer while
  `importlib.metadata` answers something years old. Reinstall it.

The second case is not hypothetical and is not cosmetic. This project
gates its security delegate on `metadata.version("secure-code-agent")`
(`_security_delegate`), so a stale environment does not merely misreport
a number — it can refuse a delegate that is correctly installed, and
report the Security pillar as unmeasured, with every other signal
looking green. On 2026-09-18 an editable venv here carried metadata for
1.8.0 while serving 3.7.8, with `secure-code-agent` metadata at 0.2.0
against a floor of 0.12.7.

The asymmetry this closes: the audit was strict about the *sibling's*
installed version and blind to its own.

Nothing here raises. An unreadable version is not a reason to fail an
audit, so the check reports what it found and says nothing when the two
agree or when metadata cannot be read at all.
"""
from __future__ import annotations

from .config import VERSION


def installed_version() -> str | None:
    """The installed distribution's version, or `None` when unreadable.

    `None` covers a tree run straight from source with nothing installed,
    which is a legitimate way to run this and not a drift to report.
    """
    import importlib.metadata as metadata

    try:
        return metadata.version("maintainability-agent")
    except metadata.PackageNotFoundError:
        return None


def _as_numbers(text: str) -> tuple[int, ...] | None:
    """Leading numeric components, for ordering. No `packaging` import.

    This package has no runtime dependencies, and `_security_delegate`
    reads versions the same way for the same reason.
    """
    import re

    parts: list[int] = []
    for piece in text.split("."):
        match = re.match(r"\d+", piece)
        if not match:
            break
        parts.append(int(match.group()))
        if match.group() != piece:
            break
    return tuple(parts) or None


def version_drift() -> dict[str, str] | None:
    """What is loaded versus what is installed, when they disagree.

    `None` when they agree, and when the installed version cannot be read
    — silence is correct for a source checkout, and a check that fired on
    every uninstalled run would be trained away inside a day.
    """
    installed = installed_version()
    if installed is None or installed == VERSION:
        return None

    running_parts = _as_numbers(VERSION)
    installed_parts = _as_numbers(installed)

    if running_parts is not None and installed_parts is not None and running_parts < installed_parts:
        remedy = (
            "A process started before the upgrade is still serving the old "
            "module. The install is current; restart the agent — for the MCP "
            "server, restart the host or stop the running server process."
        )
    elif running_parts is not None and installed_parts is not None:
        remedy = (
            "The installed distribution's metadata is behind the code, which "
            "is what an editable install does: `dist-info` froze when "
            "`pip install -e .` last ran while the source tree moved on. "
            "Reinstall it (`pip install -e .`). Until then anything reading "
            "`importlib.metadata` — including this audit's own security "
            "delegate range check — sees the old number."
        )
    else:
        remedy = (
            "The loaded code and the installed distribution report different "
            "versions. Reinstall the package, and restart any long-running "
            "process serving it."
        )

    return {
        "running": VERSION,
        "installed": installed,
        "detail": (
            f"The code answering is {VERSION}; the installed distribution says "
            f"{installed}. {remedy}"
        ),
    }
