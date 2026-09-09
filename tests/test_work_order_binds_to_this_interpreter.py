"""Every pip-backed environment remedy stays with the audit interpreter.

An environment work order is only a remedy if its install and verification
commands address the same interpreter (or its script directory) that the
next audit uses.  Walking the catalog catches a newly added adapter as well
as the fallback install command, without accepting an accidental PATH hit.
"""
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

from maintainability_audit._analysis import ToolCoverage
from maintainability_audit._catalog import CATALOG_PATH
from maintainability_audit._environment import _INSTALL, environment_work_order
from maintainability_audit._runner import _agent_script_dirs


def _pip_installable_adapters() -> set[str]:
    """Implemented adapters whose work-order install is pip-backed."""
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    adapters = {
        tool["slug"]
        for tool in catalog["tools"]
        if tool.get("adapter") == "implemented"
        and _INSTALL.get(tool["slug"], "pip install").startswith("pip install")
    }
    assert adapters, "the catalog has no pip-installable adapters to bind"
    return adapters


def _coverage(slugs: set[str]) -> list[ToolCoverage]:
    return [
        ToolCoverage(slug=slug, outcome="not-installed", concepts=("coverage",))
        for slug in sorted(slugs)
    ]


def _is_agent_script(command: str) -> bool:
    executable = Path(shlex.split(command)[0])
    return executable.parent in _agent_script_dirs()


def _is_this_interpreters_pip(command: str) -> bool:
    words = shlex.split(command)
    return words[:3] == [sys.executable, "-m", "pip"]


def _is_bound_to_this_agent(command: str) -> bool:
    words = shlex.split(command)
    return bool(words) and (words[0] == sys.executable or _is_agent_script(command))


def test_pip_adapter_work_orders_bind_install_and_verify_to_this_agent() -> None:
    """No pip-backed adapter may rely on whichever commands PATH finds."""
    adapters = _pip_installable_adapters()
    order = environment_work_order(_coverage(adapters))
    items = {item["tool"]: item for item in order}

    assert set(items) == adapters, (
        "not-installed pip adapters must all become environment work items; "
        f"expected {sorted(adapters)}, got {sorted(items)}"
    )
    for slug, item in items.items():
        assert _is_this_interpreters_pip(item["install"]) or _is_agent_script(item["install"]), (
            f"{slug} installs through a foreign or bare pip command: {item['install']!r}"
        )
        assert _is_bound_to_this_agent(item["verify"]), (
            f"{slug} verifies through a foreign or bare PATH command: {item['verify']!r}"
        )
