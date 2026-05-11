"""Schema-fidelity guard.

Asserts that the JSON Schema shipped at the repo root validates both
the example config (`maintainability-audit.example.json`) and the
self-audit config (`maintainability-agent.json`). Without this, a code
change that adds a new config key won't surface a schema drift until
users hit IDE warnings on their own configs.

`jsonschema` is an optional test-only dep; if not installed (e.g. an
agent running with PYTEST_DISABLE_PLUGIN_AUTOLOAD that didn't install
extras) the tests SKIP cleanly rather than fail.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "maintainability-agent.schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_config(filename: str) -> dict:
    return json.loads((REPO_ROOT / filename).read_text(encoding="utf-8"))


def test_example_config_validates_against_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(_load_config("maintainability-audit.example.json"), _load_schema())


def test_self_audit_config_validates_against_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(_load_config("maintainability-agent.json"), _load_schema())


def test_schema_declares_2020_12_dialect() -> None:
    """Config-schema doc claims draft 2020-12. Pin it so a future
    schema rewrite that drops the $schema or changes dialects has
    to update the doc + this test together."""
    schema = _load_schema()
    assert schema.get("$schema", "").endswith("/draft/2020-12/schema")
