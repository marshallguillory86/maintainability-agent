#!/usr/bin/env python3
"""Recompute every recorded arm from its preserved work dir.

The first four pairs were measured by a runner that diffed against
HEAD rather than the recorded base SHA. Verification showed no agent
moved HEAD, so those numbers *should* be identical — this script
replaces "should" with a re-derivation: every arm is re-diffed against
the manifest commit and its MA report rebuilt, and any discrepancy
from the recorded values is reported loudly rather than silently
overwritten.

    python3 tools/experiments/fix_scope/remeasure.py --work-dir WORK
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_experiment import ROOT, diff_stats, finding_paths, findings_total  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from maintainability_audit.config import load_config  # noqa: E402
from maintainability_audit.report import build_report  # noqa: E402

RESULTS = Path(__file__).with_name("results.json")

CHECKED_FIELDS = ("files_touched", "lines_changed", "out_of_scope_files", "findings_after")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    args = parser.parse_args()
    work = Path(args.work_dir)
    cache = Path(args.cache_dir)

    manifest: dict[str, str] = {}
    for cohort_file in ("ai.json", "human.json"):
        for repo in json.loads((ROOT / "tools/calibration" / cohort_file).read_text())["repos"]:
            manifest[repo["name"]] = repo["commit"]

    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    mismatches = 0
    for name, entry in results["runs"].items():
        base = manifest[name]
        # Scope is re-derived from the pristine cache, exactly as the
        # runner derived it, so both measurements share their ruler.
        scope = finding_paths(build_report(cache / name, load_config(None)))
        for arm in ("generic", "bounded"):
            workdir = work / f"{name}--{arm}"
            if not workdir.exists():
                print(f"!! {name} {arm}: work dir missing, cannot re-verify")
                mismatches += 1
                continue
            touched, lines = diff_stats(workdir, base)
            after = build_report(workdir, load_config(None))
            fresh = {
                "files_touched": len(touched),
                "lines_changed": lines,
                "out_of_scope_files": len([p for p in touched if p not in scope]),
                "findings_after": findings_total(after["summary"]),
            }
            recorded = entry[arm]
            diffs = {
                field: (recorded[field], fresh[field])
                for field in CHECKED_FIELDS
                if recorded[field] != fresh[field]
            }
            if diffs:
                mismatches += 1
                print(f"!! {name} {arm}: MISMATCH {diffs}")
            else:
                print(f"ok {name} {arm}: re-derived identically against base {base[:8]}")
            recorded["remeasured_against"] = base

    RESULTS.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    print(f"\n{mismatches} mismatches")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
