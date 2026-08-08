#!/usr/bin/env python3
"""Choose the reference corpus mechanically, so it is not one person's taste.

The first corpus was fourteen repositories I picked because I knew them.
That is selection bias sitting underneath a scale used to grade everyone
else, so the list is now produced by a query anybody can re-run and
check.

Three criteria, each doing real work:

- **`created:<2021-01-01`.** The corpus is the *human-written* baseline
  against which AI-assisted code is compared. Sorting today's most-starred
  repositories returns langflow, browser-use and similar — projects begun
  well into the LLM era, whose authorship is exactly the variable under
  test. Contaminating the baseline with them would quietly answer the
  question before measuring it.
- **`pushed:>` recent.** Still maintained. An abandoned repository
  describes how code was written years ago, not what maintained code
  looks like.
- **`stars:>3000`.** Widely read and depended upon, so "well maintained"
  is a claim others have tested rather than one this project asserts.

Star-sorted results are full of curated lists — `awesome-python`,
`free-programming-books`, `developer-roadmap`. `_LIST_MARKERS` skips the
obvious ones to avoid cloning hundreds of megabytes of Markdown, but the
real filter is `verify.py`, which keeps a repository only if it actually
contains code.

Usage:

    python3 tools/calibration/select_corpus.py --per-language 16 > candidates.json

(Named ``select_corpus`` rather than ``select`` because a module named
``select.py`` shadows the stdlib ``select``, which ``subprocess`` imports
through ``selectors`` — the script cannot import its own dependencies.)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

LANGUAGES = ["python", "typescript", "javascript"]

# Substrings that mark a repository as documentation, curriculum or a
# link collection rather than a codebase. Deliberately conservative: a
# false skip costs one candidate, and `verify.py` catches what slips
# through.
_LIST_MARKERS = (
    "awesome", "book", "roadmap", "handbook", "primer", "tutorial", "guide",
    "beginner", "interview", "algorithms", "cheatsheet", "checklist", "curriculum",
    "public-apis", "free-programming", "30-seconds", "hellogithub", "iptv",
    "coding-", "learn", "examples", "demo", "course", "notes", "resources",
    # "concepts" was added after `33-js-concepts` cleared verification on a
    # technicality: an index.js plus thirty concept-demo test files is
    # enough declarations to look like a codebase. The exclusion is on what
    # the repository *is* — a teaching repo, already covered by "tutorial",
    # "learn" and "examples" — not on how it measured. Note the distinction
    # matters: filtering the corpus by its own results would manufacture
    # whatever reference the filter was aimed at.
    "concepts",
)

# GitHub reports full repository size including history; a shallow clone
# is far smaller. This only excludes the genuine monsters, because
# excluding large repositories would reintroduce the size bias that made
# the previous scoring model grade Django an F.
MAX_SIZE_KB = 800_000


def search(language: str, per_language: int, created_before: str, pushed_after: str, min_stars: int) -> list[dict]:
    query = (
        f"language:{language} stars:>{min_stars} "
        f"created:<{created_before} pushed:>{pushed_after}"
    )
    # Over-fetch: the name filter and the size cap both discard candidates.
    result = subprocess.run(
        [
            "gh", "api", "-X", "GET", "search/repositories",
            "--raw-field", f"q={query}",
            "--raw-field", "sort=stars",
            "--raw-field", "per_page=100",
        ],
        capture_output=True, text=True, check=True,
    )
    items = json.loads(result.stdout).get("items", [])
    picked = []
    for item in items:
        name = item["full_name"].lower()
        if any(marker in name for marker in _LIST_MARKERS):
            continue
        if item["size"] > MAX_SIZE_KB:
            continue
        picked.append(
            {
                "name": item["name"],
                "full_name": item["full_name"],
                "url": item["clone_url"],
                "stars": item["stargazers_count"],
                "created": item["created_at"][:10],
                "language": language,
                "license": (item.get("license") or {}).get("spdx_id"),
            }
        )
        if len(picked) >= per_language:
            break
    return picked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-language", type=int, default=16)
    parser.add_argument("--created-before", default="2021-01-01")
    parser.add_argument("--pushed-after", default="2026-01-01")
    parser.add_argument("--min-stars", type=int, default=3000)
    args = parser.parse_args()

    candidates: list[dict] = []
    for language in LANGUAGES:
        found = search(language, args.per_language, args.created_before, args.pushed_after, args.min_stars)
        print(f"{language}: {len(found)} candidates", file=sys.stderr)
        candidates.extend(found)

    json.dump(
        {
            "query": {
                "languages": LANGUAGES,
                "created_before": args.created_before,
                "pushed_after": args.pushed_after,
                "min_stars": args.min_stars,
                "max_size_kb": MAX_SIZE_KB,
            },
            "candidates": candidates,
        },
        sys.stdout,
        indent=1,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
