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

import history_manifest  # noqa: E402
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

# One commit deeper than the window. The oldest commit a shallow clone
# holds has no parent locally, so git diffs it against the empty tree
# and its --numstat reports the whole tree as added rather than what the
# commit actually changed. Fetching one extra commit keeps every commit
# *in* the window parented, and `_grafted_commits` refuses the boundary
# outright in case a cache arrives shallow at exactly the window.
FETCH_DEPTH = WINDOW_COMMITS + 1

METRICS = ("median_files_per_fix", "median_lines_per_fix", "broad_fix_share")


def _git(path: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=path, capture_output=True, text=True).stdout.strip()







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


def _grafted_commits(path: Path) -> set[str]:
    """Commits whose parents this clone does not have.

    Git diffs a parentless commit against the empty tree, so the oldest
    commit in a shallow clone reports its entire tree as added instead
    of what it changed. An audit built the case: one fix commit measured
    (1 file, 75 lines) in a full clone and (2 files, 39 lines) at the
    shallow boundary — same commit, same window size, different numbers.
    A true root commit is not listed here, so a repository shorter than
    the window still measures its first commit normally.
    """
    shallow = path / ".git" / "shallow"
    if not shallow.exists():
        return set()
    return {line.strip() for line in shallow.read_text().splitlines() if line.strip()}


def fix_commits(path: Path) -> list[tuple[int, int]]:
    """(files_touched, lines_changed) per fix commit in the window."""
    result = subprocess.run(
        ["git", "log", "-n", str(WINDOW_COMMITS), "--no-merges", "--format=%x1e%H%x1f%s", "--numstat"],
        cwd=path, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []
    grafted = _grafted_commits(path)
    fixes = []
    for block in result.stdout.split("\x1e"):
        header, _, body = block.partition("\n")
        sha, _, subject = header.partition("\x1f")
        if sha.strip() in grafted or not _FIX_PATTERN.search(subject):
            continue
        files, lines = _numstat_totals(body)
        if files:
            fixes.append((files, lines))
    return fixes


def measure(entry: dict, cache_dir: Path) -> dict | None:
    """Measure one subject from the cache. Reads only; never fetches.

    ADR 001 stage 9 moved materialization out of this function. It used to
    call `clone`, so measuring a repository could reach the network and
    change the cache it was about to measure — selection, acquisition and
    measurement in one step, with the result depending on cache state
    nobody could inspect. `history_manifest.py` now does the fetching and
    writes down what it fetched; this side reads the result and refuses a
    cache the manifest does not describe.
    """
    path = cache_dir / entry["name"]
    if not (path / ".git").exists():
        print(f"  !! {entry['full_name']}: not materialized; run history_manifest.py --build",
              file=sys.stderr)
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


def _cache_matches_the_pin(manifest_path: Path, cache: Path) -> int:
    """The stage 9 gate: measure only a cache the manifest describes.

    Checked before anything is measured and without touching the network.
    A drifted cache is refused rather than measured as if it were pinned —
    the shallow-boundary defect took six audits to find precisely because
    there was nothing to check the cache against. Returns a process exit
    code, 0 when the cache is exactly what was pinned.
    """
    if not manifest_path.exists():
        print(f"no manifest at {manifest_path}; run history_manifest.py --build first",
              file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems = history_manifest.verify(manifest, cache)
    if problems:
        print("refusing to measure: the cache does not match the pinned manifest",
              file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"cache matches the manifest built {manifest['built_on']} "
          f"({len(manifest['subjects'])} subjects)", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cohorts", nargs=2, help="ai.json and human.json from select_authored.py.")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--manifest", default=str(Path(__file__).with_name("history_manifest.json")),
                        help="the pinned history this measurement is reproducible against")
    parser.add_argument("--out", default=str(Path(__file__).with_name("fix_breadth.json")))
    args = parser.parse_args()

    cache = Path(args.cache_dir)
    refusal = _cache_matches_the_pin(Path(args.manifest), cache)
    if refusal:
        return refusal

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
