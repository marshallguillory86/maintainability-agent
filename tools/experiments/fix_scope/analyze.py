#!/usr/bin/env python3
"""Apply PROTOCOL.md's pre-registered decision rule to results.json.

Written while the experiment was still running, so the rule is code
before the numbers exist. The verdict is printed as one of exactly
three words — SUPPORTED, FAILS, INCONCLUSIVE — computed, not narrated.

    python3 tools/experiments/fix_scope/analyze.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import median

RESULTS = Path(__file__).with_name("results.json")


def main() -> int:
    data = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else RESULTS).read_text(encoding="utf-8"))
    runs = data["runs"]
    print(f"protocol: {data['protocol']}  model: {data['model']}  pairs: {len(runs)}\n")

    header = f"{'repo':<36}{'arm':>9}{'files':>7}{'lines':>8}{'oos':>7}{'closed':>8}{'status':>11}"
    print(header)
    print("-" * len(header))
    per_metric: dict[str, dict[str, list[float]]] = {
        "files_touched": {"generic": [], "bounded": []},
        "lines_changed": {"generic": [], "bounded": []},
        "out_of_scope_share": {"generic": [], "bounded": []},
        "findings_closed": {"generic": [], "bounded": []},
    }
    for name, entry in runs.items():
        for arm in ("generic", "bounded"):
            row = entry[arm]
            for metric, buckets in per_metric.items():
                value = row[metric]
                buckets[arm].append(0.0 if value is None else float(value))
            print(
                f"{name[:35]:<36}{arm:>9}{row['files_touched']:>7}{row['lines_changed']:>8}"
                f"{str(row['out_of_scope_share']):>7}{row['findings_closed']:>8}"
                f"{row['agent']['status'][:10]:>11}"
            )

    print()
    medians = {
        metric: {arm: median(values) for arm, values in buckets.items()}
        for metric, buckets in per_metric.items()
    }
    for metric, sides in medians.items():
        print(f"median {metric:<22} generic={sides['generic']:<10.3f} bounded={sides['bounded']:.3f}")

    narrower_files = medians["files_touched"]["bounded"] < medians["files_touched"]["generic"]
    narrower_scope = medians["out_of_scope_share"]["bounded"] < medians["out_of_scope_share"]["generic"]
    closes_enough = medians["findings_closed"]["bounded"] >= 0.8 * medians["findings_closed"]["generic"]

    print(f"\nbounded narrower on files touched : {narrower_files}")
    print(f"bounded narrower on out-of-scope  : {narrower_scope}")
    print(f"bounded closes >= 80% of generic  : {closes_enough}")

    if narrower_files and narrower_scope and closes_enough:
        verdict = "SUPPORTED"
    elif (not narrower_files and not narrower_scope) or not closes_enough:
        verdict = "FAILS"
    else:
        verdict = "INCONCLUSIVE"
    print(f"\nverdict per pre-registered rule: {verdict}")
    if len(runs) < 6:
        print(f"NOTE: only {len(runs)} of 6 pairs recorded; verdict is provisional until all run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
