#!/usr/bin/env python3
"""Do fixes stay narrow? Measured per cohort, tested before claimed.

"Broad rewrites for narrow bugs" is one of the failure modes commonly
attributed to AI-assisted code. Unlike everything else this tool
measures it is a *process* property — it lives in the diffs, not in any
snapshot — which also makes it directly measurable: find the commits
that say they are fixes, and measure how much they touch.

Per repository, over non-merge commits whose subject matches
``_FIX_PATTERN``:

- ``median_files_per_fix`` — how many files the typical fix touches
- ``median_lines_per_fix`` — how many lines it adds plus removes
- ``broad_fix_share`` — the share of fixes touching more than
  ``BROAD_FILES`` files

Repositories with fewer than ``MIN_FIX_COMMITS`` fixes are skipped: a
median of three data points is an anecdote wearing a number.

The cohort comparison reuses the tie-corrected Mann-Whitney from
``measure_cohorts`` and reports the size correlation beside every
p-value, because the near-duplication study showed how a cohort size
imbalance manufactures significance. The discipline is the same as
there: this script produces the evidence; nobody writes the sentence
"AI fixes are broader" (or narrower) until the evidence supports it.

    python3 tools/calibration/measure_fix_breadth.py \\
        tools/calibration/ai.json tools/calibration/human.json \\
        --cache-dir DIR --out tools/calibration/fix_breadth.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).parent))

from analyze_cohorts import spearman  # noqa: E402
from measure_cohorts import mann_whitney  # noqa: E402

# Subject-line evidence that a commit is a fix. Word-bounded so
# "prefix" or "fixture" do not match. Symmetric across cohorts, so the
# noise it admits (a "fix typo" docs commit) does not favor a side.
_FIX_PATTERN = re.compile(r"\b(fix(es|ed)?|bug(fix)?|hotfix|patch)\b", re.I)

# A fix touching more than this many files is "broad" for the share
# metric. Five files is well past a change plus its test.
BROAD_FILES = 5

MIN_FIX_COMMITS = 5

METRICS = ("median_files_per_fix", "median_lines_per_fix", "broad_fix_share")


def clone(entry: dict, cache_dir: Path) -> Path | None:
    """Reuse the cohort cache; fetch 300 commits of history if absent."""
    target = cache_dir / entry["name"]
    if (target / ".git").exists():
        return target
    result = subprocess.run(
        ["git", "clone", "--quiet", "--depth", "300", entry["url"], str(target)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  !! clone failed {entry['full_name']}: {result.stderr.strip()[:90]}", file=sys.stderr)
        return None
    return target


def fix_commits(path: Path) -> list[tuple[int, int]]:
    """(files_touched, lines_changed) per fix commit."""
    result = subprocess.run(
        ["git", "log", "--no-merges", "--format=%x1e%s", "--numstat"],
        cwd=path, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []
    fixes = []
    for block in result.stdout.split("\x1e"):
        subject, _, body = block.partition("\n")
        if not _FIX_PATTERN.search(subject):
            continue
        files = 0
        lines = 0
        for row in body.splitlines():
            fields = row.split("\t")
            if len(fields) != 3:
                continue
            files += 1
            added, removed, _ = fields
            lines += (int(added) if added.isdigit() else 0) + (int(removed) if removed.isdigit() else 0)
        if files:
            fixes.append((files, lines))
    return fixes


def measure(entry: dict, cache_dir: Path) -> dict | None:
    path = clone(entry, cache_dir)
    if path is None:
        return None
    fixes = fix_commits(path)
    if len(fixes) < MIN_FIX_COMMITS:
        print(f"  -- {entry['full_name']}: only {len(fixes)} fix commits, skipped", file=sys.stderr)
        return None
    return {
        "repo": entry["full_name"],
        "declarations": entry["declarations"],
        "fix_commits": len(fixes),
        "median_files_per_fix": median(files for files, _ in fixes),
        "median_lines_per_fix": median(lines for _, lines in fixes),
        "broad_fix_share": sum(1 for files, _ in fixes if files > BROAD_FILES) / len(fixes),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cohorts", nargs=2, help="ai.json and human.json from select_authored.py.")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--out", default=str(Path(__file__).with_name("fix_breadth.json")))
    args = parser.parse_args()

    cache = Path(args.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    results: dict[str, list[dict]] = {}
    for source in args.cohorts:
        data = json.loads(Path(source).read_text(encoding="utf-8"))
        label = data["cohort"]
        measured = [entry for repo in data["repos"] if (entry := measure(repo, cache)) is not None]
        results[label] = measured
        print(f"{label}: {len(measured)}/{len(data['repos'])} repos with enough fix history", file=sys.stderr)

    ai, human = results.get("ai", []), results.get("human", [])
    pooled = ai + human
    print(f"\n{'metric':<24}{'ai':>10}{'human':>10}{'p':>10}{'size r':>9}")
    print("-" * 63)
    comparisons = {}
    for metric in METRICS:
        left, right = [r[metric] for r in ai], [r[metric] for r in human]
        test = mann_whitney(left, right)
        size_r = spearman([r["declarations"] for r in pooled], [r[metric] for r in pooled])
        comparisons[metric] = {"test": test, "size_correlation": round(size_r, 2)}
        p = f"{test['p']:.3f}" if test else "n/a"
        print(f"{metric:<24}{median(left):>10.3f}{median(right):>10.3f}{p:>10}{size_r:>9.2f}")

    Path(args.out).write_text(
        json.dumps(
            {
                "measured_on": datetime.now(UTC).date().isoformat(),
                "fix_pattern": _FIX_PATTERN.pattern,
                "broad_files_threshold": BROAD_FILES,
                "min_fix_commits": MIN_FIX_COMMITS,
                "note": (
                    "History depth is capped at 300 commits by the cohort clones; medians are "
                    "per-repo so cross-repo commit-volume differences do not weight the test."
                ),
                "cohorts": results,
                "comparisons": comparisons,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
