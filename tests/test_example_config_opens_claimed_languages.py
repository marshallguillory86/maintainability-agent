"""The published starter config opens every language the shipped default opens."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _ast_reading import declaration_suffixes, default_include_extensions
from maintainability_audit.config import DEFAULT_CONFIG


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "maintainability-audit.example.json"


def _assert_opens_shipped_default(observed: set[str], expected: set[str]) -> None:
    assert observed == expected, (
        "maintainability-audit.example.json opens a different language population "
        f"than the shipped default (missing={sorted(expected - observed)}, "
        f"extra={sorted(observed - expected)})"
    )


def test_example_config_opens_the_source_derived_default_language_population() -> None:
    """D162: the copyable config must reach every default-opened language."""
    declared = declaration_suffixes()
    shipped_default = default_include_extensions()
    assert declared, "DECLARATION_SUFFIXES from production source is empty"
    assert declared <= shipped_default, (
        "a declared language is absent from _config_defaults.py: "
        f"{sorted(declared - shipped_default)}"
    )
    assert set(DEFAULT_CONFIG["paths"]["include_extensions"]) == shipped_default, (
        "DEFAULT_CONFIG no longer matches its source declaration"
    )

    example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    _assert_opens_shipped_default(
        set(example["paths"]["include_extensions"]), shipped_default)


def test_the_example_language_oracle_rejects_an_unnamed_omission() -> None:
    """A source-derived member removed from the population makes D162 fail."""
    shipped_default = default_include_extensions()
    declared = declaration_suffixes()
    removable = next(suffix for suffix in sorted(declared) if suffix in shipped_default)
    mutated = shipped_default - {removable}

    with pytest.raises(AssertionError):
        _assert_opens_shipped_default(mutated, shipped_default)
