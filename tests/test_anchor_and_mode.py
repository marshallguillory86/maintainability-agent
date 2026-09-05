"""Two states the shipped code has never been in, and one it is in daily.

Both halves here exist because a branch nobody executes is a claim nobody
has checked.

**When the corpus finally holds every parsed language**, the disclosure
has to *disappear* — not render as an empty caveat, a stray blank line,
or the word "and" on its own. That day is a recalibration away and it is
the state none of the skins has ever been rendered in.

**When a replacement file already exists**, its mode has to survive. The
write path hardcoded `0o644` under a comment claiming to "match the old
mode", so a config a user had restricted to 0600 was widened to
world-readable by the next write, silently, every time.
"""

from __future__ import annotations

import os
from pathlib import Path

from maintainability_audit import _evidence_view as view
from maintainability_audit._anchor import unanchored_sentence
from maintainability_audit._html_view import _unanchored_html
from maintainability_audit._safe_write import _mode_for, write_bounded
from maintainability_audit.renderers import summary_table

_ANCHORED = {"reference": {"corpus_note": "everything is in the corpus"}}

_SUMMARY = {
    "files_scanned": 10, "file_warnings": 0, "file_failures": 0,
    "function_warnings": 0, "function_failures": 0, "duplicate_blocks": 0,
    "risk_findings": 0, "hard_gate_failures": 0,
}


def _score(**over: object) -> dict:
    base = {
        "maintainability_estimate": 4.0, "maintainability_range": [4.0, 4.0],
        "verified_grade": "B", "verified_grade_blockers": [],
        "evidence_status": {"status": "complete", "profile": "default-v1", "reasons": []},
        "analyzer_scored_dimensions": [],
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# The day the corpus holds everything
# ---------------------------------------------------------------------------

def test_a_fully_anchored_run_prints_no_caveat_anywhere() -> None:
    """Not an empty one, and not a stray blank line — nothing at all."""
    score = _score(**_ANCHORED)

    assert view.unanchored_languages(score) == ()
    assert view.unanchored_caveat(score) == []
    assert _unanchored_html(score) == []


def test_a_report_with_no_reference_block_is_not_a_disclosure(tmp_path: Path) -> None:
    """A score that predates `reference` must not crash a skin or invent a
    caveat. Older stored reports are read by the HTML and markdown skins."""
    score = _score()

    assert view.unanchored_languages(score) == ()
    assert view.unanchored_caveat(score) == []


def test_the_markdown_summary_ends_at_the_table_when_nothing_is_unanchored() -> None:
    """The caveat is appended to the summary rows, so an empty one would
    leave a trailing blank line under the table in every report."""
    rows = summary_table(_SUMMARY, _score(**_ANCHORED), False)

    assert rows[-1].startswith("| Hard gate failures |")


def test_the_sentence_is_empty_when_the_corpus_holds_everything(monkeypatch) -> None:
    """`unanchored_sentence` composes the corpus note. With nothing to
    name it must contribute nothing, or the note reads "... . Fortran
    entered at a lower star threshold" with a hole in it."""
    monkeypatch.setattr("maintainability_audit._anchor.UNANCHORED_LANGUAGES", ())

    assert unanchored_sentence() == ""


# ---------------------------------------------------------------------------
# The mode a replacement carries
# ---------------------------------------------------------------------------

def test_replacing_a_restricted_file_does_not_widen_it(tmp_path: Path) -> None:
    """The defect behind SonarCloud's S2612 hotspot on the old literal.

    A user who restricts their config to 0600 means it. The write path
    set 0644 unconditionally, so the next audit handed it back
    world-readable — and the comment above the call claimed to be
    matching the old mode while doing the opposite.
    """
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "maintainability-agent.json"
    target.write_text("{}", encoding="utf-8")
    target.chmod(0o600)

    write_bounded(root, target, '{"analyzers": {"run": true}}')

    assert target.stat().st_mode & 0o777 == 0o600, (
        "replacing the file widened its permissions"
    )


def test_a_new_file_follows_the_umask_rather_than_a_number_we_chose(
    tmp_path: Path,
) -> None:
    """What `open()` would have produced, so a restrictive umask is honoured."""
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "fresh.json"

    write_bounded(root, target, "{}")

    umask = os.umask(0)
    os.umask(umask)
    assert target.stat().st_mode & 0o777 == 0o666 & ~umask


def test_the_mode_helper_reads_an_existing_file_and_falls_back(tmp_path: Path) -> None:
    existing = tmp_path / "there.json"
    existing.write_text("{}", encoding="utf-8")
    existing.chmod(0o640)

    assert _mode_for(existing) == 0o640

    umask = os.umask(0)
    os.umask(umask)
    assert _mode_for(tmp_path / "absent.json") == 0o666 & ~umask
