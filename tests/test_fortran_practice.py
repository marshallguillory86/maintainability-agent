"""Practice detection speaks the Fortran toolchain (1.7.0).

Every list in `_practice` — linter configs, formatter configs, the lint
command pattern, the gate manifests — was written from the Python, JS,
JVM and Go ecosystems. Fortran appeared in none of them, so a Fortran
project that configured a linter and ran it on every change scored as
though it had done neither: **level 2, zero signals.**

The fix is four entries, and the discipline is in the second test:
`fortran-lang/stdlib` runs no linter, and after this change it must
still be level 2. A detector that lifts every Fortran repository is not
detecting anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit._practice import practice_level


def _repo(root: Path, files: dict[str, str]) -> Path:
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


def test_a_fortran_project_that_lints_in_ci_reaches_level_three(tmp_path: Path) -> None:
    """The measured defect: this scored level 2 with no signals at all."""
    root = _repo(tmp_path / "fort", {
        "fpm.toml": 'name = "demo"\n',
        "fortitude.toml": '[check]\nselect = ["C001"]\n',
        ".fprettify.rc": "indent=3\n",
        ".github/workflows/ci.yml": (
            "jobs:\n  test:\n    steps:\n"
            "      - run: fortitude check src\n"
            "      - run: fpm test\n"
        ),
    })

    practice = practice_level(root)
    kinds = {signal["signal"] for signal in practice.signals}

    assert practice.level == 3, practice.summary
    assert "linter-config" in kinds, "fortitude.toml declares a standard"
    assert "formatter-config" in kinds, ".fprettify.rc declares a format"
    assert "lint-in-ci" in kinds, "the workflow runs fortitude on every change"


def test_a_fortran_project_that_lints_nowhere_is_not_lifted(tmp_path: Path) -> None:
    """The falsifier for over-fitting.

    `fortran-lang/stdlib` has CI, an `.editorconfig`, and no linter at
    all — level 2 is the *correct* answer for it, and was before this
    change. A detector that promoted every Fortran repository would be
    measuring the language rather than the practice.
    """
    root = _repo(tmp_path / "quiet", {
        "fpm.toml": 'name = "demo"\n',
        ".editorconfig": "root = true\n",
        ".github/workflows/ci.yml": (
            "jobs:\n  test:\n    steps:\n"
            "      - run: fpm build\n"
            "      - run: fpm test\n"
            "      - run: ctest --test-dir build\n"
        ),
    })

    practice = practice_level(root)

    assert practice.level == 2, (
        "running a test suite is not running a quality check, and this "
        "repository configures no linter"
    )
    assert practice.caps, "the ceiling must be explained, not just applied"


@pytest.mark.parametrize(
    "manifest", ["fpm.toml", "pyproject.toml"],
)
def test_a_gate_declared_in_a_manifest_is_read(tmp_path: Path, manifest: str) -> None:
    """A Fortran project declares its build, its tests and — since
    fortitude 0.9 — its lint settings in `fpm.toml`. A gate written there
    was invisible for the same reason one in `pyproject.toml` would be if
    that file were missing from the list."""
    root = _repo(tmp_path / f"gated-{manifest}", {
        manifest: "[tool.coverage.report]\nfail_under = 90\n",
        "fortitude.toml": '[check]\nselect = ["C001"]\n',
        ".github/workflows/ci.yml": (
            "jobs:\n  test:\n    steps:\n      - run: fortitude check src\n"
        ),
    })

    practice = practice_level(root)
    kinds = {signal["signal"] for signal in practice.signals}

    assert "coverage-gate" in kinds, f"the gate in {manifest} was not read"
    assert practice.level >= 4, "a numeric gate held in CI is level 4"
