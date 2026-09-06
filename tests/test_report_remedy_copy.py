"""Post-D1 report remedies follow the pool state instead of prescribing a flag."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from maintainability_audit.config import discovered_config, load_config
from maintainability_audit.prompts import render_agent_instructions, render_ai_prompt
from maintainability_audit.renderers import render_html, render_markdown, render_pr_comment
from maintainability_audit.report import build_report


def _config(run: bool) -> dict:
    return {
        "version": 1,
        "analyzers": {
            "run": run,
            "concerns": ["types"],
            "depth": "baseline",
            "license_policy": "permissive",
            "acquire_tools": False,
            # One shipped adapter gives the configured-on report a real
            # coverage outcome without depending on a network or installation.
            "allow_tools": ["lizard"],
            "deny_tools": [],
            "deny_license_classes": [],
            "deny_concerns": [],
            "timeout_seconds": 5,
        },
        "paths": {"include_extensions": [".kt"]},
    }


def _repo(tmp_path: Path, config: dict | None) -> Path:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    for number in range(40):
        (root / "src" / f"thing{number}.kt").write_text(
            "package fixture\n\n"
            f"func Compute{number}(value int) int {{\n"
            "\tif value > 0 { return value }\n"
            "\treturn -value\n"
            "}\n",
            encoding="utf-8",
        )
    if config is not None:
        (root / "maintainability-agent.json").write_text(
            json.dumps(config), encoding="utf-8",
        )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git", "-C", str(root), "-c", "user.email=t@t",
            "-c", "user.name=t", "commit", "-qm", "fixture",
        ],
        check=True,
    )
    return root


def _build_case(tmp_path: Path, config: dict | None) -> dict:
    root = _repo(tmp_path, config)
    if config is None:
        loaded = load_config(None)
        loaded["paths"]["include_extensions"].append(".kt")
    else:
        loaded = load_config(discovered_config(root))
    report = build_report(root, loaded)
    assert report["summary"]["undetected_declaration_files"] == 40
    assert report["score"]["maintainability_estimate"] is None
    return report


@pytest.fixture
def remedy_reports(tmp_path: Path, real_population_floors: dict) -> dict[str, dict]:
    """The same unparsed population under each D1 configuration state."""
    return {
        "configured-on": _build_case(tmp_path / "on", _config(True)),
        "configured-off": _build_case(tmp_path / "off", _config(False)),
        "unconfigured": _build_case(tmp_path / "unconfigured", None),
    }


def _section(markdown: str, heading: str) -> str:
    start = markdown.index(f"## {heading}")
    remainder = markdown[start:]
    next_heading = remainder.find("\n## ", 1)
    return remainder if next_heading < 0 else remainder[:next_heading]


def _remedy_sites(report: dict) -> tuple[str, ...]:
    """Every user-facing remedy must resolve pool state from one report fact."""
    markdown = render_markdown(report)
    evidence = next(
        line for line in markdown.splitlines()
        if line.startswith("| Evidence |")
    )
    unparsed = _section(markdown, "Read, But Not Parsed for Declarations")
    action = [paragraph for paragraph in unparsed.split("\n\n") if paragraph.strip()][-1]
    return (
        evidence,
        action,
        render_ai_prompt(report),
        render_pr_comment(report),
        render_html(report, []),
        render_agent_instructions(report),
    )


def _activation_terms(text: str) -> frozenset[str]:
    return frozenset(
        term for term in ("--analyzers", "analyzers.run")
        if term in text
    )


def _remedy_kind(text: str) -> str:
    if _activation_terms(text):
        return "enable-pool"
    lowered = text.lower()
    if "parser" in lowered:
        return "parser"
    if "environment work order" in lowered or "install" in lowered:
        return "install-tool"
    return "unnamed"


def test_a_configured_pool_is_not_prescribed_an_analyzer_flag(
    remedy_reports: dict[str, dict],
) -> None:
    report = remedy_reports["configured-on"]
    assert report["analyzer_coverage"] is not None

    for site in _remedy_sites(report):
        assert not _activation_terms(site), (
            "the configured analyzer pool already ran; its remedy must name "
            "the missing parser or environment work, not prescribe running it again"
        )
        assert _remedy_kind(site) in {"parser", "install-tool"}


@pytest.mark.parametrize("case", ["configured-off", "unconfigured"])
def test_analyzer_activation_is_a_remedy_only_while_the_pool_is_off(
    remedy_reports: dict[str, dict],
    case: str,
) -> None:
    report = remedy_reports[case]
    assert report["analyzer_coverage"] is None

    for site in _remedy_sites(report):
        assert _activation_terms(site)


def test_withheld_evidence_and_unparsed_source_use_one_remedy_dialect(
    remedy_reports: dict[str, dict],
) -> None:
    for case, report in remedy_reports.items():
        sites = _remedy_sites(report)
        assert len({_activation_terms(site) for site in sites}) == 1, case
        assert len({_remedy_kind(site) for site in sites}) == 1, case
