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

from maintainability_audit._analysis import analyze  # noqa: E402
from maintainability_audit._calibration import (  # noqa: E402
    CALIBRATION_C,
    DIMENSION_REFERENCES,
    DIMENSION_WEIGHTS,
)
from maintainability_audit._derive import derive_curve_constant, derive_references  # noqa: E402
from maintainability_audit._pressures import (  # noqa: E402
    analyzer_pressures,
    analyzer_production_pressures,
    production_pressures,
)
from maintainability_audit.config import VERSION, load_config  # noqa: E402
from maintainability_audit.evidence import normalize_report_evidence  # noqa: E402
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


# Summary keys the rubric aspects read. Stored per repo so the anchor
# can be derived through the same rollup users receive, not through a
# structural-only approximation. History-based aspects are absent on
# purpose: the corpus is pinned via shallow fetches, so history is
# genuinely unmeasurable here and those aspects renormalize away — in
# the derivation exactly as they would in a shallow-clone report.
EVIDENCE_KEYS = (
    "test_file_count",
    "production_declarations_scanned",
    "production_files_scanned",
    "production_file_warnings",
    "production_file_failures",
    "production_function_warnings",
    "production_function_failures",
    "production_hard_gate_failures",
    "dead_code_count",
    "near_duplicate_count",
    "idiom_concern_count",
    "has_readme",
    "has_changelog",
    "has_docs_dir",
)


def measure(path: Path, repo: dict, *, with_analyzers: bool = False) -> dict:
    """One repository, under the built-in detectors and optionally the analyzers.

    Both sources are recorded side by side rather than one replacing the
    other, because the question the corpus run has to answer is *how far
    apart are they*, and whether the gap holds across forty repositories
    decides whether swapping them is a recalibration or a redesign.

    Four ratios were quoted from this comparison before it was
    trustworthy — 4.0x, 0.3x, 0.19x and 0.77x — each an artifact of a
    bridge that measured something narrower than the built-in path it was
    being divided by. It is only worth reading now because
    `test_both_paths_agree_on_every_failure_criterion` holds the two
    formulas to each other and
    `test_analyzer_production_pressure_excludes_test_declarations` holds
    them to the same population.

    A repository where the analyzers could not run is recorded with
    ``analyzer_dimensions: null`` rather than dropped, so a partial corpus
    is visible instead of quietly smaller.
    """
    config = load_config(None)
    report = build_report(path, config)
    summary = report["summary"]
    # Normalized rather than passed raw. `dimension_pressures` has taken
    # typed evidence since ADR 001 stage 4, and this script kept handing
    # it the summary dict -- so it has raised on every repository since
    # 2026-08-10 while measurements.json is dated 08-09. The calibration
    # was not reproducible for two days, which is P6's whole promise, and
    # nothing noticed because no test runs this file.
    evidence = normalize_report_evidence(report)
    row = {
        "repo": repo["name"],
        # Provenance, so a stored row can be checked rather than trusted.
        # Rows used to carry the repository name alone: nothing said which
        # commit produced them or which tool version, so no run could tell a
        # stale measurement from a fresh one and every recalibration had to
        # re-measure the whole corpus. That is the same weakness ADR 001
        # stage 9 removed from the history corpus, in the other set of
        # numbers this project derives everything from.
        "pinned_commit": repo.get("commit"),
        "tool_version": VERSION,
        "scanner_fingerprint": scanner_fingerprint(),
        "files": summary["files_scanned"],
        "declarations": summary["declarations_scanned"],
        "dimensions": dimension_pressures(evidence.summary),
        "evidence": {key: summary[key] for key in EVIDENCE_KEYS},
    }
    # Always present, null when the pool did not contribute. The
    # derivation refuses a row without the key, because a file from the
    # pre-analyzer pipeline is indistinguishable from a current one until
    # the constant comes out unchanged — and "the pool ran and measured
    # nothing" is a different fact from "nobody asked the pool".
    row["analyzer_dimensions"] = None
    row["analyzer_production_dimensions"] = None
    row["analyzer_coverage"] = None
    if with_analyzers:
        analyzer, production, coverage = _analyzer_row(path, config)
        row["analyzer_dimensions"] = analyzer
        row["analyzer_production_dimensions"] = production
        row["analyzer_coverage"] = coverage
        # The built-in production reading, so the production comparison
        # has a denominator measured the same way on both sides.
        row["production_dimensions"] = production_pressures(evidence.summary)
    return row


