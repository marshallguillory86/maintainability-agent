"""D53-D55: a broken configuration is refused by name, and the docs match.

Syntax was the only thing the reader checked. A file could parse, have
an object root, and still say `"thresholds": "nope"` — which merged
cleanly and surfaced much later as a raw `TypeError` from inside
scoring, naming neither the key nor the file. `ConfigUnreadable` existed
for exactly this reader and covered only unparseable bytes.

The shape check is derived from `DEFAULT_CONFIG` rather than written
out here, so a key added there is checked the day it is added. Unknown
keys stay permitted on purpose: this is a shape check, not a schema,
and refusing what it does not recognise would break every configuration
written against a newer version of this tool.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from maintainability_audit.config import DEFAULT_CONFIG, ConfigUnreadable, load_config

DOCS = Path(__file__).resolve().parents[1] / "docs"
SCHEMA = Path(__file__).resolve().parents[1] / "maintainability-agent.schema.json"


def _config_file(root: Path, payload: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "maintainability-agent.json"
    path.write_text(payload, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("payload", "key"),
    [
        ('{"thresholds": "nope"}', "thresholds"),
        ('{"hard_gates": []}', "hard_gates"),
        ('{"analyzers": 3}', "analyzers"),
        ('{"expected_files": {"a": 1}}', "expected_files"),
        ('{"risk_patterns": "x"}', "risk_patterns"),
    ],
)
def test_a_known_key_of_the_wrong_shape_is_refused_by_name(
    payload: str, key: str, tmp_path: Path,
) -> None:
    """Each of these produced a stack trace from somewhere else entirely."""
    path = _config_file(tmp_path / "repo", payload)
    with pytest.raises(ConfigUnreadable) as refused:
        load_config(str(path))
    message = str(refused.value)
    assert key in message, f"the refusal does not name the key: {message}"
    assert str(path) in message, f"the refusal does not name the file: {message}"


def test_every_container_key_in_the_defaults_is_covered() -> None:
    """The check is derived, so a key added tomorrow is checked tomorrow.

    Asserted rather than assumed: if `_shaped_like_the_defaults` ever
    stops reading `DEFAULT_CONFIG`, this is what notices.
    """
    containers = {
        key for key, value in DEFAULT_CONFIG.items()
        if isinstance(value, (dict, list))
    }
    assert containers, "DEFAULT_CONFIG has no container keys to check"
    from maintainability_audit import config as config_module

    source = Path(config_module.__file__).read_text(encoding="utf-8")
    assert "for key, default in DEFAULT_CONFIG.items()" in source, (
        "the shape check no longer derives its keys from DEFAULT_CONFIG, so "
        "a key added there would go unchecked"
    )


def test_an_unknown_key_is_still_accepted(tmp_path: Path) -> None:
    """Forward compatibility: a shape check is not a schema."""
    path = _config_file(tmp_path / "repo", '{"a_key_from_a_later_version": true}')
    assert load_config(str(path))["thresholds"], "a valid config stopped loading"


def test_a_valid_configuration_is_unaffected(tmp_path: Path) -> None:
    """The guard has to admit what it exists to protect."""
    payload: dict[str, Any] = {
        "version": 1,
        "thresholds": {"max_file_lines": 400},
        "hard_gates": {"require_readme": True},
        "expected_files": ["README.md", "docs/architecture.md"],
    }
    path = _config_file(tmp_path / "repo", json.dumps(payload))
    loaded = load_config(str(path))
    assert loaded["thresholds"]["max_file_lines"] == 400
    assert loaded["hard_gates"]["require_readme"] is True


@pytest.mark.parametrize(
    "entry", ["/etc/passwd", "../outside", "a/../../b", "/tmp/x"],
)
def test_expected_files_cannot_leave_the_repository(
    entry: str, tmp_path: Path,
) -> None:
    """D54: this reported whether a path on the host existed.

    `paths.history` was bounded by D20 and this was not, so a repository
    could ask the audit to probe the machine running it and read the
    answer out of the report.
    """
    path = _config_file(
        tmp_path / "repo", json.dumps({"expected_files": [entry]}))
    with pytest.raises(ConfigUnreadable) as refused:
        load_config(str(path))
    assert "expected_files" in str(refused.value)


def test_a_relative_expected_file_still_works(tmp_path: Path) -> None:
    """The common case is the whole point of the setting."""
    path = _config_file(
        tmp_path / "repo", json.dumps({"expected_files": ["README.md"]}))
    assert load_config(str(path))["expected_files"] == ["README.md"]


def test_no_document_offers_an_analyzer_selection_refuses() -> None:
    """D55: three tables still told the reader to install eslint.

    D39 made eslint unrunnable — it cannot start without executing the
    audited tree's flat config — and corrected the prose two paragraphs
    above the tables while leaving them offering it as a runtime need,
    an `npx` fetch, and a verified adapter.
    """
    from maintainability_audit._tool_adapters import ADAPTERS, adapter_for

    refused = {
        slug for slug in ADAPTERS
        if getattr(adapter_for(slug), "executes_audited_configuration", False)
    }
    assert refused, "no adapter declares that it executes the audited tree"

    pool = (DOCS / "analyzer-pool.md").read_text(encoding="utf-8")
    for slug in refused:
        for line in pool.splitlines():
            if slug not in line:
                continue
            offers_install = "brew install" in line or "npx" in line
            assert not offers_install or "not " + slug in line.lower(), (
                f"analyzer-pool.md offers an install for {slug}, which "
                f"selection refuses: {line.strip()[:110]}"
            )


def test_the_schema_does_not_call_a_live_setting_reserved() -> None:
    """D55: an IDE reader was told a switch the code reads does nothing."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def descriptions(node: Any) -> list[str]:
        found: list[str] = []
        if isinstance(node, dict):
            if isinstance(node.get("description"), str):
                found.append(node["description"])
            for value in node.values():
                found += descriptions(value)
        elif isinstance(node, list):
            for value in node:
                found += descriptions(value)
        return found

    from maintainability_audit import _first_run

    source = Path(_first_run.__file__).read_text(encoding="utf-8")
    assert "prompt_when_interactive" in source, (
        "the setting is gone from _first_run; re-read the schema description"
    )
    reserved = [
        text for text in descriptions(schema)
        if "reserved" in text.lower() and "not read" in text.lower()
    ]
    assert not reserved, (
        f"the schema calls a setting reserved and unread: {reserved}"
    )
