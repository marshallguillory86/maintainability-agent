"""Materialize history once, then measure from a pinned manifest.

ADR 001 stage 9. Everywhere else in this project, evidence is separated
from the act of collecting it; history was the exception. `measure` in
`measure_fix_breadth.py` called `clone` and then measured whatever came
back, so selection, network access and measurement were one step and the
result depended on the state of a cache nobody could inspect.

That coupling produced a real false result, and it took six audits to
find. The oldest commit a shallow clone holds has no parent locally, so
git diffs it against the empty tree and `--numstat` reports the whole
tree as added. One fix commit measured (1 file, 75 lines) in a full clone
and (2 files, 39 lines) at the shallow boundary — same commit, same
window, different numbers. Each audit repaired the symptom it found
because there was nothing to check the cache *against*.

This module is that something. Materialization runs once, touches the
network, and writes down exactly what it fetched:

    pinned head, the selection rule, the selected commit ids, the parent
    objects those commits require, and the tool version

Measurement then reads the manifest and the local cache and **never
touches the network**. A cache that has drifted from the manifest fails
closed with the difference named, instead of being measured as if it were
the pinned history. The reproducibility question stops being "what did
the cache hold that day" and becomes "does this cache match the file in
the repository", which anyone can answer.

Usage:

    python3 tools/calibration/history_manifest.py --build \\
        --cohort tools/calibration/ai.json --cohort tools/calibration/human.json \\
        --cache-dir DIR --out tools/calibration/history_manifest.json

    python3 tools/calibration/history_manifest.py --verify \\
        --manifest tools/calibration/history_manifest.json --cache-dir DIR
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from maintainability_audit.config import VERSION  # noqa: E402

#: The measurement window. Kept here because the manifest records the rule
#: it selected under, and a manifest built under a different window is not
#: comparable to one built under this one.
WINDOW_COMMITS = 300

#: One commit deeper than the window, so every commit *in* the window has
#: its parent locally and none is diffed against the empty tree.
FETCH_DEPTH = WINDOW_COMMITS + 1

SELECTION_RULE = f"git log -n {WINDOW_COMMITS} --no-merges, from the pinned commit"

MANIFEST_VERSION = 1


def git(path: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(  # noqa: S603 - argv list, never a shell
        ["git", *args], cwd=path, capture_output=True, text=True, timeout=600,
    )
    return result.returncode, result.stdout.strip()


def reachable_commits(path: Path) -> int:
    """How much history this clone actually holds.

    The depth check has to be independent of HEAD: a shallow cache sitting
    at exactly the pinned commit was once accepted untouched and measured
    zero fix commits where the deep cache measured 96.
    """
    code, count = git(path, "rev-list", "--count", "HEAD")
    return int(count) if code == 0 and count.isdigit() else 0


def _window_commits(path: Path) -> list[str]:
    """The commit ids the selection rule picks, newest first."""
    code, out = git(path, "log", "-n", str(WINDOW_COMMITS), "--no-merges", "--format=%H")
    return out.splitlines() if code == 0 else []


def _required_parents(path: Path, commits: list[str]) -> list[str]:
    """Parent objects the window needs but does not itself contain.

    These are what a shallow clone silently lacks. Recording them is what
    lets `verify` refuse a cache that would diff a commit against the
    empty tree rather than against its parent.
    """
    selected = set(commits)
    required: set[str] = set()
    for commit in commits:
        code, out = git(path, "rev-list", "--parents", "-n", "1", commit)
        if code != 0:
            continue
        parents = out.split()[1:]
        required.update(parent for parent in parents if parent not in selected)
    return sorted(required)


def _grafted(path: Path) -> list[str]:
    shallow = path / ".git" / "shallow"
    if not shallow.exists():
        return []
    return sorted(line.strip() for line in shallow.read_text().splitlines() if line.strip())


def materialize(entry: dict, cache_dir: Path) -> Path | None:
    """Fetch the pinned commit with the whole window behind it.

    The network half, unchanged in behaviour from what `measure_fix_breadth`
    did — depth verified and repaired independently of HEAD, because a
    shallow cache already sitting at the pin was once accepted untouched
    and measured as zero fix commits where the deep cache found 96.
    """
    target = cache_dir / entry["name"]
    if not (target / ".git").exists():
        code, _ = git(cache_dir, "clone", "--quiet", "--depth", str(FETCH_DEPTH),
                      entry["url"], str(target))
        if code != 0:
            print(f"  !! clone failed {entry['full_name']}", file=sys.stderr)
            return None
    _, head = git(target, "rev-parse", "HEAD")
    if head != entry["commit"]:
        git(target, "fetch", "--quiet", "--depth", str(FETCH_DEPTH), "origin", entry["commit"])
        code, _ = git(target, "checkout", "--quiet", entry["commit"])
        if code != 0:
            print(f"  !! {entry['full_name']}: cannot reach pinned {entry['commit'][:8]}",
                  file=sys.stderr)
            return None
    for _ in range(2):
        if reachable_commits(target) >= FETCH_DEPTH:
            return target
        _, shallow = git(target, "rev-parse", "--is-shallow-repository")
        if shallow != "true":
            return target  # genuinely shorter than the window, fully fetched
        git(target, "fetch", "--quiet", f"--depth={FETCH_DEPTH}", "origin", entry["commit"])
    print(f"  !! {entry['full_name']}: refusing a truncated window", file=sys.stderr)
    return None


def build(cohorts: dict[str, list[dict]], cache_dir: Path) -> dict:
    """Materialize every subject and write down what was fetched."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    subjects: dict[str, dict] = {}
    for cohort, entries in cohorts.items():
        for entry in entries:
            path = materialize(entry, cache_dir)
            if path is None:
                continue
            commits = _window_commits(path)
            if not commits:
                print(f"  !! {entry['full_name']}: no commits in window", file=sys.stderr)
                continue
            _, total = git(path, "rev-list", "--count", "HEAD")
            subjects[entry["full_name"]] = {
                "cohort": cohort,
                "name": entry["name"],
                "url": entry["url"],
                "pinned_head": entry["commit"],
                "history_commits": int(total) if total.isdigit() else None,
                "window_commits": commits,
                "required_parents": _required_parents(path, commits),
                "grafted": _grafted(path),
            }
            print(f"  {entry['full_name']}: {len(commits)} commits in window")
    return {
        "manifest_version": MANIFEST_VERSION,
        "built_on": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool_version": VERSION,
        "selection_rule": SELECTION_RULE,
        "window_commits": WINDOW_COMMITS,
        "fetch_depth": FETCH_DEPTH,
        "subjects": subjects,
    }


