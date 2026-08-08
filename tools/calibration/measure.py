#!/usr/bin/env python3
"""Measure the reference corpus and regenerate the calibration constants.

The scoring scale is only meaningful if the numbers behind it can be
reproduced. This script is the network half of that: it clones each repo
in ``corpus.json`` at its pinned commit, audits it under the package
defaults, and writes ``measurements.json``.

The arithmetic from those measurements to the constants in
``_calibration.py`` lives in ``maintainability_audit._derive`` and is
re-run offline by ``tests/test_calibration_corpus.py``, so nobody has to
take the constants on faith.

Usage:

    python3 tools/calibration/measure.py                 # clone + measure + report
    python3 tools/calibration/measure.py --cache-dir DIR # reuse existing clones
    python3 tools/calibration/measure.py --check         # fail if constants are stale

Re-run this whenever the default thresholds change. The constants are an
anchor for every score the tool emits; changing thresholds without
recalibrating silently moves the meaning of every grade.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from maintainability_audit._calibration import (  # noqa: E402
    CALIBRATION_C,
    DIMENSION_REFERENCES,
    DIMENSION_WEIGHTS,
)
from maintainability_audit._derive import derive_curve_constant, derive_references  # noqa: E402
from maintainability_audit.config import load_config  # noqa: E402
from maintainability_audit.report import build_report  # noqa: E402
from maintainability_audit.scoring import dimension_pressures  # noqa: E402

MANIFEST = Path(__file__).with_name("corpus.json")
MEASUREMENTS = Path(__file__).with_name("measurements.json")


def clone(repo: dict[str, str], cache_dir: Path) -> Path | None:
    """Fetch one repo at its pinned commit. Returns None if unavailable."""
    target = cache_dir / repo["name"]
    if (target / ".git").exists():
        return target
    target.mkdir(parents=True, exist_ok=True)
    commands = [
        ["git", "init", "--quiet"],
        ["git", "remote", "add", "origin", repo["url"]],
        ["git", "fetch", "--quiet", "--depth", "1", "origin", repo["commit"]],
        ["git", "checkout", "--quiet", "FETCH_HEAD"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=target, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  !! {repo['name']}: {' '.join(command[:2])} failed: {result.stderr.strip()[:120]}")
            return None
    return target


def measure(path: Path, name: str) -> dict:
    report = build_report(path, load_config(None))
    summary = report["summary"]
    return {
        "repo": name,
        "files": summary["files_scanned"],
        "declarations": summary["declarations_scanned"],
        "dimensions": dimension_pressures(summary),
    }


def report_drift(references: dict[str, float], curve: float) -> bool:
    """Print the stored constants beside the freshly measured ones."""
    stale = False
    print(f"\n{'dimension':<16}{'stored':>12}{'measured':>12}")
    print("-" * 40)
    for name, value in references.items():
        stored = DIMENSION_REFERENCES.get(name)
        flag = "" if stored == value else "   <- drift"
        stale = stale or stored != value
        print(f"{name:<16}{stored!s:>12}{value!s:>12}{flag}")
    flag = "" if curve == CALIBRATION_C else "   <- drift"
    stale = stale or curve != CALIBRATION_C
    print(f"{'CALIBRATION_C':<16}{CALIBRATION_C!s:>12}{curve!s:>12}{flag}")
    return stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", help="Directory to clone into. Defaults to a temp dir.")
    parser.add_argument("--check", action="store_true", help="Exit 1 if stored constants differ from measured.")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cache_dir = Path(args.cache_dir) if args.cache_dir else Path(tempfile.mkdtemp(prefix="ma-corpus-"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"corpus: {len(manifest['repos'])} repos -> {cache_dir}")

    measurements = []
    for repo in manifest["repos"]:
        path = clone(repo, cache_dir)
        if path is None:
            continue
        entry = measure(path, repo["name"])
        measurements.append(entry)
        print(f"  {entry['repo']:<12} files={entry['files']:<6} " + " ".join(
            f"{k}={v:.4f}" for k, v in entry["dimensions"].items()))

    if not measurements:
        print("no repos could be measured (network unavailable?)")
        return 1

    references = derive_references(measurements)
    curve = derive_curve_constant(measurements, references, DIMENSION_WEIGHTS)
    MEASUREMENTS.write_text(
        json.dumps(
            {
                # The manifest is generated by verify_corpus.py and does
                # not carry a date; stamp the measurement instead, since
                # that is what the constants are derived from.
                "measured_on": datetime.now(UTC).date().isoformat(),
                "corpus_size": len(measurements),
                "measurements": measurements,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {MEASUREMENTS.relative_to(ROOT)} ({len(measurements)} repos)")
    stale = report_drift(references, curve)
    if stale:
        print("\nConstants differ from the measured corpus. Update _calibration.py if this is intended.")
    return 1 if (stale and args.check) else 0


if __name__ == "__main__":
    sys.exit(main())
