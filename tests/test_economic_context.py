"""ADR 004's v1: optional economic scenarios stay outside the score."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from maintainability_audit.cli import main
from maintainability_audit.config import CONFIG_FILENAME, load_config
from maintainability_audit.report import build_report

LABOR_ENV = (
    "MAINTAINABILITY_LABOR_LOW",
    "MAINTAINABILITY_LABOR_BASE",
    "MAINTAINABILITY_LABOR_HIGH",
    "MAINTAINABILITY_CURRENCY",
    "MAINTAINABILITY_HORIZON_MONTHS",
)
LABOR = {
    "version": 1,
    "currency": "USD",
    "planning_horizon_months": 12,
    "loaded_engineering_cost_per_hour": {"low": 90, "base": 140, "high": 210},
}


@pytest.fixture(autouse=True)
def _no_ambient_labor(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in LABOR_ENV:
        monkeypatch.delenv(name, raising=False)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _commit(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(
        root,
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test",
        "commit",
        "-qm",
        message,
    )


def _long_function(name: str, branches: int) -> str:
    decisions = "".join(
        f"    if value == {number}:\n        return {number}\n"
        for number in range(branches)
    )
    return f"def {name}(value):\n{decisions}    return -1\n"


def _repo(root: Path, *, two_findings: bool = False) -> Path:
    root.mkdir()
    _git(root, "init", "-q")
    (root / "README.md").write_text("# Economic context fixture\n", encoding="utf-8")
    source = root / "src"
    source.mkdir()
    for index in range(40):
        (source / f"module_{index}.py").write_text(
            f"def work_{index}(value):\n    return value + {index}\n",
            encoding="utf-8",
        )
    if two_findings:
        (source / "hot.py").write_text(
            _long_function("frequently_changed", branches=16), encoding="utf-8"
        )
        (source / "cold.py").write_text(
            _long_function("larger_but_stable", branches=45), encoding="utf-8"
        )
    _commit(root, "initial tree")
    if two_findings:
        hot = source / "hot.py"
        for number in range(3):
            hot.write_text(
                hot.read_text(encoding="utf-8") + f"# routine change {number}\n",
                encoding="utf-8",
            )
            _commit(root, f"touch hot path {number}")
    return root


def _config(economic_context: dict | None = None) -> dict:
    config = load_config(None)
    if economic_context is not None:
        config["economic_context"] = economic_context
    return config


def _assert_scenario_shape(
    impact: object, *, currency: str, horizon: int,
) -> dict:
    assert isinstance(impact, dict) and impact, "configured labor produced no scenario"
    low, base, high = (impact.get(name) for name in ("low", "base", "high"))
    assert all(isinstance(value, int | float) for value in (low, base, high))
    assert low <= base <= high
    assert impact.get("currency") == currency
    assert impact.get("planning_horizon_months") == horizon
    assumptions = impact.get("assumptions")
    assert isinstance(assumptions, list | dict) and assumptions, (
        "the scenario does not list the assumptions that produced its range"
    )
    language = json.dumps(impact, sort_keys=True).lower()
    assert "labor" in language or "loaded_engineering_cost_per_hour" in language
    forbidden = re.search(
        r"\b(?:prediction|savings?|roi)\b|avoided[ _-]?cost|return[ _-]on[ _-]investment",
        language,
    )
    assert forbidden is None, f"scenario claims an unvalidated outcome: {forbidden.group(0)!r}"
    return impact


def test_absent_context_keeps_the_standard_report_and_order(tmp_path: Path) -> None:
    root = _repo(tmp_path / "absent", two_findings=True)
    plain = build_report(root, _config())
    contextual = build_report(root, _config(LABOR))

    assert not plain.get("economic_impact")
    assert plain["score"] == contextual["score"]
    assert plain["score"]["verified_grade"] == contextual["score"]["verified_grade"]

    band_order = {"quick-win": 0, "major-project": 1, "fill-in": 2, "reconsider": 3}
    standard_keys = [
        (
            band_order[item["band"]],
            -item["class_delta"],
            -item["severity"],
            item["path"],
        )
        for item in plain["work_order"]
    ]
    assert standard_keys == sorted(standard_keys), (
        "without economic context the work order left its risk-by-effort order"
    )


def test_configured_labor_produces_an_honestly_labeled_range(tmp_path: Path) -> None:
    report = build_report(_repo(tmp_path / "configured", two_findings=True), _config(LABOR))

    _assert_scenario_shape(
        report.get("economic_impact"), currency="USD", horizon=12
    )


def test_environment_labor_produces_a_one_run_scenario(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAINTAINABILITY_LABOR_LOW", "80")
    monkeypatch.setenv("MAINTAINABILITY_LABOR_BASE", "120")
    monkeypatch.setenv("MAINTAINABILITY_LABOR_HIGH", "180")
    monkeypatch.setenv("MAINTAINABILITY_CURRENCY", "CAD")
    monkeypatch.setenv("MAINTAINABILITY_HORIZON_MONTHS", "18")

    report = build_report(_repo(tmp_path / "environment", two_findings=True), _config())

    _assert_scenario_shape(
        report.get("economic_impact"), currency="CAD", horizon=18
    )


def test_labor_numbers_cannot_change_the_score_or_verified_grade(tmp_path: Path) -> None:
    root = _repo(tmp_path / "score-boundary", two_findings=True)
    low = {**LABOR, "loaded_engineering_cost_per_hour": {"low": 20, "base": 30, "high": 40}}
    high = {
        **LABOR,
        "loaded_engineering_cost_per_hour": {"low": 200, "base": 300, "high": 400},
    }

    low_report = build_report(root, _config(low))
    high_report = build_report(root, _config(high))

    for field in ("maintainability_estimate", "verified_grade"):
        assert low_report["score"][field] == high_report["score"][field], field


def test_hotter_finding_leads_without_erasing_standard_order_evidence(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path / "exposure", two_findings=True)
    plain = build_report(root, _config())
    contextual = build_report(root, _config(LABOR))
    hotspots = {item["file"] for item in contextual["history"]["hotspots"]}

    assert "src/hot.py" in hotspots, "fixture did not establish repository-derived exposure"
    plain_paths = [item["path"] for item in plain["work_order"]]
    contextual_paths = [item["path"] for item in contextual["work_order"]]
    assert plain_paths.index("src/cold.py") < plain_paths.index("src/hot.py"), (
        "fixture must put the structurally worse but stable item first today"
    )
    assert contextual_paths.index("src/hot.py") < contextual_paths.index("src/cold.py"), (
        "economic priority ignored the higher-exposure hotspot"
    )
    for item in contextual["work_order"]:
        assert {"severity", "risk", "effort", "band", "class_delta"} <= set(item), (
            "economic ordering erased the standard severity/order evidence"
        )


def _tty(monkeypatch: pytest.MonkeyPatch, answer: bool) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: answer, raising=False)


def _silence_outputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("maintainability_audit.cli.write_outputs", lambda *_args: None)


def test_tty_without_labor_asks_once_and_persists_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path / "tty")
    _tty(monkeypatch, True)
    _silence_outputs(monkeypatch)
    asked: list[str] = []

    def answer(prompt: str = "") -> str:
        asked.append(prompt)
        lowered = prompt.lower()
        if "labor" in lowered or "cost" in lowered:
            if "low" in lowered:
                return "90"
            if "base" in lowered:
                return "140"
            if "high" in lowered:
                return "210"
        return ""

    monkeypatch.setattr("builtins.input", answer)

    assert main(["--root", str(root), "--format", "markdown"]) == 0

    labor_prompts = [prompt for prompt in asked if re.search(r"labor|cost", prompt, re.I)]
    assert labor_prompts, f"TTY first run never asked for the labor range: {asked}"
    written = json.loads((root / CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert written.get("economic_context", {}).get(
        "loaded_engineering_cost_per_hour"
    ) == {"low": 90, "base": 140, "high": 210}


def test_non_tty_without_labor_never_asks_or_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path / "ci")
    _tty(monkeypatch, False)
    _silence_outputs(monkeypatch)

    def forbidden(prompt: str = "") -> str:
        raise AssertionError(f"non-TTY audit called input(): {prompt!r}")

    monkeypatch.setattr("builtins.input", forbidden)

    assert main(["--root", str(root), "--format", "markdown"]) == 0
    assert not (root / CONFIG_FILENAME).exists()


def test_prompt_when_interactive_false_suppresses_the_economic_ask(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path / "silent-tty")
    config_path = root / CONFIG_FILENAME
    config_path.write_text(
        json.dumps({"version": 1, "analyzers": {"prompt_when_interactive": False}}),
        encoding="utf-8",
    )
    _tty(monkeypatch, True)
    _silence_outputs(monkeypatch)

    def forbidden(prompt: str = "") -> str:
        raise AssertionError(f"disabled interactive prompting called input(): {prompt!r}")

    monkeypatch.setattr("builtins.input", forbidden)

    assert main(
        ["--root", str(root), "--config", str(config_path), "--format", "markdown"]
    ) == 0
