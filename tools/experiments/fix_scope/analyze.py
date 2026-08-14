#!/usr/bin/env python3
"""Apply PROTOCOL.md's decision rule to results.json.

**On which statistic is registered.** The protocol contains two
phrasings: "per-repo differences, medians across repos" in prose, and
explicit inequalities over marginal medians in the decision rule. A
hostile audit correctly noted the first analyzer computed only the
marginal form. Both are computed here; the registered inequalities
(marginal medians) decide the verdict, the paired differences are the
primary descriptive statistic, and **if the two disagree in direction
on any deciding metric the verdict is INCONCLUSIVE** — ambiguity in a
pre-registration is resolved against the experimenter, not for them.

Runs whose agent status is not "completed" are excluded from the
verdict and listed. An out_of_scope_share of None (nothing touched) is
excluded from scope medians, not scored as 0.0 — a run that did
nothing must not be rewarded with perfect scope.

    python3 tools/experiments/fix_scope/analyze.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import median

RESULTS = Path(__file__).with_name("results.json")
DECIDING = ("files_touched", "out_of_scope_share", "findings_closed")
REPORTED = ("files_touched", "lines_changed", "out_of_scope_share", "findings_closed")


def _values(pairs: list[dict], arm: str, metric: str) -> list[float]:
    values = [pair[arm][metric] for pair in pairs]
    return [float(v) for v in values if v is not None]


def _paired_diffs(pairs: list[dict], metric: str) -> list[float]:
    diffs = []
    for pair in pairs:
        left, right = pair["bounded"][metric], pair["generic"][metric]
        if left is not None and right is not None:
            diffs.append(float(left) - float(right))
    return diffs


def _print_rows(runs: dict) -> None:
    header = f"{'repo':<38}{'arm':>9}{'files':>7}{'lines':>8}{'oos':>7}{'closed':>8}"
    print(header)
    print("-" * len(header))
    for name, entry in runs.items():
        for arm in ("generic", "bounded"):
            row = entry[arm]
            rerun = " (rerun)" if "rerun" in row else ""
            print(
                f"{name[:37]:<38}{arm:>9}{row['files_touched']:>7}{row['lines_changed']:>8}"
                f"{str(row['out_of_scope_share']):>7}{row['findings_closed']:>8}{rerun}"
            )


def _marginals(pairs: list[dict]) -> dict[str, dict[str, float]]:
    print("\nmarginal medians (registered decision-rule form):")
    marginal = {}
    for metric in REPORTED:
        marginal[metric] = {arm: median(_values(pairs, arm, metric)) for arm in ("generic", "bounded")}
        sides = marginal[metric]
        print(f"  {metric:<22} generic={sides['generic']:<10.3f} bounded={sides['bounded']:.3f}")
    return marginal


def _paired_signs(pairs: list[dict]) -> dict[str, int]:
    print("\npaired differences, bounded minus generic (median [signs -/0/+]):")
    signs = {}
    for metric in DECIDING:
        diffs = _paired_diffs(pairs, metric)
        med = median(diffs) if diffs else 0.0
        signs[metric] = (med > 0) - (med < 0)
        tally = f"{sum(d < 0 for d in diffs)}/{sum(d == 0 for d in diffs)}/{sum(d > 0 for d in diffs)}"
        print(f"  {metric:<22} median_diff={med:<10.3f} [{tally}]")
    return signs


def _verdict(marginal: dict[str, dict[str, float]], paired_sign: dict[str, int]) -> str:
    narrower_files = marginal["files_touched"]["bounded"] < marginal["files_touched"]["generic"]
    narrower_scope = marginal["out_of_scope_share"]["bounded"] < marginal["out_of_scope_share"]["generic"]
    closes_enough = (
        marginal["findings_closed"]["bounded"] >= 0.8 * marginal["findings_closed"]["generic"]
    )

    def concurs(metric: str, marginal_says_narrower: bool) -> bool:
        return paired_sign[metric] == 0 or (paired_sign[metric] < 0) == marginal_says_narrower

    agree = concurs("files_touched", narrower_files) and concurs("out_of_scope_share", narrower_scope)

    print(f"\nbounded narrower on files touched : {narrower_files}")
    print(f"bounded narrower on out-of-scope  : {narrower_scope}")
    print(f"bounded closes >= 80% of generic  : {closes_enough}")
    print(f"paired and marginal forms agree   : {agree}")

    if not agree:
        return "INCONCLUSIVE"
    if narrower_files and narrower_scope and closes_enough:
        return "SUPPORTED"
    if (not narrower_files and not narrower_scope) or not closes_enough:
        return "FAILS"
    return "INCONCLUSIVE"


def main() -> int:
    data = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else RESULTS).read_text(encoding="utf-8"))
    runs = data["runs"]
    excluded = {
        name: {arm: entry[arm]["agent"]["status"] for arm in ("generic", "bounded")}
        for name, entry in runs.items()
        if any(entry[arm]["agent"]["status"] != "completed" for arm in ("generic", "bounded"))
    }
    pairs = [entry for name, entry in runs.items() if name not in excluded]
    print(f"protocol: {data['protocol']}  model: {data['model']}")
    print(f"pairs recorded: {len(runs)}  analyzable: {len(pairs)}  excluded: {excluded or 'none'}\n")

    _print_rows(runs)
    verdict = _verdict(_marginals(pairs), _paired_signs(pairs))
    print(f"\nverdict per pre-registered rule: {verdict}")
    if len(pairs) < 6:
        print(f"NOTE: {len(pairs)} of 6 analyzable pairs; verdict is provisional until all run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
