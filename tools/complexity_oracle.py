"""Compare this project's complexity against an independent implementation.

Every branch keyword set in this project was, until now, asserted rather
than tested: a list of keywords written from somebody's knowledge of a
language, checked against examples written by the same person from the
same knowledge. That is not evidence. It reads as evidence because the
prose around it is confident, which is worse than reading as a guess.

`lizard` computes cyclomatic complexity for most of the languages here,
from a separate codebase, by separate authors, with its own reading of
each grammar. It is not a proof of correctness — two implementations can
share a misconception — but a *disagreement* is a fact that neither
implementation's author can talk away, and that is what this produces.

Usage::

    python3 tools/complexity_oracle.py <path> [<path> ...]

For every declaration both tools find, it reports the two complexity
numbers and the difference. What matters is not the total but the
**pattern** of disagreement: a language where we are consistently lower
is a language whose keywords we are missing, which is the exact defect
Fortran had before 1.6.0 and PHP had before 2.11.0.

This tool answers one question and refuses the neighbouring one: it does
not say which implementation is right. A divergence sends a reader to the
grammar, which is the only authority either tool answers to.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maintainability_audit.config import DEFAULT_CONFIG  # noqa: E402
from maintainability_audit.declarations import (  # noqa: E402
    DECLARATION_SUFFIXES,
    detect_functions,
)

THRESHOLDS = DEFAULT_CONFIG["thresholds"]


def _ours(path: Path) -> dict[str, int]:
    """Our complexity per declaration, keyed by the name we report."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    found = {}
    for metric in detect_functions(path.parent, path, lines, THRESHOLDS):
        # Our qualified names carry the owner (`Store::get`); lizard
        # reports its own qualification. Compare on the last segment,
        # which both agree on, and on the start line where available.
        found[metric.start_line] = metric.complexity
    return found


def _theirs(path: Path) -> dict[str, int]:
    """lizard's cyclomatic complexity per function, keyed by start line."""
    import lizard

    try:
        analysis = lizard.analyze_file(str(path))
    except Exception:                                    # noqa: BLE001
        return {}
    return {f.start_line: f.cyclomatic_complexity for f in analysis.function_list}


def compare(path: Path) -> list[tuple[int, int, int]]:
    """(line, ours, theirs) for declarations both tools located."""
    ours, theirs = _ours(path), _theirs(path)
    shared = sorted(set(ours) & set(theirs))
    return [(line, ours[line], theirs[line]) for line in shared]


def _walk(roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        base = Path(root)
        if base.is_file():
            files.append(base)
            continue
        files += [
            path for path in base.rglob("*")
            if path.is_file() and path.suffix in DECLARATION_SUFFIXES
        ]
    return files


def _tally(files: list[Path]) -> tuple[dict, dict]:
    """Per-suffix comparisons, and how many files contributed each."""
    by_suffix: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    matched: dict[str, int] = defaultdict(int)
    for path in files:
        rows = compare(path)
        if rows:
            by_suffix[path.suffix] += rows
            matched[path.suffix] += 1
    return by_suffix, matched


def _report(by_suffix: dict, matched: dict) -> list[tuple[int, str, int, int]]:
    """Print the per-language table and return the disagreements."""
    print(f"{'suffix':8} {'files':>6} {'decls':>6} {'agree':>6} "
          f"{'we are lower':>13} {'we are higher':>14}")
    worst: list[tuple[int, str, int, int]] = []
    for suffix in sorted(by_suffix):
        rows = by_suffix[suffix]
        agree = sum(1 for _l, a, b in rows if a == b)
        lower = sum(1 for _l, a, b in rows if a < b)
        higher = sum(1 for _l, a, b in rows if a > b)
        print(f"{suffix:8} {matched[suffix]:6} {len(rows):6} {agree:6} "
              f"{lower:13} {higher:14}")
        worst += [(b - a, suffix, a, b) for _l, a, b in rows if a != b]
    return worst


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    by_suffix, matched = _tally(_walk(argv))
    if not by_suffix:
        print("no declaration was located by both tools")
        return 1

    worst = _report(by_suffix, matched)
    if worst:
        worst.sort(key=lambda row: -abs(row[0]))
        print("\nlargest disagreements (difference, suffix, ours, theirs):")
        for difference, suffix, ours, theirs in worst[:12]:
            print(f"  {difference:+4}  {suffix:8} ours={ours:<4} theirs={theirs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
