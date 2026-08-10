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

# The measurement window, and therefore the depth every cache must hold.
WINDOW_COMMITS = 300

METRICS = ("median_files_per_fix", "median_lines_per_fix", "broad_fix_share")


def _git(path: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=path, capture_output=True, text=True).stdout.strip()


def _reachable_commits(path: Path) -> int:
    count = _git(path, "rev-list", "--count", "HEAD")
    return int(count) if count.isdigit() else 0


def clone(entry: dict, cache_dir: Path) -> Path | None:
    """A clone at the manifest's pinned commit with the whole window behind it.

    Two audits landed here. The first found the measurement running over
    whatever history the cache happened to hold, which made the result
    irreproducible from pinned inputs; the window became a fixed
    ``git log -n 300``. The second found the deepening step gated on
    ``HEAD != pinned commit``, so a *shallow cache already at the pin*
    was accepted untouched: a depth-one clone of ``open-mercato/cezar``
    at its recorded pin yielded 0 fix commits where the deep cache
    yielded 96, silently dropping the repo from the population. A window
    is only deterministic if the history behind it is guaranteed, so
    depth is now verified and repaired independently of HEAD, and a
    subject that cannot be deepened is reported rather than quietly
    measured short.
    """
    target = cache_dir / entry["name"]
    if not (target / ".git").exists():
        result = subprocess.run(
            ["git", "clone", "--quiet", "--depth", str(WINDOW_COMMITS), entry["url"], str(target)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  !! clone failed {entry['full_name']}: {result.stderr.strip()[:90]}", file=sys.stderr)
            return None
    if _git(target, "rev-parse", "HEAD") != entry["commit"]:
        subprocess.run(["git", "fetch", "--quiet", "--depth", str(WINDOW_COMMITS), "origin", entry["commit"]],
                       cwd=target, capture_output=True, text=True)
        checked = subprocess.run(["git", "checkout", "--quiet", entry["commit"]],
                                 cwd=target, capture_output=True, text=True)
        if checked.returncode != 0:
            print(f"  !! {entry['full_name']}: cannot reach pinned {entry['commit'][:8]}", file=sys.stderr)
            return None
    return _deepen_to_window(target, entry)


def _deepen_to_window(target: Path, entry: dict) -> Path | None:
    """Guarantee the window's worth of history, whatever the cache held.

    A repository genuinely shorter than the window is fine — it stops
    being shallow once its root commit is fetched, and ``history_commits``
    records what it actually has. A repository that is still shallow and
    still short after deepening is not measurable reproducibly, so it is
    refused instead of contributing a truncated window.
    """
    for _ in range(2):
        if _reachable_commits(target) >= WINDOW_COMMITS:
            return target
        if _git(target, "rev-parse", "--is-shallow-repository") != "true":
            return target  # short history, fully fetched: the window is the repo
        subprocess.run(["git", "fetch", "--quiet", f"--depth={WINDOW_COMMITS}", "origin", entry["commit"]],
                       cwd=target, capture_output=True, text=True)
    print(f"  !! {entry['full_name']}: only {_reachable_commits(target)} commits reachable after "
          f"deepening to {WINDOW_COMMITS}; refusing a truncated window", file=sys.stderr)
    return None


def _numstat_totals(body: str) -> tuple[int, int]:
    files = 0
    lines = 0
    for row in body.splitlines():
        fields = row.split("\t")
        if len(fields) != 3:
            continue
        files += 1
        added, removed, _ = fields
        lines += (int(added) if added.isdigit() else 0) + (int(removed) if removed.isdigit() else 0)
    return files, lines


def fix_commits(path: Path) -> list[tuple[int, int]]:
    """(files_touched, lines_changed) per fix commit."""
    result = subprocess.run(
        ["git", "log", "-n", str(WINDOW_COMMITS), "--no-merges", "--format=%x1e%s", "--numstat"],
        cwd=path, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []
    fixes = []
    for block in result.stdout.split("\x1e"):
        subject, _, body = block.partition("\n")
        if not _FIX_PATTERN.search(subject):
            continue
        files, lines = _numstat_totals(body)
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
    depth = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=path,
                           capture_output=True, text=True).stdout.strip()
    return {
        "repo": entry["full_name"],
        "pinned_commit": entry["commit"],
        "history_commits": int(depth) if depth.isdigit() else None,
        "declarations": entry["declarations"],
        "fix_commits": len(fixes),
        "median_files_per_fix": median(files for files, _ in fixes),
        "median_lines_per_fix": median(lines for _, lines in fixes),
        "broad_fix_share": sum(1 for files, _ in fixes if files > BROAD_FILES) / len(fixes),
    }


def banded_comparisons(ai: list[dict], human: list[dict]) -> dict:
    """Size-banded re-test, computed and stored here — an audit caught
    the banded numbers living only in documentation, hand-derived from
    this script's output rather than produced by it."""
    if not ai or not human:
        return {}
    low = max(min(r["declarations"] for r in ai), min(r["declarations"] for r in human))
    high = min(max(r["declarations"] for r in ai), max(r["declarations"] for r in human))
    band_ai = [r for r in ai if low <= r["declarations"] <= high]
    band_human = [r for r in human if low <= r["declarations"] <= high]
    print(f"\nsize-banded {low}-{high} declarations: ai n={len(band_ai)} human n={len(band_human)}")
    return {
        "declaration_range": [low, high],
        "n_ai": len(band_ai),
        "n_human": len(band_human),
        "tests": {metric: _banded_test(metric, band_ai, band_human) for metric in METRICS},
    }


def _banded_test(metric: str, band_ai: list[dict], band_human: list[dict]) -> dict:
    left, right = [r[metric] for r in band_ai], [r[metric] for r in band_human]
    test = mann_whitney(left, right)
    shown = f"{test['p']:.3f}" if test else "n/a"
    print(f"  {metric:<22} ai={median(left):.3f} human={median(right):.3f} p={shown}")
    return {
        "median_ai": round(median(left), 4) if left else None,
        "median_human": round(median(right), 4) if right else None,
        "test": test,
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

    banded = banded_comparisons(ai, human)

    Path(args.out).write_text(
        json.dumps(
            {
                "measured_on": datetime.now(UTC).date().isoformat(),
                "fix_pattern": _FIX_PATTERN.pattern,
                "broad_files_threshold": BROAD_FILES,
                "min_fix_commits": MIN_FIX_COMMITS,
                "note": (
                    "Measured over the most recent 300 commits from each pinned HEAD (git log -n 300). "
                    "Every cache is verified to hold at least that much history before measurement and "
                    "deepened if it does not, so neither a deeper nor a shallower cache can change the "
                    "window: an audit showed a depth-one cache sitting at the correct pinned commit "
                    "producing zero fix commits where the deep cache produced 96, because the deepening "
                    "step was gated on the commit matching rather than on the depth. A repository whose "
                    "entire history is shorter than the window contributes what it has and records it in "
                    "history_commits; one that cannot be deepened is refused, not measured short. "
                    "Medians are per-repo so commit volume does not weight the test."
                ),
                "cohorts": results,
                "comparisons": comparisons,
                "banded": banded,
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
