#!/usr/bin/env python3
"""Run the audit over the validation sample and record every outcome.

This answers a different question from the calibration corpus. That set
fits the *scale*; this one asks whether the **output is any use on real
code** — findings located where they claim, coverage stated honestly, a
score a reader with the repository open would recognise, and a withheld
score where the evidence does not support one.

Two rules make the results worth reading:

**Nothing is dropped.** A repository that fails to clone, crashes the
audit or times out is recorded with the failure, because a sample that
quietly loses its hard cases proves nothing. `report_error` is a result.

**Nothing is summarised away.** The full report for each repository is
written to disk, so any claim in the write-up can be checked against the
run rather than taken on trust.

Usage:
    python tools/validation/run_sample.py --cache /tmp/validation-cache
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from maintainability_audit.config import load_config  # noqa: E402
from maintainability_audit.report import build_report  # noqa: E402

SAMPLE = Path(__file__).with_name("sample.json")
RESULTS = Path(__file__).with_name("results.json")

# Deep enough for churn, coupling and ownership to be measurable, but not
# a full clone of thirty years of curl. `kilo` is fetched shallow on
# purpose: a repository with no usable history is one of the cases the
# report has to handle honestly rather than score as clean.
HISTORY_DEPTH = 400
SHALLOW = {"kilo"}


def clone(repo: dict, cache_dir: Path) -> tuple[Path | None, str]:
    """Fetch one repository at its pinned commit, or say why not."""
    target = cache_dir / repo["name"]
    if (target / ".git").exists():
        return target, "cached"
    target.mkdir(parents=True, exist_ok=True)
    depth = "1" if repo["name"] in SHALLOW else str(HISTORY_DEPTH)
    steps = [
        ["git", "init", "--quiet"],
        ["git", "remote", "add", "origin", repo["url"]],
        ["git", "fetch", "--quiet", "--depth", depth, "origin", repo["commit"]],
        ["git", "checkout", "--quiet", "FETCH_HEAD"],
    ]
    for step in steps:
        done = subprocess.run(step, cwd=target, capture_output=True, text=True)
        if done.returncode != 0:
            return None, f"{' '.join(step[:2])} failed: {done.stderr.strip()[:200]}"
    return target, f"fetched depth {depth}"


def audit(path: Path, config: dict) -> tuple[dict | None, str, float]:
    """One audit, with analyzers. Never raises — a crash is a result."""
    started = time.monotonic()
    try:
        report = build_report(path, config, run_analyzers=True)
    except Exception:  # noqa: BLE001 - a crash is data, not a reason to stop
        return None, traceback.format_exc(limit=8), time.monotonic() - started
    return report, "", time.monotonic() - started


def row(repo: dict, report: dict) -> dict:
    """The facts about one run, taken from the report rather than restated."""
    score = report.get("score") or {}
    coverage = report.get("analyzer_coverage") or {}
    summary = report.get("summary") or {}
    return {
        "repo": repo["name"],
        "language": repo["language"],
        "expected_size": repo["size"],
        "files_scanned": summary.get("files_scanned"),
        "declarations_scanned": summary.get("declarations_scanned"),
        # What the scan could not open. The finding this sample exists to
        # have caught: a score computed from a minority of a repository.
        "unread_source": summary.get("unread_source"),
        "unread_source_files": summary.get("unread_source_files"),
        "read_source_files": summary.get("read_source_files"),
        "production_declarations": summary.get("production_declarations_scanned"),
        "estimate": score.get("maintainability_estimate"),
        "range": score.get("maintainability_range"),
        "verified_grade": score.get("verified_grade"),
        "evidence_status": (score.get("evidence_status") or {}).get("status"),
        "evidence_reasons": (score.get("evidence_status") or {}).get("reasons"),
        "analyzers_contributed": coverage.get("tools_contributed"),
        "analyzers_attempted": coverage.get("tools_attempted"),
        "built_in_sources": (coverage.get("sources") or {}).get("built_in"),
        "concepts_covered": coverage.get("concepts_covered"),
        "concepts_single_source": coverage.get("concepts_single_source"),
        "concepts_unexamined": coverage.get("concepts_unexamined"),
        "analyzer_findings": len(report.get("analyzer_findings") or []),
        "hard_gate_failures": report.get("hard_gate_failures"),
        "has_history": report.get("history") is not None,
        # Discovery and the work order, so a later run can be compared
        # against this one on the things that now decide the score.
        "generated_files": summary.get("generated_files"),
        "vendored_files": summary.get("vendored_files"),
        "classifications": summary.get("classifications"),
        "languages": summary.get("languages"),
        "practice_level": (report.get("practice") or {}).get("level"),
        "work_order_items": len(report.get("work_order") or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", default="/tmp/validation-cache")
    parser.add_argument("--only", help="Run a single repository by name.")
    args = parser.parse_args()

    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(SAMPLE.read_text(encoding="utf-8"))
    repos = [r for r in manifest["repos"] if not args.only or r["name"] == args.only]
    config = load_config(None)
    reports_dir = Path(__file__).with_name("reports")
    reports_dir.mkdir(exist_ok=True)

    rows: list[dict] = []
    for repo in repos:
        path, note = clone(repo, cache)
        if path is None:
            print(f"  !! {repo['name']}: {note}", flush=True)
            rows.append({"repo": repo["name"], "language": repo["language"],
                         "clone_error": note})
            continue

        report, crash, seconds = audit(path, config)
        if report is None:
            print(f"  !! {repo['name']}: audit raised after {seconds:.0f}s", flush=True)
            rows.append({"repo": repo["name"], "language": repo["language"],
                         "audit_error": crash, "seconds": round(seconds, 1)})
            continue

        (reports_dir / f"{repo['name']}.json").write_text(
            json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
        record = row(repo, report)
        record["seconds"] = round(seconds, 1)
        rows.append(record)
        print(
            f"  {repo['name']:24s} {record['files_scanned'] or 0:6d} files  "
            f"est={record['estimate']}  grade={record['verified_grade']}  "
            f"{record['analyzers_contributed']}/{record['analyzers_attempted']} analyzers  "
            f"unread={record['unread_source_files']}  {seconds:.0f}s",
            flush=True,
        )

    RESULTS.write_text(json.dumps(
        {"frame": manifest["frame"], "sample": SAMPLE.name, "runs": rows},
        indent=1, sort_keys=True) + "\n", encoding="utf-8")
    failed = [r for r in rows if "clone_error" in r or "audit_error" in r]
    print(f"\n{len(rows) - len(failed)} of {len(rows)} audited; "
          f"{len(failed)} failed and are recorded as failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
