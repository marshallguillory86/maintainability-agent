"""The security run's time limit is configured, bounded, and long enough.

The delegate ran under a hard-coded 300 seconds, set when the pillar
arrived (D177). A full secure-code-agent run on this repository now takes
about 8½ minutes, so both audits of it timed out and reported the pillar
unmeasured, while the same run outside took 8½ minutes and came back clean
(gate pass, 5.00). The suite had the same defect with a fixed 120 seconds
until `test_execution.timeout_seconds` made it configurable.

The limit is now `security.timeout_seconds` in `maintainability-agent.json`,
under the same clamp as `analyzers.timeout_seconds`: a repository naming a
number is naming how long this host waits, so it is held to 1 second..1 hour
and anything that is not an integer falls back to the default. The default
is 900 seconds, about twice the time measured on this repository.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from maintainability_audit import report as report_module
from maintainability_audit._security_delegate import DelegateRun
from maintainability_audit.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def _limit_used(tmp_path: Path, monkeypatch, security: dict | None) -> int:
    (tmp_path / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    seen: dict = {}

    def capture(root, **kwargs):
        seen.update(kwargs)
        return DelegateRun(None, "not run by the test suite")

    monkeypatch.setattr(report_module, "run_security_delegate", capture)
    config = load_config(None)
    if security is not None:
        config["security"] = security
    report_module.build_report(tmp_path, config)
    return seen["timeout_seconds"]


def test_the_default_limit_outlasts_a_full_run(tmp_path: Path, monkeypatch) -> None:
    assert _limit_used(tmp_path, monkeypatch, None) == 900


@pytest.mark.parametrize(("configured", "used"), [(1500, 1500), (10**9, 3600), (0, 1), ("x", 900)])
def test_a_configured_limit_is_used_and_bounded(tmp_path: Path, monkeypatch, configured, used) -> None:
    assert _limit_used(tmp_path, monkeypatch, {"timeout_seconds": configured}) == used


def test_the_published_schema_accepts_it() -> None:
    schema = json.loads((ROOT / "maintainability-agent.schema.json").read_text(encoding="utf-8"))
    config = {"version": 1, "security": {"timeout_seconds": 1200}}

    jsonschema.validate(config, schema)
