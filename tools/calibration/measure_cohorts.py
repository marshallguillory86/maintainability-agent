#!/usr/bin/env python3
"""Measure two cohorts against each other, and say what the comparison means.

``select_authored.py`` builds the cohorts; this measures them. The output
is the evidence behind the claims in ``docs/studies.md`` about signals
that separate AI-assisted code from human-written code — and, just as
importantly, the ones that do not.

**The comparison that answers the question is ai-assisted vs
recent-human.** Both cohorts are drawn from the same era, so age and
project type are roughly held constant and what remains is authorship.

**The comparison against the mature corpus does not answer it.** Mature
OSS is libraries with a decade of review pressure behind them; both
recent cohorts are mostly young applications. A gap there is maturity,
domain and authorship confounded together, and reading it as authorship
is the mistake this script exists to make hard. It is measured anyway,
because the size of the maturity gap is what puts the authorship gap in
proportion — but it is labelled, and ``--baseline`` names which cohort
the report treats as the control.

Rates, never counts: every figure is normalized by the population it was
drawn from, for the same reason the scores are. A cohort of larger repos
would otherwise "have more duplication" purely by being larger.

    python3 tools/calibration/measure_cohorts.py ai.json human.json \\
        --include-corpus --cache-dir DIR --out cohorts.json
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from maintainability_audit.config import load_config  # noqa: E402
from maintainability_audit.deadcode import dead_declarations  # noqa: E402
from maintainability_audit.metrics import iter_files  # noqa: E402
from maintainability_audit.report import build_report  # noqa: E402
from maintainability_audit.similarity import collect_fingerprints, find_near_duplicates  # noqa: E402
from maintainability_audit.source import SourceIndex  # noqa: E402

CORPUS = Path(__file__).with_name("corpus.json")

# Rates the comparison is about. Each is a share of the population it can
# possibly be drawn from, so cohorts of different sizes stay comparable.
METRICS = (
    "near_duplicate_rate",
    "dead_code_rate",
    "file_failure_rate",
    "function_failure_rate",
    "duplicate_block_rate",
)


def clone(repo: dict, cache_dir: Path) -> Path | None:
    """Fetch one repo at its pinned commit. Returns None if unavailable."""
    target = cache_dir / repo["name"]
    if (target / ".git").exists():
        return target
    target.mkdir(parents=True, exist_ok=True)
    for command in (
        ["git", "init", "--quiet"],
        ["git", "remote", "add", "origin", repo["url"]],
        ["git", "fetch", "--quiet", "--depth", "1", "origin", repo["commit"]],
        ["git", "checkout", "--quiet", "FETCH_HEAD"],
    ):
        result = subprocess.run(command, cwd=target, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  !! {repo['name']}: {' '.join(command[:2])} failed: {result.stderr.strip()[:110]}")
            return None
    return target


def measure(path: Path, name: str) -> dict | None:
    """Every rate for one repository.

    ``build_report`` truncates its near-duplicate and dead-code lists for
    readability, so those two are recomputed here in full — a rate built
    from a list capped at 25 would silently flatten exactly the repos the
    comparison is about.
    """
    config = load_config(None)
    source = SourceIndex()
    report = build_report(path, config)
    summary = report["summary"]

    files = iter_files(path, config)
    fingerprints = collect_fingerprints(path, files, index=source)
    eligible = len(fingerprints)
    cross_file = sum(
        1 for pair in find_near_duplicates(fingerprints) if pair.left.path != pair.right.path
    )
    dead = len(dead_declarations(path, files, source))

    production_declarations = max(1, summary["production_declarations_scanned"])
    production_files = max(1, summary["production_files_scanned"])
    if eligible < 1:
        # No declaration long enough to fingerprint. A rate over nothing
        # is not zero duplication, it is no measurement — drop the repo
        # rather than contribute a misleading 0.0 to a median.
        print(f"  -- {name}: no eligible declarations, skipped")
        return None

    return {
        "repo": name,
        "files": summary["files_scanned"],
        "declarations": summary["declarations_scanned"],
        "eligible_declarations": eligible,
        "score": report["score"]["overall"],
        "near_duplicate_rate": cross_file / eligible,
        "dead_code_rate": dead / production_declarations,
        "file_failure_rate": summary["production_file_failures"] / production_files,
        "function_failure_rate": summary["production_function_failures"] / production_declarations,
        "duplicate_block_rate": summary["duplicate_blocks"] / production_files,
    }


def distribution(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "median": round(median(ordered), 5),
        "p90": round(ordered[max(0, math.ceil(0.9 * len(ordered)) - 1)], 5),
        "max": round(ordered[-1], 5),
    }


def mann_whitney(left: list[float], right: list[float]) -> dict[str, float] | None:
    """Rank-sum test, so "indistinguishable" is a measurement not a vibe.

    Implemented here rather than pulled from scipy because this tool ships
    with no scientific dependencies and one offline comparison does not
    justify adding them. The p-value uses the normal approximation with
    both the **tie correction** and the continuity correction — matching
    ``scipy.stats.mannwhitneyu(method="asymptotic")``, which the test
    suite pins numerically. The first version averaged ranks for ties but
    kept the untied variance; on these metrics, where most repos tie at
    zero, that inflated p-values by up to 2.4x — and inflated p in a study
    concluding "no significant difference" is the convenient direction to
    be wrong in. Still rough below roughly n=10 per group; group sizes are
    reported so a reader can discount accordingly.
    """
    if len(left) < 3 or len(right) < 3:
        return None
    pooled = sorted([(v, 0) for v in left] + [(v, 1) for v in right])
    ranks: list[float] = [0.0] * len(pooled)
    tie_term = 0.0  # sum of t^3 - t over tie groups, for the variance
    index = 0
    while index < len(pooled):
        stop = index
        while stop + 1 < len(pooled) and pooled[stop + 1][0] == pooled[index][0]:
            stop += 1
        shared = (index + stop) / 2 + 1
        for position in range(index, stop + 1):
            ranks[position] = shared
        size = stop - index + 1
        tie_term += size**3 - size
        index = stop + 1

    rank_sum = sum(rank for rank, (_, group) in zip(ranks, pooled, strict=True) if group == 0)
    n_left, n_right = len(left), len(right)
    total = n_left + n_right
    u_left = rank_sum - n_left * (n_left + 1) / 2
    u = min(u_left, n_left * n_right - u_left)
    mean = n_left * n_right / 2
    variance = n_left * n_right / 12 * (total + 1 - tie_term / (total * (total - 1)))
    if variance <= 0:
        # Every value tied: the groups are literally identical in rank.
        return {"u": u, "z": 0.0, "p": 1.0}
    # Continuity correction on the *larger* U, signed, doubled and
    # clipped — scipy's exact formulation. Taking |z| instead looks
    # equivalent but is not at the boundary: identical groups put U at
    # its mean, where the correction lands on the far side of zero and
    # must clip to 1.0 rather than report a small spurious difference.
    z = (n_left * n_right - u - mean - 0.5) / math.sqrt(variance)
    p = min(1.0, 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2)))))
    return {"u": u, "z": round(z, 3), "p": round(p, 4)}


def load_cohort(path: Path) -> tuple[str, list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    # corpus.json is the mature reference and carries no cohort label.
    return data.get("cohort", "mature-oss"), data["repos"]


def print_table(results: dict[str, list[dict]]) -> None:
    names = list(results)
    for metric in METRICS:
        print(f"\n{metric}")
        print(f"  {'cohort':<16}{'n':>4}{'median':>11}{'p90':>11}{'max':>11}")
        for name in names:
            stats = distribution([entry[metric] for entry in results[name]])
            print(
                f"  {name:<16}{stats['n']:>4}{stats['median']:>11.4%}"
                f"{stats['p90']:>11.4%}{stats['max']:>11.4%}"
            )


def measure_cohort(source: Path, cache_dir: Path) -> tuple[str, list[dict]]:
    """Clone and measure every repository in one cohort file."""
    label, repos = load_cohort(source)
    print(f"\n{label}: {len(repos)} repos -> {cache_dir}")
    measured = []
    for repo in repos:
        path = clone(repo, cache_dir)
        if path is None:
            continue
        entry = measure(path, repo["name"])
        if entry is None:
            continue
        measured.append(entry)
        print(
            f"  {entry['repo']:<38} score={entry['score']:<5}"
            f" near_dup={entry['near_duplicate_rate']:.2%} dead={entry['dead_code_rate']:.2%}"
        )
    return label, measured


def compare(results: dict[str, list[dict]], baseline: str) -> dict[str, dict]:
    """Every cohort against the control, one rank-sum test per metric."""
    if baseline not in results:
        print(f"\nno significance tests: baseline cohort {baseline!r} was not measured")
        return {}
    comparisons = {}
    for label in results:
        if label == baseline:
            continue
        tests = {
            metric: mann_whitney(
                [e[metric] for e in results[label]], [e[metric] for e in results[baseline]]
            )
            for metric in METRICS
        }
        comparisons[f"{label}_vs_{baseline}"] = tests
        print(f"\n{label} vs {baseline} (Mann-Whitney, normal approximation)")
        for metric, test in tests.items():
            verdict = "n too small" if test is None else f"p={test['p']:.4f} z={test['z']:+.2f}"
            print(f"  {metric:<24}{verdict}")
    return comparisons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cohorts", nargs="+", help="Cohort files from select_authored.py.")
    parser.add_argument("--include-corpus", action="store_true", help="Also measure the mature reference corpus.")
    parser.add_argument("--cache-dir", help="Directory to clone into. Defaults to a temp dir.")
    # Must match the label select_authored.py writes, which is the bare
    # mode name. Defaulting to "recent-human" silently skipped every
    # significance test on the first full run — the comparison the whole
    # script exists for, absent from the output with only a one-line note.
    parser.add_argument("--baseline", default="human", help="Cohort the others are tested against.")
    parser.add_argument("--out", default=str(Path(__file__).with_name("cohorts.json")))
    args = parser.parse_args()

    sources = [Path(p) for p in args.cohorts]
    if args.include_corpus:
        sources.append(CORPUS)

    # Check the baseline exists *before* cloning anything. This ran for an
    # hour once and then reported no significance tests at all, because
    # the label did not match — the one output the script exists to
    # produce, missing, discovered at the end.
    labels = [load_cohort(source)[0] for source in sources]
    if args.baseline not in labels:
        print(f"baseline {args.baseline!r} is not among the cohorts {labels}; nothing to compare against")
        return 1

    cache_dir = Path(args.cache_dir) if args.cache_dir else Path(tempfile.mkdtemp(prefix="ma-cohorts-"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, list[dict]] = {}
    for source in sources:
        label, measured = measure_cohort(source, cache_dir)
        if measured:
            results[label] = measured

    if not results:
        print("no repos could be measured (network unavailable?)")
        return 1

    print_table(results)
    comparisons = compare(results, args.baseline)

    Path(args.out).write_text(
        json.dumps(
            {
                "measured_on": datetime.now(UTC).date().isoformat(),
                "baseline": args.baseline,
                "note": (
                    "ai-assisted vs recent-human isolates authorship; either against mature-oss "
                    "confounds authorship with maturity and project type."
                ),
                "cohorts": {
                    label: {
                        "summary": {m: distribution([e[m] for e in entries]) for m in METRICS},
                        "repos": entries,
                    }
                    for label, entries in results.items()
                },
                "comparisons": comparisons,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
