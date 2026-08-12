from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "0.6.1"

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
            # Third-party code the repo did not write. Auditing it
            # measures someone else's decisions and, worse, calibrated
            # references drawn from a corpus containing it describe
            # vendored bundles rather than maintained source. lodash's
            # entry was 41% vendored.
            "vendor/",
            "vendored/",
            "third_party/",
            "third-party/",
            "*.min.js",
            "*.min.css",
            "*.bundle.js",
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
    # Hard gates block CI, so every one of them is opt-in. Three used to
    # fire automatically from threshold breaches, which meant a default
    # run failed the gate on every real codebase measured -- 33 to 5,325
    # duplicate blocks against a max of 20, plus file and function
    # breaches. A gate that always fails is not a gate; it is noise that
    # trains people to pass --fail-on-gate and ignore the result.
    "hard_gates": {
        "require_test_command": False,
        "require_readme": True,
        "require_clean_worktree": False,
        # These three previously had no switch and fired whenever a
        # threshold was breached. Default off: a repo opts in to what
        # should block its CI.
        "fail_on_file_failures": False,
        "fail_on_function_failures": False,
        "fail_on_duplicate_blocks": False,
    },
    "expected_files": ["README.md"],
    "expected_commands": {"test": [], "lint": []},
    # Shipped patterns are bug *classes*, each one earned by a defect that
    # actually happened rather than invented from a checklist. The first
    # three come from this project's own failures, which is the only
    # evidence any of them has and is better than none.
    "risk_patterns": [
        {
            "name": "debt-marker",
            "pattern": r"\b(TODO|FIXME|HACK)\b",
            "extensions": [".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".md"],
        },
        {
            # Absence read as a value. `counts.get("x", 0)` cannot
            # distinguish "measured none" from "never measured", and the
            # zero then flows into a rate as though it were evidence.
            #
            # This project shipped that defect at least four times: a
            # repository with one function scored 5.0/A+ because six
            # detectors found nothing; analyzer coverage derived from
            # emitted output made a clean scan read as unexamined; a
            # metric adapter returning no measurements reported success.
            # Every instance was written by someone who knew the rule.
            #
            # Deliberately narrow. `counts.get(k, 0) + 1` is an accumulator
            # and not this defect, and a pattern that flags it produces the
            # nit loop this tool exists to avoid. Matching only a default
            # that is *returned or assigned* dropped the finding count on
            # this repository from 22 to a handful, nearly all real.
            #
            # Still a review prompt rather than a defect assertion, and one
            # of the survivors on this repository is a false positive: a
            # zero used immediately as a skip sentinel. That is the
            # intended precision profile -- the finding says "look here",
            # and looking is cheap.
            "name": "absence-as-zero",
            "pattern": r"(?:return|=)\s*[\w.\[\]\"\']+\.get\([^)]+,\s*0\s*\)\s*$",
            "extensions": [".py"],
        },
        {
            # An assertion that cannot fail. A test built against a path
            # that did not exist compared two identical empty results and
            # passed, which is how a gap survived the test written to
            # catch it. A test that cannot fail is worse than no test: it
            # buys confidence it has not earned.
            "name": "vacuous-assertion",
            "pattern": r"assert\s+(True|1)\s*(?:,|$)|assert\s+(\w+)\s*==\s*\2\b",
            "extensions": [".py"],
        },
        {
            # Output cut without saying so. A reader who believes a
            # truncated list is complete draws conclusions from a
            # fragment. Slicing is fine; silent slicing is not.
            #
            # Only a literal cut on a *returned* collection. Slicing into a
            # local, or with a named limit, is ordinary; silently returning
            # a shortened result to a caller who cannot tell is not.
            "name": "silent-truncation",
            "pattern": r"return\s+[\w.\[\]()]+\[:\s*\d{2,}\s*\]\s*$",
            "extensions": [".py"],
        },
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


CONFIG_FILENAME = "maintainability-agent.json"


def discovered_config(root: Path) -> str | None:
    """The repository's own config, when a caller did not name one.

    A tool that sits next to its configuration and silently ignores it is
    a trap: this project audited itself for a session against built-in
    defaults rather than its own exclusions, and the difference was 422
    findings versus 162 -- most of the excess from a generated data file
    the config had excluded all along.

    Lives here rather than in `cli` because every entry point needs it.
    Fixed in the CLI first, and the MCP server then returned 405 findings
    where the CLI returned 162 on the same repository, which is what a
    fix living in one caller looks like from the outside.
    """
    candidate = root / CONFIG_FILENAME
    return str(candidate) if candidate.is_file() else None


def load_config(path: str | None) -> dict[str, Any]:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if not path:
        return config
    user_config = json.loads(Path(path).read_text(encoding="utf-8"))
    deep_update(config, user_config)
    return config