def _analyzer_row(path: Path, config: dict) -> tuple[dict | None, dict | None, dict | None]:
    """Analyzer pressures for one repository, both populations, or a stated absence."""
    analysis = analyze(path, config)
    if analysis.error or not any(item.contributed for item in analysis.coverage):
        return None, None, {"error": analysis.error or "no tool contributed"}
    thresholds = config["thresholds"]
    return (
        analyzer_pressures(analysis.measurements, thresholds),
        analyzer_production_pressures(analysis.measurements, thresholds),
        {
            "tools": sorted(item.slug for item in analysis.coverage if item.contributed),
            # Which version of each tool produced this row. Determinism is
            # only promised against pinned analyzer versions, so a corpus
            # measured half on lizard 1.23 and half on 1.24 is not one
            # corpus — and without this field nobody could tell.
            "versions": {
                item.slug: item.version
                for item in analysis.coverage
                if item.contributed and item.version
            },
            "unexamined": analysis.gaps(),
            "single_source": analysis.single_source_concerns(),
        },
    )


def stored_measurements() -> list[dict]:
    """The checked-in corpus the shipped constants were derived from."""
    if not MEASUREMENTS.exists():
        return []
    return json.loads(MEASUREMENTS.read_text(encoding="utf-8")).get("measurements", [])


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


def _would_downgrade_stored_evidence(with_analyzers: bool) -> bool:
    """True when this run measured less than what is already stored."""
    if with_analyzers:
        return False
    return any(entry.get("analyzer_dimensions") for entry in stored_measurements())


def _refuses_downgrade(args: argparse.Namespace) -> bool:
    """True when this run would replace stronger evidence with weaker.

    Refused before doing the work, not after. Stored measurements fitted
    `--with-analyzers` are the analyzer-primary readings the shipped
    constants derive from; a run without that flag measures the built-ins
    only, and overwriting the first with the second silently replaces the
    corpus those constants were fitted to. The original WARNING said so
    *after* the file was already gone, and a first attempt at this check
    placed at the write site still cloned 112 repositories before refusing —
    an hour of network to reach a decision available at argument-parse time.
    """
    if args.check or args.replace_measurements:
        return False
    if not _would_downgrade_stored_evidence(args.with_analyzers):
        return False
    print(
        f"refusing to overwrite {MEASUREMENTS.relative_to(ROOT)}: it holds "
        "analyzer-primary measurements and this run would measure the built-ins "
        "only.\nRe-run with --with-analyzers, or pass --replace-measurements if "
        "a built-in-only corpus is genuinely what should be stored.",
        file=sys.stderr,
    )
    return True


#: The modules whose behaviour can change a measurement. A stored row stays
#: reusable across releases that do not touch these, and is invalidated the
#: moment one changes — which is the question reuse actually needs answered.
#: Keying on the release version instead was the first attempt and it was
#: wrong in both directions: it re-measured 112 repositories for a
#: documentation release, and it would have said nothing if the scanner
#: changed within one version. A module added to the measurement path
#: belongs in this list; scoring, rendering and reporting deliberately do
#: not, because they read measurements rather than produce them.
MEASUREMENT_PATH = (
    "source", "declarations", "metrics", "_metrics_types", "_cognitive", "_masking",
    "_ranges_core", "_ranges_js", "_ranges_java", "_ranges_c", "_ranges_cpp",
    "_ranges_csharp", "_ranges_fortran", "_tokens",
    "duplication", "deadcode", "idioms", "similarity", "history",
    "_discovery", "_practice", "_analysis", "_adapters", "_generic",
    "_metric_adapters", "_verdict_adapters", "_jvm_adapters", "_tool_adapters",
    "_selection", "_pressures", "_built_ins",
)


def scanner_fingerprint() -> str:
    """A digest of the code that produces measurements, not of the release."""
    import hashlib

    package = ROOT / "src" / "maintainability_audit"
    digest = hashlib.sha256()
    for name in sorted(MEASUREMENT_PATH):
        path = package / f"{name}.py"
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def _reusable(repo: dict, with_analyzers: bool) -> dict | None:
    """A stored row that provably measured this exact repository state.

    Reuse is what makes adding a language cost its own repositories rather
    than the whole corpus — 16 instead of 112 — but it is only safe because
    rows now carry what produced them. A row is reusable when it pinned the
    same commit under the same tool version and holds the analyzer readings
    this run would produce. Anything else is measured again; the cost of a
    wrong reuse is a constant fitted to a corpus that never existed.
    """
    for entry in stored_measurements():
        if entry.get("repo") != repo["name"]:
            continue
        if entry.get("pinned_commit") != repo.get("commit"):
            return None
        if entry.get("scanner_fingerprint") != scanner_fingerprint():
            return None
        if with_analyzers and not entry.get("analyzer_dimensions"):
            return None
        return entry
    return None


