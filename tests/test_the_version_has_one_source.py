"""The version is written once (D198).

This repository's own audit put `__init__.py` and `config.py` at the top
of its change-coupling table: **64 co-changes at 0.985 confidence**, the
most coupled pair in the codebase. They were coupled because every
release edited both, plus `pyproject.toml`, plus two documents — five
files to change one number.

That is not a tidiness complaint. v3.7.9 was tagged and **failed its
release** because four of the five were updated and the fifth was not.
And `secure-code-agent` shipped a wheel stamped with one version while
every report it produced carried another, because its `pyproject.toml`
held a second copy that drifted.

A test asserting the copies agree would only police the duplication.
Having one of them is the fix: `maintainability_audit.__version__` holds
the literal, `config.VERSION` re-exports it, and `pyproject.toml` reads
it through `[tool.setuptools.dynamic]`.

The two documents that also carry it — the README header and the release
plan's "Last tagged version" row — are prose, and stay prose. They are
already gated by their own tests; what changed is that they are now the
only places a human types the number.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_config_reexports_rather_than_duplicating() -> None:
    """The most coupled pair in the audit, now one value.

    `is` rather than `==`: an equal copy is exactly what this removes.
    """
    from maintainability_audit import __version__
    from maintainability_audit.config import VERSION

    assert VERSION is __version__


def test_config_holds_no_version_literal() -> None:
    """Re-exporting and *also* hardcoding would pass the test above."""
    source = (ROOT / "src" / "maintainability_audit" / "config.py").read_text(
        encoding="utf-8"
    )

    assert not re.search(r'^VERSION\s*=\s*["\']', source, re.MULTILINE), (
        "config.py writes a version literal again; it must re-export the package's"
    )


def test_pyproject_derives_the_version() -> None:
    """The copy that shipped a mis-stamped wheel in the sibling project."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "version" in project["project"].get("dynamic", []), (
        "pyproject declares a static version again, which is a second copy to drift"
    )
    assert "version" not in project["project"], (
        "a static version alongside `dynamic` is the drift this removes"
    )


def test_the_dynamic_version_points_at_the_package() -> None:
    """Declaring it dynamic and reading it from elsewhere would still be two."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    attr = project["tool"]["setuptools"]["dynamic"]["version"]["attr"]

    assert attr == "maintainability_audit.__version__"


def test_only_one_module_writes_the_number() -> None:
    """The population is every module, not a remembered list.

    A third module assigning its own version string is the same defect
    wearing a different name.
    """
    from maintainability_audit import __version__

    writers = [
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src" / "maintainability_audit").rglob("*.py")
        if re.search(rf'["\']{re.escape(__version__)}["\']', path.read_text(encoding="utf-8"))
    ]

    assert writers == ["src/maintainability_audit/__init__.py"], (
        f"the version literal appears in more than one module: {writers}"
    )
