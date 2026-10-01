"""Every workflow step that installs the analyzer pool installs all of it.

`test_ci_installs_every_pip_installable_adapter` checks the **union** of
every `pip install` in the workflows, so a step that left a tool out
passed as long as some other step installed it. Two did. The
resolve-constraints and analyzer-drift steps never installed
`fortitude-lint`, so the weekly drift check compared the pins against a
smaller pool than the one they pin, and reported the Fortran analyzer and
its dependencies as drift (issue #284).

Per step, then: any install that names the pool names exactly the pool,
derived from the catalog the same way the union test derives it.
"""

from __future__ import annotations

from pathlib import Path

from test_ci_installs_the_analyzer_pool import (
    _YAML_KEY,
    WORKFLOW,
    _expected_package,
    _pip_installable_adapters,
)


def _pool() -> set[str]:
    return {_expected_package(slug) for slug in _pip_installable_adapters()}


def _command_words(lines: list[str], index: int) -> list[str]:
    """The words of the `pip install` on `lines[index]`, continuation lines included."""
    words = lines[index].split("pip install", 1)[1].split()
    for following in lines[index + 1:]:
        stripped = following.strip()
        if not stripped or stripped.startswith("- ") or _YAML_KEY.match(stripped):
            break
        words += stripped.split()
    return words


def _packages(words: list[str]) -> set[str]:
    return {w.rstrip("\\") for w in words if w and not w.startswith("-") and w != "\\"}


def _pool_installs() -> list[tuple[str, int, set[str]]]:
    """Each `pip install` that names the pool: (file, line, packages)."""
    pool = _pool()
    found = []
    for path in sorted(WORKFLOW.parent.glob("*.yml")):
        lines = [line for line in path.read_text(encoding="utf-8").splitlines()
                 if not line.lstrip().startswith("#")]
        for index in (i for i, line in enumerate(lines) if "pip install" in line):
            packages = _packages(_command_words(lines, index))
            if len(packages & pool) > 2:
                found.append((Path(path).name, index + 1, packages))
    return found


def test_every_pool_install_names_the_whole_pool() -> None:
    pool = _pool()
    installs = _pool_installs()
    short = [(name, line, sorted(pool - packages)) for name, line, packages in installs
             if pool - packages]

    assert len(installs) >= 4, "the parser found too few pool installs; this test would pass vacuously"
    assert not short, f"these steps install part of the analyzer pool: {short}"
