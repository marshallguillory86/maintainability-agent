from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "0.3.0"

PROJECT_URL = "https://github.com/marshallguillory86/maintainability-agent"

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
        "max_complexity": 15,
        "warn_complexity": 10,
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
