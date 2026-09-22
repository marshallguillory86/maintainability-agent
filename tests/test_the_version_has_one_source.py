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


# A module-level assignment of a dotted numeric literal to a name that
# reads like a version: `VERSION = "3.7.16"`, `__version__ = '1.0'`.
# Deliberately not keyed to the *current* version — see the test below.
_VERSION_ASSIGNMENT = re.compile(
    r'^\s*(?P<name>[A-Za-z_][A-Za-z_0-9]*)\s*(?::[^=\n]+)?=\s*'
    r'["\'](?P<value>\d+\.\d+(?:\.\d+)?[^"\']*)["\']',
    re.MULTILINE,
)


def _assigns_a_version(source: str) -> bool:
    """A module-level name containing "version" bound to a dotted number."""
    return any(
        "version" in match.group("name").lower()
        for match in _VERSION_ASSIGNMENT.finditer(source)
    )


def test_only_one_module_writes_the_number() -> None:
    """The population is every module, not a remembered list.

    A third module assigning its own version string is the same defect
    wearing a different name.

    **It used to search for the current version's characters**, which
    made it blind in exactly the direction that matters. A module still
    holding `VERSION = "3.7.16"` after the package moved to 3.7.20 is
    the drift this entry exists to stop, and a substring search for
    "3.7.20" cannot see it — the check passed *because* the copy was
    stale. It now matches the shape of a version assignment, so a second
    writer is caught whether or not it agrees with the first.
    """
    from maintainability_audit import __version__

    writers = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src" / "maintainability_audit").rglob("*.py")
        if _assigns_a_version(path.read_text(encoding="utf-8"))
    )

    assert writers == ["src/maintainability_audit/__init__.py"], (
        f"a version literal is assigned in more than one module: {writers}"
    )
    # Clause two: a regex that matched nothing would pass the assertion
    # above by returning an empty list.
    assert __version__ in (ROOT / "src" / "maintainability_audit" / "__init__.py").read_text(
        encoding="utf-8"
    ), "the one writer does not contain the loaded version"


def test_the_release_gate_reads_the_single_source() -> None:
    """The gate that compares tag to package must read where it lives.

    It read `pyproject`'s static `version` key. D198 removed that key, so
    the gate raised `KeyError` and v3.7.17 failed its release eleven
    seconds in — the fix for a release-breaking duplication broke a
    release, because the check protecting it was reading one of the
    copies.

    Asserted against the workflow text: the gate runs in CI, where no
    test does, and the only thing that can be checked from here is what
    it is told to read.
    """
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    gate = workflow[workflow.index("Verify the tag matches the packaged version"):]
    gate = gate[: gate.index("\n      - name:")]

    assert "__init__.py" in gate, (
        "the release gate does not read the module holding the version literal"
    )
    assert "['project']['version']" not in gate, (
        "the release gate reads pyproject's static version, which no longer exists"
    )


def test_the_release_build_compares_the_artifact_to_the_tag() -> None:
    """The source gate is not a check on the thing that ships (D205).

    The gate above reads a file in the tree, before anything is built. Its
    comment used to claim it checked "the literal the wheel will actually
    carry" — the one thing reading the tree cannot do. The build step
    installed the wheel, printed `maintainability-agent --version`, and
    compared it to nothing, so a wheel whose metadata disagreed with the
    tag would have been printed and published.

    That is the failure D198's own entry cites from the sibling project:
    a wheel stamped with one version while every report it produced
    carried another.

    Asserted against the workflow text, like the gate test above, and
    scoped to the step rather than the file so that an unrelated mention
    of `importlib.metadata` elsewhere cannot satisfy it.
    """
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    step = workflow[workflow.index("Test the built package"):]
    step = step[: step.index("\n      - uses:")]

    assert "pip install dist/" in step, (
        "the build step no longer installs the wheel, so there is no artifact to check"
    )
    assert "importlib.metadata" in step, (
        "the build step does not read the installed artifact's own version"
    )
    assert "GITHUB_REF_NAME" in step, (
        "the build step reads the artifact's version but never compares it to the tag"
    )
    # Printing it is not comparing it: that is exactly what was there.
    assert "exit 1" in step, (
        "the artifact/tag comparison reports without failing the build"
    )
