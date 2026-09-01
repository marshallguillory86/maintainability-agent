"""Java range detection must be wired completely before it is enabled."""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path

from _ast_reading import (
    ROOT,
    declaration_suffixes,
    default_include_extensions,
    scanner_registry,
)


def test_java_is_declaration_enabled() -> None:
    assert ".java" in declaration_suffixes()


def test_java_is_in_the_default_include_extensions() -> None:
    assert ".java" in default_include_extensions()


def test_java_dispatch_uses_only_the_java_range_detector() -> None:
    """Read from `declarations.SCANNERS`, which replaced the `if` chain in
    1.1.0 — a branch per language does not survive four more languages."""
    assert scanner_registry().get(".java") == "java_declaration_ranges"


def test_project_config_excludes_the_java_range_fixtures() -> None:
    config = json.loads((ROOT / "maintainability-agent.json").read_text(encoding="utf-8"))
    patterns = config["paths"]["exclude_patterns"]
    fixture = "tests/fixtures/java/Widget.java"

    def matches(pattern: str) -> bool:
        normalized = pattern.replace("\\", "/")
        return (
            fnmatch.fnmatch(fixture, normalized)
            or fnmatch.fnmatch(Path(fixture).name, normalized)
            or (normalized.endswith("/") and fixture.startswith(normalized))
        )

    assert any(matches(pattern) for pattern in patterns)


def test_language_support_documents_java_measurement() -> None:
    text = (ROOT / "docs" / "language-support.md").read_text(encoding="utf-8")

    assert re.search(
        r"^\|\s*Java\s*\([^\n|]*\.java[^\n|]*\)\s*\|",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    assert re.search(
        r"\.java[^.\n]*(?:never\s+(?:parsed|handed)|not\s+parsed)",
        text,
        flags=re.IGNORECASE,
    ) is None