def _mixed_analyzer_versions(rows: list[dict]) -> dict[str, set[str]]:
    """Tools that did not read the same version across the corpus.

    Determinism is promised against *pinned* analyzer versions, so a corpus
    measured partly on one version of a tool and partly on another is not a
    corpus — the medians would mix two instruments. Reuse makes that
    reachable for the first time, so it is checked before anything is
    written rather than trusted.
    """
    seen: dict[str, set[str]] = {}
    for row in rows:
        for slug, version in ((row.get("analyzer_coverage") or {}).get("versions") or {}).items():
            seen.setdefault(slug, set()).add(version)
    return {slug: versions for slug, versions in seen.items() if len(versions) > 1}


def _collect(manifest: dict, cache_dir: Path, args: argparse.Namespace) -> tuple[list[dict], int]:
    """Every repository's row, reusing what provably still applies."""
    measurements: list[dict] = []
    reused = 0
    for repo in manifest["repos"]:
        if args.reuse and (stored := _reusable(repo, args.with_analyzers)) is not None:
            measurements.append(stored)
            reused += 1
            continue
        path = clone(repo, cache_dir)
        if path is None:
            continue
        entry = measure(path, repo, with_analyzers=args.with_analyzers)
        measurements.append(entry)
        print(f"  {entry['repo']:<12} files={entry['files']:<6} " + " ".join(
            f"{k}={v:.4f}" for k, v in entry["dimensions"].items()), flush=True)
    return measurements, reused


def _refuses_mixed_versions(measurements: list[dict], reused: int) -> bool:
    """True when the corpus was not measured on one analyzer pool."""
    if reused:
        print(f"\nreused {reused} stored rows; measured {len(measurements) - reused}")
    mixed = _mixed_analyzer_versions(measurements)
    if not mixed:
        return False
    print(
        "\nrefusing to fit constants to a corpus measured on more than one "
        "version of a tool:",
        file=sys.stderr,
    )
    for slug, versions in sorted(mixed.items()):
        print(f"  {slug}: {', '.join(sorted(versions))}", file=sys.stderr)
    print("Re-run without --reuse to measure the whole corpus on one pool.",
          file=sys.stderr)
    return True


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", help="Directory to clone into. Defaults to a temp dir.")
    parser.add_argument(
        "--with-analyzers", action="store_true",
        help="Also run the external analyzer pool on each repository and record its "
             "pressures beside the built-in ones. Slower by orders of magnitude, and "
             "the input the Phase 3.6 recalibration needs.",
    )
    parser.add_argument("--check", action="store_true", help="Exit 1 if stored constants differ from measured.")
    parser.add_argument(
        "--reuse", action="store_true",
        help="Reuse stored rows whose pinned commit, tool version and analyzer "
             "population match, and measure only the rest. Adding a language "
             "then costs its own repositories instead of the whole corpus.",
    )
    parser.add_argument(
        "--replace-measurements", action="store_true",
        help="Allow a built-in-only run to overwrite stored analyzer-primary "
             "measurements. Needed only when a built-in-only corpus is the "
             "intended evidence.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()

    if _refuses_downgrade(args):
        return 2

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cache_dir = Path(args.cache_dir) if args.cache_dir else Path(tempfile.mkdtemp(prefix="ma-corpus-"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"corpus: {len(manifest['repos'])} repos -> {cache_dir}")

    measurements, reused = _collect(manifest, cache_dir, args)

    if not measurements:
        print("no repos could be measured (network unavailable?)")
        return 1

    if _refuses_mixed_versions(measurements, reused):
        return 2

    references = derive_references(measurements)
    curve = derive_curve_constant(measurements, references, DIMENSION_WEIGHTS)
    if args.check:
        # A check reports; it does not rewrite the evidence it checks
        # against. Writing here replaced the checked-in analyzer-primary
        # measurements with whatever this run happened to produce — and
        # a `--check` without `--with-analyzers` produces a *different
        # corpus*, so it reported a large false CALIBRATION_C drift and
        # left the tree holding the corpus that "proved" it.
        print(f"\n--check: {MEASUREMENTS.relative_to(ROOT)} left as-is")
    else:
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
    if not args.with_analyzers and any(
        entry.get("analyzer_dimensions") for entry in stored_measurements()
    ):
        print(
            "\nWARNING: the stored constants were fitted with --with-analyzers and "
            "this run measured the built-ins only. Any drift below is that "
            "difference, not necessarily a real one. Re-run with --with-analyzers "
            "before believing it."
        )
    stale = report_drift(references, curve)
    if stale:
        print("\nConstants differ from the measured corpus. Update _calibration.py if this is intended.")
    return 1 if (stale and args.check) else 0


if __name__ == "__main__":
    sys.exit(main())
