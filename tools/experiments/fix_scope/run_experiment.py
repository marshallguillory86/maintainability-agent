#!/usr/bin/env python3
"""Execute the pre-registered fix-scope experiment. See PROTOCOL.md.

The protocol is the authority; this file is plumbing. Anything this
script does that the protocol does not describe is a bug in one of
them, and the protocol wins.

    python3 tools/experiments/fix_scope/run_experiment.py \\
        --cache-dir CACHE --work-dir WORK --out results.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from maintainability_audit.config import load_config  # noqa: E402
from maintainability_audit.prompts import render_ai_prompt  # noqa: E402
from maintainability_audit.report import build_report  # noqa: E402

# Fixed by PROTOCOL.md. Do not tune.
SUBJECTS = (
    "Omikaye__Binary-Star-Pokedex",
    "KateBeston__TGS-Platform",
    "abiere__medical-rag-state",
    "sergey-levko__macro-mind",
    "alkhas72__goapsny-mvp",
    "SanjibBayen__rental-management-system-odoo-devdaas",
)
GENERIC_PROMPT = (
    "Improve the maintainability of this codebase. "
    "Make the code easier to understand, modify, and test."
)
MODEL = "gpt-5.6-sol"
RUN_TIMEOUT_SECONDS = 600

FINDING_COUNT_KEYS = (
    "file_failures",
    "function_failures",
    "duplicate_blocks",
    "near_duplicate_count",
    "dead_code_count",
)


def finding_paths(report: dict) -> set[str]:
    """Every path the MA report names as a finding — the "in scope" set."""
    paths: set[str] = set()
    paths.update(item["path"] for item in report["function_hotspots"])
    paths.update(item["path"] for item in report["largest_files"] if item["status"] != "ok")
    for block in report["duplicate_blocks"]:
        paths.update(location.rsplit(":", 1)[0] for location in block["locations"])
    for item in report["near_duplicates"]:
        paths.add(item["path"])
        paths.add(item["duplicate_of"]["path"])
    paths.update(item["path"] for item in report["dead_code"])
    paths.update(item["path"] for item in report["risk_findings"])
    return paths


def findings_total(summary: dict) -> int:
    return sum(int(summary.get(key, 0)) for key in FINDING_COUNT_KEYS)


def _git(path: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=path, capture_output=True, text=True).stdout.strip()


def fresh_copy(cache: Path, name: str, work: Path, arm: str, pinned: str) -> tuple[Path, str]:
    """A pristine copy, validated against the manifest before use.

    Returns the copy and its base SHA. A hostile audit correctly noted
    the first version trusted the cache blindly and diffed against
    HEAD — which an agent that commits would move, silently deleting
    its own changes from measurement. The base SHA is recorded at copy
    time and every diff is taken against it explicitly.
    """
    source = cache / name
    head = _git(source, "rev-parse", "HEAD")
    if head != pinned:
        raise RuntimeError(f"{name}: cache at {head[:8]}, manifest pins {pinned[:8]}")
    if _git(source, "status", "--short"):
        raise RuntimeError(f"{name}: cache clone is dirty")
    target = work / f"{name}--{arm}"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, symlinks=True)
    return target, head


def run_agent(workdir: Path, prompt: str) -> dict:
    """One codex run under the protocol's fixed budget and sandbox."""
    started = datetime.now(UTC)
    try:
        completed = subprocess.run(
            ["codex", "exec", "-C", str(workdir), "-s", "workspace-write",
             "--ephemeral", "--ignore-user-config", "-m", MODEL, prompt],
            capture_output=True, text=True, timeout=RUN_TIMEOUT_SECONDS,
        )
        status = "completed" if completed.returncode == 0 else f"exit {completed.returncode}"
        tail = (completed.stdout or "")[-2000:]
    except subprocess.TimeoutExpired as expired:
        status = "timeout"
        tail = ((expired.stdout or b"").decode(errors="replace"))[-2000:]
    return {
        "status": status,
        "seconds": round((datetime.now(UTC) - started).total_seconds(), 1),
        "output_tail": tail,
    }


