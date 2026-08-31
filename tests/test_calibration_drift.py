"""The guard the corpus tests could not be: it re-runs a live scanner.

``test_calibration_corpus`` re-derives the constants from the stored
measurements, but nothing there re-runs a scanner — so the day a
scanner's counting changes, every score shifts while the frozen
references do not, and the corpus tests stay green because they replay
the stored numbers on both sides. That is exactly how the duplication
reference came to be ~14x too high: plan-81dc6870 Class 4 collapsed a
clone's overlapping windows into one clone-group finding, and the
2026-08-14 corpus was never re-measured against it.

This pins the built-in duplication scanner's counting on a controlled
clone, so a change like Class 4 fails a test that names the re-run rather
than drifting into production in silence.
"""
from __future__ import annotations

from pathlib import Path

from maintainability_audit.duplication import duplicate_blocks
from maintainability_audit.source import SourceIndex


def test_a_scanner_counting_change_is_caught_before_it_rots_the_calibration(
    tmp_path: Path,
) -> None:
    """One 40-line clone across three files is one clone group of three.

    A change here means the built-in duplication scanner's counting moved,
    so every duplication score is now measured against a stale reference:
    re-run ``tools/calibration/measure.py`` and re-derive ``_calibration``.
    """
    body = "\n".join(f"    x{i} = combine(x{i - 1}, {i})" for i in range(1, 40))
    clone = f"def process(seed):\n    x0 = seed\n{body}\n    return x39\n"
    files = []
    for stem in ("alpha", "beta", "gamma"):
        path = tmp_path / f"{stem}.py"
        path.write_text(
            f"{clone}\n\ndef only_{stem}():\n    return {stem!r}\n", encoding="utf-8")
        files.append(path)

    groups = duplicate_blocks(tmp_path, files, 8, SourceIndex())
    assert len(groups) == 1, (
        f"one 40-line clone across three files reported {len(groups)} "
        "duplication findings, not one clone group. The built-in scanner's "
        "counting changed; every duplication score is now measured against a "
        "stale reference. Re-run tools/calibration/measure.py and re-derive "
        "_calibration.py (see docs/standard.md)."
    )
    assert groups[0]["count"] == 3, (
        "the clone group's occurrence count changed; recalibration is due"
    )
