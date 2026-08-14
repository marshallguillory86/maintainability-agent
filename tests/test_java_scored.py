"""Java reaches the declaration population, and the fixtures do not.

`test_java_wiring` proves the wiring is *present* by reading the source:
the suffix is listed, the branch exists, the exclusion is configured.
These are the same claims asserted from the other end — by running an
audit and looking at what it counted — because every defect this
project has shipped in this area was a structure that existed and a
number that stayed zero.

Two directions, both required:

- **An included Java file produces declarations.** Not "is opened", not
  "is counted as read": a file read for length alone with a declaration
  population of zero is precisely the state that let a 9,639-declaration
  repository report a denominator of nothing.
- **This repository's own ranger fixtures stay out of its own audit.**
  They exist to be awkward — a class that is nothing but a constructor,
  an annotation carrying a value — and scoring a parser's test corpus
  would let it move the number this project publishes about itself.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from maintainability_audit.config import load_config
from maintainability_audit.report import build_report

ROOT = Path(__file__).resolve().parents[1]

WIDGET = """package fixture;

public class Widget {

    public Widget(int size) {
        this.size = size;
    }

    public int doubled(int value) {
        if (value > 0) {
            return value * 2;
        }
        return 0;
    }
}
"""


def _repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def test_an_included_java_file_produces_declarations(tmp_path: Path) -> None:
    """`declarations_scanned` is the denominator under every rate.

    A Java file that is opened but contributes nothing to it is the
    "read but unparsed" state — and the report would then blame the
    population floor, telling the reader their repository is too small
    when the truth is that nothing parsed it.
    """
    root = _repo(tmp_path / "java", {"src/Widget.java": WIDGET})
    summary = build_report(root, load_config(None))["summary"]

    assert summary["declarations_scanned"] > 0, (
        "an included Java file contributed no declarations"
    )
    assert not summary["unread_source"], (
        f"Java is still reported unread: {summary['unread_source']}"
    )
    assert not summary["undetected_declarations"], (
        f"Java is opened and reported unparseable: {summary['undetected_declarations']}"
    )


def test_java_methods_reach_the_findings(tmp_path: Path) -> None:
    """Parsed is not the same as measured.

    A population can be non-zero while every declaration is invisible to
    the thresholds. The fixture's `doubled` is an ordinary short method,
    so it should appear as a scanned declaration and trip nothing.
    """
    root = _repo(tmp_path / "graded", {"src/Widget.java": WIDGET})
    report = build_report(root, load_config(None))

    assert report["summary"]["declarations_scanned"] >= 3, (
        "the class, its constructor and its method should all be counted"
    )
    assert "src/Widget.java" in {item["path"] for item in report["largest_files"]}


def test_this_repository_does_not_score_its_own_ranger_fixtures() -> None:
    """The parser's corpus is input to a test, not source under audit."""
    report = build_report(ROOT, load_config(None))

    scanned = {item["path"] for item in report["largest_files"]}
    assert not [path for path in scanned if "tests/fixtures/java" in path], (
        "the ranger fixtures were scanned as project source"
    )

    unread = {item["suffix"] for item in report["summary"]["unread_source"]}
    assert ".java" not in unread, (
        "the excluded fixtures are still counted as unread Java source"
    )
