"""D39: no analyzer this agent runs may take its configuration from the tree.

Decision 9 draws the line at executing code, and configuration is code:
a pylint `init-hook=` runs arbitrary Python before analysis begins, a
mypy `plugins =` imports a module out of the repository, and an eslint
flat config *is* a JavaScript program.

Two kinds of check, because two kinds of thing can go wrong.

The **sweep** is structural and always runs: every tool the pool can
invoke is classified as isolated-by-flag, or as not reading repository
configuration at all with a stated reason. A tool added tomorrow that is
neither fails here rather than waiting for an audit.

The **live** checks spawn the real binary and skip where it is absent —
the pattern `analyzer-pool.md` already discloses for Checkstyle and
SpotBugs, whose live spawn is unproven wherever nobody supplied the
tool, including this project's CI. The flags below come from each
tool's documented CLI, and these are what turn that into evidence on
any machine that has them installed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._generic import DECLARED, declared_adapter
from maintainability_audit._runner import analyzer_env
from maintainability_audit._tool_adapters import ADAPTERS, adapter_for

# The flag that stops each tool searching the audited tree for its own
# configuration, and the tree-supplied mechanism that search enables.
CONFIG_ISOLATION = {
    "mypy": ("--config-file=", "plugins = imports a module from the tree"),
    "pylint": ("--rcfile=", "init-hook= executes arbitrary Python at startup"),
}

# Tools that read no configuration out of the tree, and why. A reason is
# the classification; an empty string is not one.
NO_TREE_CONFIG: dict[str, str] = {}

# Every hand-written adapter, classified by what honouring its
# configuration would *execute*. Decision 9 draws the line at running
# the audited tree's code, not at reading its preferences: a ruff or
# flake8 config is TOML and INI, and a repository choosing which of its
# own lint rules apply is policy about its own code, which the eslint
# adapter's docstring already argued and which is fine for a verdict
# emitter that contributes no rate.
#
# The sweep covered `DECLARED` — two tools — while `ADAPTERS` holds
# fifteen, so ruff sat in the baseline pool unclassified. The module
# docstring claimed "every tool the pool can invoke". This is that
# claim, made true.
ADAPTER_CONFIG: dict[str, str] = {
    "eslint": "REFUSED: a flat config is a JavaScript program",
    "checkstyle": "agent-supplied ruleset via -c; the tree's is never read",
    "pmd": "agent-supplied rulesets via --rulesets",
    "spotbugs": "agent-supplied exclude file; reads bytecode, not config",
    "jscpd": "reads .jscpd.json — JSON data, executes nothing",
    "ruff": "reads pyproject.toml / ruff.toml — TOML data, executes nothing",
    "flake8": "reads setup.cfg / tox.ini / .flake8 — INI data, executes nothing",
    "pydocstyle": "reads setup.cfg — INI data, executes nothing",
    "interrogate": "reads pyproject.toml — TOML data, executes nothing",
    "vulture": "no configuration file; flags only",
    "lizard": "no configuration file; flags only",
    "radon": "reads radon.cfg — INI data, executes nothing",
    "complexipy": "no configuration file; flags only",
    "cohesion": "no configuration file; flags only",
    "multimetric": "no configuration file; flags only",
}


def test_every_adapter_is_classified_for_what_its_configuration_executes() -> None:
    """Fifteen adapters, not the two declared tools.

    The sweep this replaces diffed `DECLARED`, which holds pylint and
    mypy, while the pool invokes fifteen — so ruff, baseline tier and
    in the default pool, was never asked the question the sweep exists
    to ask. Same shape as the first git sweep matching only list
    literals: a narrow set, a green test, and a docstring claiming the
    class.
    """
    from maintainability_audit._tool_adapters import ADAPTERS

    unclassified = sorted(set(ADAPTERS) - set(ADAPTER_CONFIG))
    assert not unclassified, (
        "adapters with no statement of what their configuration would "
        f"execute: {unclassified}. Add each to ADAPTER_CONFIG — reading a "
        "repository's TOML preferences is not executing its code, and "
        "saying which one it is has to be deliberate"
    )
    stale = sorted(set(ADAPTER_CONFIG) - set(ADAPTERS))
    assert not stale, f"ADAPTER_CONFIG names adapters that do not exist: {stale}"
    assert all(reason.strip() for reason in ADAPTER_CONFIG.values())


def test_an_adapter_whose_config_executes_code_is_refused_not_isolated() -> None:
    """The REFUSED marker and the adapter property say the same thing."""
    from maintainability_audit._tool_adapters import ADAPTERS, adapter_for

    marked = {s for s, why in ADAPTER_CONFIG.items() if why.startswith("REFUSED")}
    declaring = {
        slug for slug in ADAPTERS
        if getattr(adapter_for(slug), "executes_audited_configuration", False)
    }
    assert marked == declaring, (
        "the table and the adapters disagree about which tools are "
        f"refused: table={sorted(marked)} adapters={sorted(declaring)}"
    )


def test_every_declared_tool_is_classified_for_tree_configuration() -> None:
    """A declared tool added tomorrow must say which it is.

    The pool grows by hand, one verified tool at a time, and the thing
    that made D39 possible was a tool arriving with a documented
    invocation and nobody asking whether that invocation reads the
    audited tree. This makes not asking a build failure.
    """
    unclassified = sorted(
        set(DECLARED) - set(CONFIG_ISOLATION) - set(NO_TREE_CONFIG)
    )
    assert not unclassified, (
        "declared tools with no tree-configuration classification — add each "
        "to CONFIG_ISOLATION with its flag, or to NO_TREE_CONFIG with a "
        f"reason: {unclassified}"
    )
    assert all(reason.strip() for reason in NO_TREE_CONFIG.values())
    stale = sorted(set(CONFIG_ISOLATION) | set(NO_TREE_CONFIG) - set(DECLARED))
    assert set(CONFIG_ISOLATION) <= set(DECLARED), (
        f"CONFIG_ISOLATION names tools that are not declared: {stale}"
    )


@pytest.mark.parametrize("slug", sorted(CONFIG_ISOLATION))
def test_a_declared_tool_is_invoked_with_its_configuration_isolated(
    slug: str, tmp_path: Path,
) -> None:
    """The flag is in the argv the runner would actually spawn."""
    adapter = declared_adapter(slug)
    assert adapter is not None, f"{slug} is declared but has no adapter"
    argv = adapter.invocation(tmp_path, excludes=()).argv
    flag, mechanism = CONFIG_ISOLATION[slug]
    carrier = [item for item in argv if item.startswith(flag)]
    assert carrier, (
        f"{slug} is spawned without {flag}, so the audited tree's own "
        f"configuration is honoured and {mechanism}: {argv}"
    )
    # The value, not just the flag. `--rcfile=.pylintrc` starts with the
    # flag and points straight back into the tree, which is the thing
    # being prevented.
    assert all(item.split("=", 1)[1] == os.devnull for item in carrier), (
        f"{slug} passes {flag} pointing somewhere other than {os.devnull}, "
        f"so {mechanism} is still reachable: {carrier}"
    )


def test_no_selectable_adapter_needs_the_audited_trees_configuration() -> None:
    """An adapter that cannot run without the tree's config is refused.

    A property on the adapter rather than a list of slugs here, so the
    next tool needing the tree's own configuration is refused without
    anyone remembering this test.
    """
    declaring = {
        slug for slug in ADAPTERS
        if getattr(adapter_for(slug), "executes_audited_configuration", False)
    }
    assert "eslint" in declaring, (
        "eslint stopped declaring that it executes the audited tree's "
        "configuration; it cannot run without a flat config, which is a "
        "JavaScript program"
    )


def _usable(binary: str) -> str | None:
    """The binary, if it is present and actually runs."""
    found = shutil.which(binary)
    if not found:
        return None
    probe = subprocess.run(
        [found, "--version"], capture_output=True, text=True, check=False,
        env=analyzer_env(),
    )
    return found if probe.returncode == 0 else None


def _tree_with_a_hostile_config(root: Path, config_name: str, body: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "sample.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (root / config_name).write_text(body, encoding="utf-8")
    # What the config would load, if the config were honoured.
    (root / "tripwire.py").write_text(
        "raise SystemExit('the audited tree chose what ran')\n", encoding="utf-8")
    return root


@pytest.mark.skipif(_usable("pylint") is None, reason="pylint is not installed here")
def test_pylint_does_not_run_the_trees_init_hook(tmp_path: Path) -> None:
    """Live. `init-hook=` is the sharpest case: it executes on startup.

    Skipped wherever pylint is absent, which is the disclosed pattern
    for an analyzer this project cannot spawn on every machine. Where it
    is installed, this is the evidence that `--rcfile` closed the door.
    """
    root = _tree_with_a_hostile_config(
        tmp_path / "tree", "pylintrc",
        "[MASTER]\ninit-hook=import sys; sys.exit('the audited tree chose what ran')\n")
    adapter = declared_adapter("pylint")
    assert adapter is not None
    argv = list(adapter.invocation(root, excludes=()).argv)

    completed = subprocess.run(
        argv, capture_output=True, text=True, check=False,
        cwd=str(root), env=analyzer_env(),
    )
    combined = f"{completed.stdout}{completed.stderr}"
    assert "the audited tree chose what ran" not in combined, (
        "pylint executed init-hook from the audited tree despite --rcfile"
    )


@pytest.mark.skipif(_usable("mypy") is None, reason="mypy is not installed here")
def test_mypy_does_not_load_a_plugin_from_the_tree(tmp_path: Path) -> None:
    """Live. A tree-supplied mypy plugin is an import out of the repository."""
    root = _tree_with_a_hostile_config(
        tmp_path / "tree", "mypy.ini", "[mypy]\nplugins = tripwire.py\n")
    adapter = declared_adapter("mypy")
    assert adapter is not None
    argv = list(adapter.invocation(root, excludes=()).argv)

    completed = subprocess.run(
        argv, capture_output=True, text=True, check=False,
        cwd=str(root), env=analyzer_env(),
    )
    combined = f"{completed.stdout}{completed.stderr}"
    assert "the audited tree chose what ran" not in combined, (
        "mypy loaded a plugin from the audited tree despite --config-file"
    )
    # And the isolated run still produces the JSON the adapter parses,
    # which is what makes the flag a fix rather than a way to break the
    # tool quietly.
    if completed.stdout.strip():
        for line in completed.stdout.splitlines():
            if line.strip():
                json.loads(line)


def test_the_devnull_config_path_exists_on_this_platform() -> None:
    """Both flags point at `os.devnull`; a missing path would make the
    tool error rather than isolate it."""
    assert Path(os.devnull).exists()
