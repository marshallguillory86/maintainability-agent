from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "0.6.0"

PROJECT_URL = "https://github.com/marshallguillory86/maintainability-agent"

# Concern -> competing packages. Empty means "use the shipped list in
# ``idioms.DEFAULT_IDIOM_GROUPS``"; set it to override that list entirely
# with groups meaningful to this repo.
DEFAULT_IDIOM_GROUPS: dict[str, list[str]] = {}

DEFAULT_CONFIG: dict[str, Any] = {
    "paths": {
        "include_extensions": [".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".md"],
        "exclude_patterns": [
            ".git/",
            "node_modules/",
            ".venv/",
            "venv/",
            "dist/",
            "build/",
            "coverage/",
            "__pycache__/",
            # Schema migrations are append-only history. Refactoring one
            # rewrites the past, so a long-but-branchless migration is
            # correct code, not a maintainability finding.
            "migrations/",
            "maintainability-baseline.json",
            "maintainability-report.md",
            "maintainability-remediation-prompt.md",
            "maintainability-pr-comment.md",
            "maintainability.sarif",
        ],
    },
    "thresholds": {
        "max_file_lines": 800,
        "warn_file_lines": 400,
        "max_function_lines": 80,
        "warn_function_lines": 50,
        # Classes are containers, graded on length alone — see
        # ``metrics.class_status``.
        "max_class_lines": 300,
        "warn_class_lines": 200,
        "max_complexity": 15,
        "warn_complexity": 10,
        # Nesting-weighted reading cost. Fitted against 21,300 declarations
        # in the reference corpus: 15 sits near its 94th percentile and 25
        # near its 97th, so these flag the genuinely hard-to-read tail
        # rather than ordinary branching. See ``_cognitive``.
        "max_cognitive_complexity": 25,
        "warn_cognitive_complexity": 15,
        "max_duplicate_blocks": 20,
        "duplicate_block_lines": 8,
    },
    "hard_gates": {
        "require_test_command": False,
        "require_readme": True,
        "require_clean_worktree": False,
    },
    "expected_files": ["README.md"],
    "expected_commands": {"test": [], "lint": []},
    "risk_patterns": [
        {
            "name": "debt-marker",
            "pattern": r"\b(TODO|FIXME|HACK)\b",
            "extensions": [".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".md"],
        }
    ],
    "instruction_pack": {
        "project_name": "this repository",
        "strictness": "high",
        "test_policy": "tests for meaningful behavior changes",
        "architecture_notes": [],
    },
}


def deep_update(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value


def load_config(path: str | None) -> dict[str, Any]:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if not path:
        return config
    user_config = json.loads(Path(path).read_text(encoding="utf-8"))
    deep_update(config, user_config)
    return config