def diff_stats(workdir: Path, base: str) -> tuple[list[str], int]:
    """(touched files, lines added+removed) against the recorded base SHA.

    ``git add -A`` first so untracked files the agent created are
    counted; the diff is then taken from the explicit base, so agent
    commits — none observed, but possible — cannot hide changes.
    """
    subprocess.run(["git", "add", "-A"], cwd=workdir, capture_output=True)
    numstat = subprocess.run(
        ["git", "diff", "--cached", base, "--numstat"], cwd=workdir, capture_output=True, text=True
    ).stdout
    touched: list[str] = []
    lines = 0
    for row in numstat.splitlines():
        fields = row.split("\t")
        if len(fields) != 3:
            continue
        added, removed, path = fields
        touched.append(path)
        lines += (int(added) if added.isdigit() else 0) + (int(removed) if removed.isdigit() else 0)
    return touched, lines


def measure_arm(workdir: Path, base: str, prompt: str, scope: set[str], before_total: int) -> dict:
    agent = run_agent(workdir, prompt)
    touched, lines = diff_stats(workdir, base)
    after = build_report(workdir, load_config(None))
    out_of_scope = [path for path in touched if path not in scope]
    return {
        "agent": agent,
        "base_sha": base,
        "files_touched": len(touched),
        "lines_changed": lines,
        "out_of_scope_files": len(out_of_scope),
        "out_of_scope_share": round(len(out_of_scope) / len(touched), 3) if touched else None,
        "findings_after": findings_total(after["summary"]),
        "findings_closed": before_total - findings_total(after["summary"]),
        "score_after": after["score"]["maintainability_estimate"],
        "touched": touched[:100],
    }


def run_arm_with_retry(
    cache: Path, name: str, work: Path, arm: str, pinned: str, prompt: str, scope: set[str], before_total: int
) -> dict:
    """One arm, with the protocol's rerun-once rule implemented.

    A crashed run or one that changed nothing is rerun exactly once
    from a fresh copy; the rerun is recorded in the result. A second
    failure stands as the result — the protocol does not allow fishing.
    """
    copy, base = fresh_copy(cache, name, work, arm, pinned)
    result = measure_arm(copy, base, prompt, scope, before_total)
    crashed = result["agent"]["status"] != "completed"
    if crashed or result["files_touched"] == 0:
        reason = "crash" if crashed else "no change"
        print(f"  arm {arm}: {reason}; protocol rerun (once)")
        copy, base = fresh_copy(cache, name, work, arm, pinned)
        result = measure_arm(copy, base, prompt, scope, before_total)
        result["rerun"] = reason
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", required=True, help="Pinned cohort clones (clones-measure).")
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--out", default=str(Path(__file__).with_name("results.json")))
    parser.add_argument("--subjects", nargs="*", default=list(SUBJECTS))
    args = parser.parse_args()

    cache, work = Path(args.cache_dir), Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out)
    results = (
        json.loads(out_path.read_text(encoding="utf-8"))
        if out_path.exists()
        else {
            "protocol": "tools/experiments/fix_scope/PROTOCOL.md",
            "started": datetime.now(UTC).isoformat(),
            "model": MODEL,
            "generic_prompt": GENERIC_PROMPT,
            "runs": {},
        }
    )

    manifest: dict[str, str] = {}
    for cohort_file in ("ai.json", "human.json"):
        for repo in json.loads((ROOT / "tools/calibration" / cohort_file).read_text())["repos"]:
            manifest[repo["name"]] = repo["commit"]

    for name in args.subjects:
        if name in results["runs"]:
            print(f"{name}: already recorded, skipping")
            continue
        print(f"\n=== {name} ===")
        pinned = manifest[name]
        before = build_report(cache / name, load_config(None))
        scope = finding_paths(before)
        before_total = findings_total(before["summary"])
        bounded_prompt = render_ai_prompt(before)
        print(f"  findings before: {before_total}, in-scope files: {len(scope)}")

        entry: dict = {
            "findings_before": before_total,
            "score_before": before["score"]["maintainability_estimate"],
            "in_scope_files": len(scope),
            "bounded_prompt_chars": len(bounded_prompt),
            "pinned_commit": pinned,
        }
        for arm, prompt in (("generic", GENERIC_PROMPT), ("bounded", bounded_prompt)):
            print(f"  arm {arm}: running...")
            entry[arm] = run_arm_with_retry(cache, name, work, arm, pinned, prompt, scope, before_total)
            print(
                f"  arm {arm}: {entry[arm]['agent']['status']} in {entry[arm]['agent']['seconds']}s"
                f" — files={entry[arm]['files_touched']} lines={entry[arm]['lines_changed']}"
                f" closed={entry[arm]['findings_closed']} oos={entry[arm]['out_of_scope_share']}"
            )
        results["runs"][name] = entry
        out_path.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
        print(f"  saved -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