def verify(manifest: dict, cache_dir: Path) -> list[str]:
    """Check the cache against the manifest. No network, ever.

    Returns the problems found, empty when the cache is exactly what the
    manifest pinned. Fails closed on every difference rather than
    measuring a cache that has drifted.
    """
    problems: list[str] = []
    if manifest.get("window_commits") != WINDOW_COMMITS:
        problems.append(
            f"manifest window {manifest.get('window_commits')} != this tool's "
            f"{WINDOW_COMMITS}; the results are not comparable"
        )
    for full_name, subject in sorted(manifest.get("subjects", {}).items()):
        path = cache_dir / subject["name"]
        if not (path / ".git").exists():
            problems.append(f"{full_name}: no clone in the cache")
            continue
        code, head = git(path, "rev-parse", "HEAD")
        if code != 0 or head != subject["pinned_head"]:
            problems.append(
                f"{full_name}: cache is at {head[:8] or '?'}, manifest pins "
                f"{subject['pinned_head'][:8]}"
            )
            continue
        present = set(_window_commits(path))
        missing = [c for c in subject["window_commits"] if c not in present]
        if missing:
            problems.append(
                f"{full_name}: {len(missing)} of {len(subject['window_commits'])} "
                "pinned window commits are not in the cache"
            )
        # The defect this whole module exists for: a parent the window
        # needs but the cache lacks means git diffs that commit against
        # the empty tree and reports the whole file as changed.
        for parent in subject["required_parents"]:
            code, _ = git(path, "cat-file", "-e", f"{parent}^{{commit}}")
            if code != 0:
                problems.append(
                    f"{full_name}: required parent {parent[:8]} is absent, so a "
                    "commit in the window would be diffed against the empty tree"
                )
                break
    return problems


def _load_cohort(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("repos", data.get("entries", []))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="materialize and write a manifest")
    parser.add_argument("--verify", action="store_true", help="check a cache against a manifest")
    parser.add_argument("--cohort", action="append", type=Path, default=[])
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if args.build:
        cohorts = {path.stem: _load_cohort(path) for path in args.cohort}
        manifest = build(cohorts, args.cache_dir)
        target = args.out or Path("tools/calibration/history_manifest.json")
        target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {target} — {len(manifest['subjects'])} subjects")
        return 0

    if args.verify:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        problems = verify(manifest, args.cache_dir)
        if problems:
            print("cache does not match the manifest:")
            for line in problems:
                print(f"  {line}")
            return 1
        print(f"cache matches the manifest for {len(manifest['subjects'])} subjects")
        return 0

    parser.error("pass --build or --verify")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
