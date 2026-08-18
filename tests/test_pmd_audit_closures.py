"""Closures for the 549fcad audit queue on the PMD slice.

Six commitments: a complexity-concern pool keeps PMD; applicability and
the coverage row state what the integration reads (java), not what the
tool upstream could; a tree with nothing PMD reads is a coverage fact,
never a spawned CLI error; the recorded version is a version, not
ASCII art; an unmapped rule lands on a declared concept; and a
truncated raw capture is said on the coverage row.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from maintainability_audit import _runner
from maintainability_audit._adapters import Exclusions
from maintainability_audit._analysis import ToolCoverage
from maintainability_audit._catalog import load_catalog, resolve_pool
from maintainability_audit._documents import _coverage_entry
from maintainability_audit._runner import Outcome, ToolResult, version_line
from maintainability_audit._tool_adapters import adapter_for
from maintainability_audit.config import load_config
from maintainability_audit.report import build_report


def _config(**analyzers: Any) -> dict[str, Any]:
    config = load_config(None)
    config["analyzers"].update({
        "run": True, "depth": "moderate", "license_policy": "permissive",
        "allow_tools": ["pmd"],
        "deny_tools": sorted(
            tool["slug"] for tool in load_catalog() if tool["slug"] != "pmd"
        ),
        **analyzers,
    })
    return config


def _repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True)
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _row(report: dict[str, Any], slug: str) -> tuple[str, dict[str, Any]]:
    for outcome, rows in report["analyzer_coverage"]["by_outcome"].items():
        for row in rows:
            if row["tool"] == slug:
                return outcome, row
    raise AssertionError(f"{slug} absent from coverage")


def test_a_complexity_concern_pool_keeps_pmd() -> None:
    """Audit M: measures name the concern, so concern pools can select it."""
    config = load_config(None)
    config["analyzers"].update({
        "run": True, "depth": "moderate", "license_policy": "permissive",
        "concerns": ["complexity"],
    })
    pool, _decisions = resolve_pool(config)
    assert "pmd" in {tool["slug"] for tool in pool}, (
        "a complexity-only pool dropped the complexity tool"
    )


def test_a_javascript_tree_is_not_applicable_for_pmd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit M: applicability follows what the adapter reads, not the catalog."""
    root = _repo(tmp_path / "js", {"app.js": "const x = 1;\n"})
    monkeypatch.setattr(_runner, "locate", lambda _executable: None)

    report = build_report(root, _config(), run_analyzers=True)
    outcome, row = _row(report, "pmd")

    assert outcome == "not-applicable", (
        "a JS-only tree invited a Java-only integration to spawn"
    )
    assert row["languages"] == ["java"], (
        "the coverage row claims languages the integration does not read"
    )


def test_a_java_tree_with_everything_excluded_stays_a_coverage_fact(
    tmp_path: Path,
) -> None:
    """Audit M: nothing to scan is not-applicable, never a spawned exit 2."""
    adapter = adapter_for("pmd")
    root = _repo(tmp_path / "vendored", {
        "vendor/Only.java": "class Only {}\n",
        "README.md": "# fixture\n",
    })

    assert adapter.has_targets(root, excludes=()) is True
    assert adapter.has_targets(root, excludes=("vendor/",)) is False


def test_pmd_expand_files_honours_the_inventory_tree_shape(tmp_path: Path) -> None:
    """Audit L: the shared-name sweep, proven for the Java suffix."""
    adapter = adapter_for("pmd")
    root = _repo(tmp_path / "shape", {
        "lib/Bundle.java": "class Bundle {}\n",
        "src/lib/Owned.java": "class Owned {}\n",
        "src/Library.java": "class Library {}\n",
    })

    named = " ".join(
        adapter.invocation(root, excludes=Exclusions((), ("lib",))).argv
    )
    assert "src/lib/Owned.java" in named, "first-party src/lib was dropped"
    assert "src/Library.java" in named, "prefix-matched past a boundary"
    assert f"{root}/lib/Bundle.java" not in named, "named a generated file"


def test_version_line_skips_ascii_art_and_names_the_version() -> None:
    """Audit M: P1 pins versions; a banner drawing is not a version."""
    banner = (
        "████        ████\n"
        "  ██    ██\n"
        "PMD 7.26.0\n"
    )
    assert version_line(banner) == "PMD 7.26.0"
    assert version_line("ruff 0.6.4") == "ruff 0.6.4"
    assert version_line("no digits here") == "no digits here"


def test_an_unmapped_rule_lands_on_a_declared_concept() -> None:
    """Audit L: the default concept must be one the adapter claims."""
    adapter = adapter_for("pmd")
    payload = json.dumps({
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "PMD"}},
            "results": [{
                "ruleId": "NPathComplexity",
                "message": {"text": "NPath complexity of 512"},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": "src/X.java"},
                    "region": {"startLine": 9},
                }}],
            }],
        }],
    })

    extraction = adapter.parse(ToolResult(
        slug="pmd", outcome=Outcome.RAN, stdout=payload, exit_code=4,
    ))

    assert len(extraction.findings) == 1
    assert extraction.findings[0].concept in set(adapter.concepts)


def test_truncated_raw_capture_is_stated_on_the_coverage_row() -> None:
    """Audit L: the same unserialized-field class that produced #76."""
    row = _coverage_entry(ToolCoverage(
        slug="pmd", outcome="ran", concepts=("complexity",), truncated=True,
    ))
    assert row["truncated"] is True
    plain = _coverage_entry(ToolCoverage(
        slug="pmd", outcome="ran", concepts=("complexity",),
    ))
    assert "truncated" not in plain
