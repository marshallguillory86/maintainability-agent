"""TDD-shaped structure: pairing, constructs, unpaired fail-band, cap.

Chronology is not measured. A `pass` in a test file still counts as
structure. Mutation: a 90-line unpaired production function next to a
full test suite must not report testability 5.0.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from maintainability_audit._test_pairing import describe_tdd, subject_stem
from maintainability_audit.config import load_config
from maintainability_audit.report import build_report


def test_subject_stem_pairs_conventional_names() -> None:
    assert subject_stem("web/src/pages/Dashboard.tsx") == subject_stem(
        "web/src/test/Dashboard.test.tsx"
    )
    assert subject_stem("api/src/foo.py") == subject_stem("api/tests/test_foo.py")
    assert subject_stem("pkg/bar.py") == subject_stem("pkg/bar_test.py")
    assert subject_stem("lib/util.ts") == subject_stem("lib/util.spec.ts")


def test_subject_stem_pairs_the_fortran_conventions() -> None:
    """Fortran names its tests four ways, and pairing must know all four.

    fpm puts them in `test/`; test-drive writes `test_gravity.f90`;
    pFUnit writes `.pf` files and the camelCase `testGravity_mod.F90`.
    A module file is conventionally `gravity_mod.f90`, so `_mod` has to
    come off both sides or the stems never meet.

    Claiming Fortran in `PAIRABLE` without these would report untested
    production code on every Fortran repository in existence — one
    confident finding, wrong everywhere, which is the failure this
    project exists to prevent.
    """
    production = subject_stem("src/gravity_mod.f90")

    assert production == subject_stem("src/gravity.f90")
    assert production == subject_stem("test/test_gravity.f90")
    assert production == subject_stem("test/gravity_test.f90")
    assert production == subject_stem("tests/testGravity_mod.F90")
    assert production == subject_stem("tests/test_gravity.pf")


def test_a_pfunit_file_is_a_test_wherever_it_sits() -> None:
    """A `.pf` file exists to become a test suite and holds nothing else,
    so it is a test even outside a `test/` directory."""
    from maintainability_audit._metrics_types import is_test_path

    assert is_test_path("src/gravity.pf")
    assert not is_test_path("src/gravity_mod.f90")


def _repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def _tiny(n: int = 40) -> dict[str, str]:
    files = {f"pkg/mod{i}.py": "def f():\n    return 1\n" for i in range(n)}
    files.update(
        {f"tests/test_mod{i}.py": "def test_f():\n    assert True\n" for i in range(n)}
    )
    return files


def test_describe_tdd_counts_a_colocated_pair(tmp_path: Path) -> None:
    from maintainability_audit.metrics import collect_metrics

    root = _repo(tmp_path / "pair", {
        "src/app.py": "def run():\n    return 1\n",
        "tests/test_app.py": "import pytest\n\ndef test_run():\n    assert True\n",
    })
    _files, file_metrics, function_metrics = collect_metrics(
        root, load_config(None), None)
    structure = describe_tdd(root, file_metrics, function_metrics)
    assert structure["paired_production_files"] == 1
    assert structure["detected"] is True
    assert structure["constructs"]["pytest"] >= 1
    assert structure["unpaired_fail_band"] == []


def test_an_unpaired_fail_band_function_is_named(tmp_path: Path) -> None:
    from maintainability_audit.metrics import collect_metrics

    long_fn = "def big():\n" + "    x = 1\n" * 85 + "    return x\n"
    root = _repo(tmp_path / "unpaired", {
        **_tiny(20),
        "pkg/page.py": long_fn,
    })
    _files, file_metrics, function_metrics = collect_metrics(
        root, load_config(None), None)
    structure = describe_tdd(root, file_metrics, function_metrics)
    paths = {item["path"] for item in structure["unpaired_fail_band"]}
    assert "pkg/page.py" in paths
    assert any(item["kind"] == "declaration" for item in structure["unpaired_fail_band"])


def test_html_is_not_an_unpaired_page(tmp_path: Path) -> None:
    from maintainability_audit.metrics import collect_metrics

    html = "<html>" + ("<p>x</p>\n" * 90) + "</html>\n"
    root = _repo(tmp_path / "html", {**_tiny(10), "graphics/scene.html": html})
    _files, file_metrics, function_metrics = collect_metrics(
        root, load_config(None), None)
    structure = describe_tdd(root, file_metrics, function_metrics)
    assert all("scene.html" not in item["path"] for item in structure["unpaired_fail_band"])


def test_unpaired_fail_band_caps_testability(tmp_path: Path) -> None:
    long_fn = "def big():\n" + "    x = 1\n" * 85 + "    return x\n"
    root = _repo(tmp_path / "cap", {**_tiny(80), "pkg/page.py": long_fn})
    report = build_report(root, load_config(None))
    structure = report["tdd_structure"]
    assert structure["unpaired_fail_band"]
    assert report["score"]["categories"]["testability"] <= 4.0
    titles = [item["title"] for item in report["work_order"]]
    assert any("unpaired" in title for title in titles)
    blockers = " ".join(report["score"].get("verified_grade_blockers") or [])
    if report["score"].get("verified_grade"):
        assert "unpaired" in blockers.lower()


def test_tdd_sentence_reaches_markdown_html_and_prompt(tmp_path: Path) -> None:
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.renderers import render_html, render_markdown

    root = _repo(tmp_path / "skins", _tiny(20))
    report = build_report(root, load_config(None))
    markdown = render_markdown(report)
    html = render_html(report, [])
    prompt = render_ai_prompt(report)
    assert "## TDD-shaped tests" in markdown
    assert "<h2>TDD-shaped tests</h2>" in html
    assert "Chronology is not measured" in markdown
    assert "Chronology is not measured" in html
    assert "Chronology is not measured" in prompt


def test_zero_pairs_says_none_detected(tmp_path: Path) -> None:
    root = _repo(tmp_path / "none", {
        f"pkg/mod{i}.py": "def f():\n    return 1\n" for i in range(20)
    })
    report = build_report(root, load_config(None))
    assert report["tdd_structure"]["detected"] is False
    assert "No TDD-shaped test files were detected" in render_markdown_safe(report)


def render_markdown_safe(report: dict) -> str:
    from maintainability_audit.renderers import render_markdown
    return render_markdown(report)
