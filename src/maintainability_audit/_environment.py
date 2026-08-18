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
}

# `--version` is the availability probe the runner itself uses, so the
# verification a reader runs is the same check the next audit will run.
_VERIFY: dict[str, str] = {
    "multimetric": "pip show multimetric",  # its CLI has no --version
    "eslint": "npx eslint --version",
    "jscpd": "npx jscpd --version",
    "pmd": "pmd --version",
}


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
        if entry.outcome not in _ACTIONABLE:
            continue
        items.append({
            "tool": entry.slug,
            "reason": entry.detail or f"outcome: {entry.outcome}",
            "install": _INSTALL.get(entry.slug, f"pip install {entry.slug}"),
            "verify": _VERIFY.get(entry.slug, f"{entry.slug} --version"),
            # What installing the tool restores, so a host can explain
            # the trade instead of relaying a bare command (D9).
            "concepts": ", ".join(entry.concepts),
        })
    return items
