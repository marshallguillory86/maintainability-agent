"""Class 4 (plan-81dc6870), Part 2: asset-snapshot detection precision.

A saved page asset — versioned page snapshots, or a folder of HTML/CSS
beside images — is not application source. It should drop out of the
declaration and clone populations while keeping its file-length finding.
The detector's job is to recognise those folders *from evidence*, never a
folder-name list (ADR 010), and — the safety margin — to never mistake a
real app template for an asset, which would drop real code from the score.

This file audits the detector in isolation (`_asset_snapshot_directories`),
positive and negative, before it is wired into scoring. The population-level
behaviour is asserted once the wiring lands.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit._discovery import _asset_snapshot_directories
from maintainability_audit.config import DEFAULT_CONFIG
from maintainability_audit.report import build_report


def _tree(root: Path, files: list[str]) -> None:
    for rel in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")


# (label, files, directory-that-must-be-flagged-or-None)
_FLAGGED = [
    ("versioned-snapshot",
     ["renders/scene_v1.2.3.html", "renders/scene_v2.0.0.html"], "renders"),
    ("single-versioned-file",
     ["out/report_v1.0.0.html", "out/data.json"], "out"),
    ("markup-majority-beside-images",
     ["assets/a.html", "assets/b.html", "assets/style.css",
      "assets/logo.png", "assets/hero.svg"], "assets"),
]

_NOT_FLAGGED = [
    ("templates-only-no-images",
     ["templates/home.html", "templates/about.html"]),
    ("real-component-with-one-template",
     ["widget/index.html", "widget/app.js", "widget/logo.png"]),
    ("code-heavy-with-one-page",
     ["src/main.py", "src/util.py", "src/page.html", "src/icon.png"]),
    ("single-page-and-image",
     ["page/index.html", "page/logo.png"]),
    ("markup-not-outnumbering-code",
     ["ui/a.html", "ui/b.html", "ui/a.js", "ui/b.js", "ui/img.png"]),
]


@pytest.mark.parametrize("label,files,expected", _FLAGGED, ids=[c[0] for c in _FLAGGED])
def test_an_asset_snapshot_directory_is_recognised(
    tmp_path: Path, label: str, files: list[str], expected: str,
) -> None:
    _tree(tmp_path, files)
    found = _asset_snapshot_directories(tmp_path, ())
    assert expected in found, f"{label}: {expected!r} not detected -> {found}"
    assert found[expected], "an asset verdict must carry its evidence"


@pytest.mark.parametrize("label,files", _NOT_FLAGGED, ids=[c[0] for c in _NOT_FLAGGED])
def test_real_source_is_never_flagged_as_an_asset(
    tmp_path: Path, label: str, files: list[str],
) -> None:
    """The safety margin: a false positive drops real code from the score,
    so anything with real code, or too little evidence, is left alone."""
    _tree(tmp_path, files)
    found = _asset_snapshot_directories(tmp_path, ())
    assert not found, f"{label}: real source wrongly flagged as asset -> {found}"


def test_the_repository_root_is_never_an_asset(tmp_path: Path) -> None:
    _tree(tmp_path, ["a_v1.0.0.html", "b_v2.0.0.html"])
    found = _asset_snapshot_directories(tmp_path, ())
    assert "." not in found and "" not in found


# --- population level: what an asset moves out of, and keeps -------------


def _asset_and_source_tree(root: Path) -> None:
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text(
        "\n".join(f"def f{i}(x):\n    return x + {i}" for i in range(3)) + "\n",
        encoding="utf-8")
    (root / "renders").mkdir()
    block = "\n".join(f"<div class='row-{i}'>value {i} rendered here now</div>" for i in range(120))
    for version in ("1.0.0", "1.1.0", "2.0.0", "2.1.0"):
        (root / "renders" / f"scene_v{version}.html").write_text(
            "<html>\n" + block + "\n</html>\n", encoding="utf-8")


def test_an_asset_snapshot_keeps_file_length_but_leaves_declarations_and_clones(
    tmp_path: Path,
) -> None:
    """The whole point: a saved page is one file-length row, never a
    declaration population and never the repository's clone problem."""
    _asset_and_source_tree(tmp_path)
    report = build_report(tmp_path, DEFAULT_CONFIG)

    assert any(c["provenance"] == "asset" for c in report["summary"]["classifications"]), \
        "the asset directory was not recorded"
    # File length is kept: a rendered page is still in the file population.
    assert any("renders/" in metric["path"] for metric in report["largest_files"]), \
        "the asset's file length was dropped"
    # Declarations are not: the HTML pages mint no declaration population.
    assert not any("renders/" in hotspot["path"] for hotspot in report["function_hotspots"]), \
        "an asset page reached the declaration population"
    # Clones are not: the four saved copies are not a clone finding.
    asset_dupes = [
        location for finding in report["duplicate_blocks"]
        for location in finding.get("locations", []) if "renders/" in location
    ]
    assert not asset_dupes, f"asset markup reached the clone scan: {asset_dupes}"


def test_a_real_template_beside_code_stays_scored(tmp_path: Path) -> None:
    """The over-correction guard: a real app template folder with source
    beside it is not an asset, and its code still reaches the score."""
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text(
        "<html><script>x</script></html>\n", encoding="utf-8")
    (tmp_path / "web" / "app.js").write_text(
        "function main(){\n  return 1;\n}\n", encoding="utf-8")
    report = build_report(tmp_path, DEFAULT_CONFIG)
    assert not any(c["provenance"] == "asset" for c in report["summary"]["classifications"])
