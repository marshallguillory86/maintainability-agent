"""D23: the built artifact carries the data the code cannot run without.

Every test in this suite ran from a source checkout, where
``Path(__file__).parent.parent.parent / "data"`` happens to resolve to
the repository root. From an installed wheel the same expression points
at ``<site-packages>/../data/analyzer-catalog.json``, a path that has
never existed on any machine. Nine releases shipped that way: the
analyzer catalog and the rubric were declared in no package, copied
into no wheel, and every pip-installed user lost the analyzer pool —
the product's primary evidence source — falling back to built-in
numbers with no signal that anything was missing.

A green suite proved nothing here because the suite never looked at a
built distribution. This one stages the build and reads what came out.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# The files the product cannot function without, as they must appear
# in the distribution: package-relative, never repository-relative.
REQUIRED = (
    "maintainability_audit/_assets/analyzer-catalog.json",
    "maintainability_audit/_assets/standard.md",
)


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The real artifact, built the way a release builds it."""
    pytest.importorskip("setuptools", reason="staging a build needs the backend")
    out = tmp_path_factory.mktemp("build")
    # `build_py` rather than a full wheel: it is the step that copies
    # package data into the staging tree a wheel is zipped from, so it
    # answers exactly the question this defect turned on, and it needs
    # neither the `wheel` package nor a network fetch. A check that can
    # only run where a build frontend happens to be installed would be
    # skipped on the machines most likely to reintroduce the bug.
    result = subprocess.run(
        [
            sys.executable, "-c",
            "from setuptools import setup; setup()",
            "build_py", "--build-lib", str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"build staging failed:\n{result.stdout}\n{result.stderr}")
    return out


def test_the_built_distribution_carries_the_catalog_and_the_standard(
    wheel: Path,
) -> None:
    """Declared package data is a claim; the staged tree is the evidence."""
    staged = {
        str(path.relative_to(wheel))
        for path in wheel.rglob("*")
        if path.is_file()
    }
    for required in REQUIRED:
        assert required in staged, (
            f"{required} was not copied into the distribution; an installed "
            f"copy cannot read it. Staged assets: "
            f"{sorted(name for name in staged if '_assets' in name)}"
        )

    catalog = json.loads(
        (wheel / "maintainability_audit/_assets/analyzer-catalog.json").read_text(
            encoding="utf-8"
        )
    )
    # Present but empty is the same outage with a better disguise.
    assert catalog["tools"], "the shipped catalog carries no tools"


def test_no_runtime_asset_is_read_from_outside_the_package() -> None:
    """The path shape that caused this, refused at its source.

    Climbing to `parents[2]` or `parent.parent.parent` from a module
    inside the package leaves the package entirely. In a checkout that
    lands on the repository root and everything appears to work; from
    site-packages it lands somewhere arbitrary. No runtime module may
    do it, whatever it is reaching for.
    """
    offenders = []
    for module in sorted((ROOT / "src" / "maintainability_audit").rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        for marker in ("parents[2]", "parent.parent.parent"):
            if marker in text:
                offenders.append(f"{module.relative_to(ROOT)} uses {marker}")

    assert not offenders, (
        "runtime modules resolve paths outside the installed package: "
        + "; ".join(offenders)
    )


def test_the_packaged_standard_matches_the_documented_one() -> None:
    """The mirror is byte-pinned, like the skill payload it follows.

    `docs/standard.md` is what a reader opens on the forge; the copy in
    `_assets` is what the MCP resource serves. Two copies drift unless
    something holds them together.
    """
    documented = (ROOT / "docs" / "standard.md").read_text(encoding="utf-8")
    packaged = (
        ROOT / "src" / "maintainability_audit" / "_assets" / "standard.md"
    ).read_text(encoding="utf-8")
    assert packaged == documented, (
        "the packaged standard drifted from docs/standard.md; copy it across"
    )
