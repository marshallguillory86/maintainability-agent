"""The shipped default configuration: what this tool measures out of the box.

Split out of ``config.py`` in 1.1.0. That module had two jobs — carrying
the defaults and loading/validating a user's file — and had sat at its
500-line budget, so each new language spent its budget arguing with the
gate instead of describing itself. The data lives here; ``config`` keeps
the behaviour and re-exports these names, so every existing
``from .config import DEFAULT_CONFIG`` is unchanged.

Two lists in this file move with every language the project adds:
``paths.include_extensions`` (what is opened) and the ``extensions`` of
each risk pattern (where that pattern is looked for). ``include_extensions``
is bound to ``declarations.DECLARATION_SUFFIXES`` in both directions by
``test_claimed_languages`` — a suffix is opened as source only when
something parses it, and parsed only when the page says so.
"""
from __future__ import annotations

from typing import Any

# Concern -> competing packages. Empty means "use the shipped list in
# ``idioms.DEFAULT_IDIOM_GROUPS``"; set it to override that list entirely
# with groups meaningful to this repo.
DEFAULT_IDIOM_GROUPS: dict[str, list[str]] = {}

DEFAULT_CONFIG: dict[str, Any] = {
    # Whether the external analyzer pool executes. False here covers
    # only the no-config-file path: unconfigured programmatic callers
    # keep the built-in fallback until D2's first-run setup writes a
    # config. `load_config` flips the default to True the moment a real
    # file loads — a repository that wrote a config chose the product,
    # and ADR 006 says the pool is the product's evidence source.
    "analyzers": {"run": False},
    "paths": {
        # `.c`/`.h` joined in 1.1.0 with the C scanner, the C++ set in 1.2.0,
        # `.cs` in 1.3.0 and free-form Fortran in 1.4.0. A source suffix is
        # listed here only when something parses it, and parsed only when
        # it is listed: opening a language nothing reads produces the P7
        # population nobody measured, and parsing one the default config
        # never opens is a capability no user can reach. Both directions
        # are enforced — `test_every_scanned_source_suffix_can_be_read_by
        # _something` and `test_the_parsed_languages_are_exactly_the
        # _documented_languages`.
        "include_extensions": [
            ".py", ".java", ".c", ".h",
            ".cpp", ".hpp", ".cc", ".cxx", ".hh",
            ".cs",
            ".swift",
            ".go",
            ".rs",
            ".cbl", ".cob", ".cpy", ".CBL", ".COB", ".CPY",
            ".f90", ".f95", ".f03", ".f08",
            ".F90", ".F95", ".F03", ".F08", ".pf",
            ".f", ".for", ".ftn", ".F", ".FOR", ".FTN",
            ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
            ".html", ".css", ".md",
        ],
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
            # A debt marker is a debt marker in every language, and this
            # list was the web stack only. Every compiled language this
            # project claims — Java since 1.0, C since 1.1, C++, C#, and
            # Fortran — could carry `TODO` and `FIXME` in comments that
            # nothing looked at, so the one risk pattern that ships by
            # default was silent on exactly the trees where the debt is
            # oldest.
            "name": "debt-marker",
            "pattern": r"\b(TODO|FIXME|HACK)\b",
            "extensions": [".py", ".java", ".c", ".h",
                           ".cpp", ".hpp", ".cc", ".cxx", ".hh", ".cs",
                           ".f90", ".f95", ".f03", ".f08",
                           ".F90", ".F95", ".F03", ".F08", ".pf",
                           ".f", ".for", ".ftn", ".F", ".FOR", ".FTN",
                           ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
                           ".html", ".css", ".md"],
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
