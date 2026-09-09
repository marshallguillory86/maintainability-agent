"""The environment work order: what would widen coverage, for a human to run.

ADR 006 §2c. Coverage names the tools that did not run; this is the
artifact on top — for each selected-but-unrunnable tool, why it did not
run, the exact install command, and how to verify the install took. The
same shape as the code work order, deliberately: one artifact, whether a
person acts on it or hands it to their own agent.

**The agent never installs anything.** Installation is a network and
privilege action belonging to the user, so this module emits text and
imports nothing that can spawn a process. `test_the_agent_never_runs_the_install_command`
holds that structurally.
"""
from __future__ import annotations

import shlex
import sys
from typing import Any

# Outcomes a user can act on. `timed-out` and `failed` are excluded on
# purpose: the tool is present, so there is nothing to install, and
# advising a reinstall for a timeout sends the reader to fix the wrong
# thing. Those stay coverage facts.
_ACTIONABLE = ("not-installed", "not-working", "no-config")

# How each adapter-backed tool is actually acquired. Python tools install
# into the same interpreter that runs the audit; Node tools are global
# npm installs, matching docs/analyzer-pool.md. A slug not listed falls
# back to pip, which is right for every current Python adapter and wrong
# loudly (pip will say so) rather than silently for anything else.
_INSTALL: dict[str, str] = {
    "jscpd": "npm install -g jscpd",
    "eslint": "npm install -g eslint",
    # A JVM tool, not a Python package: the pip fallback would name a
    # different project entirely.
    "pmd": "brew install pmd",
    "checkstyle": "brew install checkstyle",
    "spotbugs": "brew install spotbugs",
    # The distribution is `fortitude-lint`; the command it installs is
    # `fortitude`. Falling back to `pip install fortitude` would name a
    # different project entirely, which is the same trap the JVM tools
    # above are here to avoid.
    "fortitude": "pip install fortitude-lint",
}

# `--version` is the availability probe the runner itself uses, so the
# verification a reader runs is the same check the next audit will run.
_VERIFY: dict[str, str] = {
    "multimetric": "pip show multimetric",  # its CLI has no --version
    "eslint": "npx eslint --version",
    "jscpd": "npx jscpd --version",
    "pmd": "pmd --version",
    "checkstyle": "checkstyle --version",
    "spotbugs": "spotbugs -version",
}


def _remedy_for(slug: str) -> dict[str, str]:
    """The install and verify commands, bound to the interpreter that audits.

    A remedy is only a remedy if it addresses the same environment the
    next audit reads. `pip install lizard` and `lizard --version` name
    neither: they address whatever `pip` and `lizard` `PATH` happens to
    resolve, which on any machine with more than one Python is a
    different interpreter than the one that just reported the tool
    missing (D144).

    That is not hypothetical here. D142 was the same gap seen from the
    other side — the agent could not find tools the operator had already
    installed, because `pip` had put them where `PATH` did not look. A
    work order that hands back a bare `pip` sends the operator around
    that loop again, and the second time it looks like the remedy simply
    does not work.

    So pip-backed adapters emit `{sys.executable} -m pip ...`. The dict
    entries stay spelled as distribution names — `pip install
    fortitude-lint` — because two tests derive the CI install list from
    them, and rewriting the dict would move a fact that belongs at the
    emit site into the data.

    Verification moves from `--version` to `pip show` for these, and the
    reason is worth stating because the old comment argued the opposite:
    `--version` was chosen to run the same probe the runner runs. Since
    D142 the runner does not probe `PATH` at all — it searches this
    interpreter's script directories — so a bare `{slug} --version`
    verifies a *different* thing than the audit does. `pip show` asks the
    question that actually decides the next run: is this distribution
    installed for this interpreter.

    Node and JVM overrides are untouched. `npx` and `brew` are not
    interpreter-scoped and rewriting them through `sys.executable` would
    name a Python package that does not exist.
    """
    install = _INSTALL.get(slug, f"pip install {slug}")
    if not install.startswith("pip install"):
        return {"install": install, "verify": _VERIFY.get(slug, f"{slug} --version")}
    distribution = install.split()[-1]
    return {
        "install": _pip_command("install", distribution),
        "verify": _pip_command("show", distribution),
    }


def _pip_command(action: str, distribution: str) -> str:
    """A pip invocation that cannot resolve to another interpreter."""
    return f"{shlex.quote(sys.executable)} -m pip {action} {distribution}"


def environment_work_order(coverage: list[Any]) -> list[dict[str, str]]:
    """One item per selected analyzer that could not contribute.

    Built-ins are skipped — they always run and cannot be installed — and
    so is every outcome that is not an installation problem. An empty
    list is a real answer: everything selected ran.
    """
    items: list[dict[str, str]] = []
    for entry in coverage:
        if getattr(entry, "tier", "analyzer") != "analyzer":
            continue
        remedy = getattr(entry, "remedy", None)
        if remedy is not None:
            # A non-install remedy the adapter stated itself: the user
            # acts (a build, per ADR 012), the agent only reports.
            install, verify = remedy
            items.append({
                "tool": entry.slug,
                "reason": entry.detail or f"outcome: {entry.outcome}",
                "install": install,
                "verify": verify,
                "concepts": ", ".join(entry.concepts),
            })
            continue
        if entry.outcome not in _ACTIONABLE:
            continue
        items.append({
            "tool": entry.slug,
            "reason": entry.detail or f"outcome: {entry.outcome}",
            **_remedy_for(entry.slug),
            # What installing the tool restores, so a host can explain
            # the trade instead of relaying a bare command (D9).
            "concepts": ", ".join(entry.concepts),
        })
    return items
