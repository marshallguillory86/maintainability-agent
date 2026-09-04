"""8.1 + 8.2: what a scan stores, and when a scan is stored at all.

Schema 2 added chart fields; schema 3 adds ADR 009 structured identities.
The chart fields still exist because the charts ADR 011 requires cannot be drawn
from schema 1: a record holding only the rollup estimate can plot one
line, and the pillar and practice series — the two ADR 007 refuses to
average — were never written down. A trend you did not store is a trend
you cannot show.

8.2 exists because `--record-history` is a flag people forget, and a
forgotten flag was silently costing the one scan the next trend needed.
The file's *existence* is the user's standing answer: once it is there,
a successful scan appends.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# One fixture repo for the whole Phase-8 suite; the second copy of
# this builder tripped the project's own duplicate-block gate once
# already.
from test_first_run_prompt import _repo

from maintainability_audit._recurrence import recurrence
from maintainability_audit._scan_history import (
    DEFAULT_HISTORY_PATH,
    HISTORY_SCHEMA_VERSION,
    ScanRecord,
    Segment,
    read_history,
    record_of,
)
from maintainability_audit.cli import main
from maintainability_audit.config import VERSION, load_config
from maintainability_audit.report import build_report

# A schema-1 line exactly as 0.7.0 wrote it. Loading it is a promise to
# every existing history file.
SCHEMA_1_LINE = json.dumps({
    "history_schema_version": 1,
    "recorded_at": "2026-08-10T10:00:00Z", "commit": "a" * 40, "branch": "main",
    "scope": "full", "rubric_version": "0.7.0", "calibration": 2.6279,
    "thresholds_digest": "abc123", "analyzers": [], "scored_languages": ["Python"],
    "estimate": 4.1, "range_low": 4.0, "range_high": 4.2,
    "populations": {"files_scanned": 50}, "fingerprints": [], "backfilled": False,
    "targeted": [],
}, sort_keys=True)


def _record(tmp_path: Path) -> ScanRecord:
    config = load_config(None)
    root = _repo(tmp_path)
    body = "\n".join(f"    value_{line} = {line}" for line in range(90))
    (root / "hot.py").write_text(f"def huge():\n{body}\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "hot.py"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "finding"],
        check=True,
    )
    report = build_report(root, config)
    return record_of(report, config, VERSION, 2.2658, ())


def test_new_writes_carry_structured_identities() -> None:
    """Schema 3 or later, which is a floor rather than a version.

    This asserted `== 3` and broke when schema 4 added the transformation
    label — a test whose subject is the identity contract failing over a
    field it does not care about. What it defends is that new lines are
    never the label-only schema 1 or 2 records; a later schema keeps that
    property by construction, and the current number is pinned where it
    belongs, in `test_run_comparison.test_the_label_round_trips_through_
    the_written_line`.

    Covers existing behaviour: the identity contract shipped with schema 3
    and is untouched here. This change only renames the guard and loosens
    an assertion that was pinning an unrelated number, so it cannot fail
    against a base where the same property already held.
    """
    assert HISTORY_SCHEMA_VERSION >= 3, (
        "new lines must distinguish structured finding identities from the "
        "label-only schema 1 and 2 records"
    )


def test_a_new_record_stores_what_the_charts_need(tmp_path: Path) -> None:
    """categories, aspects, pillars, practice_level, evidence_status.

    Each is copied from what the report *published*, not recomputed —
    a record that recomputes is a second scorer.
    """
    record = _record(tmp_path)
    payload = json.loads(record.as_line())

    assert payload["history_schema_version"] >= 3
    assert payload["identities"], "schema 3 must retain matcher inputs beside labels"
    assert set(payload["identities"][0]) == {
        "kind", "path", "name", "ordinal", "body_digest", "fingerprint",
    }
    assert payload["categories"], "no categories stored; the category bars have no data"
    assert payload["aspects"], "no aspects stored"
    assert payload["pillars"], "no pillar series stored; the pillar chart has no data"
    assert isinstance(payload["practice_level"], int), (
        "no practice level stored; the maturity series has no data"
    )
    assert payload["evidence_status"], "no evidence status stored"


def test_pillars_and_practice_are_two_series_never_one(tmp_path: Path) -> None:
    """ADR 007: condition and practice answer different questions.

    The record must carry them as separate fields, and no stored field
    may be an average of the two — there is nothing a combined number
    could mean.
    """
    payload = json.loads(_record(tmp_path).as_line())

    assert "pillars" in payload and "practice_level" in payload
    pillar_values = [v for v in payload["pillars"].values() if v is not None]
    non_series_numbers = {
        "history_schema_version", "calibration", "estimate", "range_low", "range_high",
    }
    for name, value in payload.items():
        if (
            name in {"pillars", "practice_level", *non_series_numbers}
            or not isinstance(value, (int, float))
        ):
            continue
        for pillar_value in pillar_values:
            blended = (pillar_value + payload["practice_level"]) / 2
            assert value != pytest.approx(blended, abs=1e-9) or value in (
                payload["practice_level"],
            ), f"{name} looks like an average of condition and practice"


def test_a_schema_one_line_still_loads(tmp_path: Path) -> None:
    """Every existing history file keeps working, missing fields default."""
    path = tmp_path / "history.jsonl"
    path.write_text(SCHEMA_1_LINE + "\n", encoding="utf-8")

    records = read_history(path)

    assert len(records) == 1
    record = records[0]
    assert record.estimate == 4.1
    assert record.categories == {}, "a schema-1 record has no categories; default, don't invent"
    assert record.pillars == {}
    assert record.practice_level is None
    assert record.evidence_status == ""


def test_schema_two_records_still_load_and_match_by_label_equality(tmp_path: Path) -> None:
    """Old records have no digest or rename evidence; strings are all they know."""
    base = json.loads(SCHEMA_1_LINE)
    lines = []
    for index, fingerprints in enumerate((["finding:a"], [], ["finding:a"])):
        payload = {
            **base,
            "history_schema_version": 2,
            "commit": str(index) * 40,
            "fingerprints": fingerprints,
            "targeted": ["finding:a"] if index == 0 else [],
            "categories": {},
            "aspects": {},
            "pillars": {},
            "practice_level": None,
            "evidence_status": "",
        }
        lines.append(json.dumps(payload, sort_keys=True))
    path = tmp_path / "schema-2.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    records = read_history(path)

    assert all(not record.identities for record in records)
    assert recurrence(Segment(records=records))["finding:a"].returns == 1


def test_mixed_schema_files_load_in_order(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    root = _repo(tmp_path)
    config = load_config(None)
    new = record_of(build_report(root, config), config, VERSION, 2.2658, ())
    path.write_text(SCHEMA_1_LINE + "\n" + new.as_line() + "\n", encoding="utf-8")

    records = read_history(path)

    assert len(records) == 2
    assert records[0].practice_level is None and records[1].practice_level is not None


# --------------------------------------------------------------------
# 8.2 — the file's existence is the standing answer
# --------------------------------------------------------------------


def test_an_existing_history_gains_the_scan_without_the_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forgotten flag must not drop the current scan."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    root = _repo(tmp_path)
    out = tmp_path / "out.md"
    assert main(["--root", str(root), "--record-history", "--output", str(out)]) == 0
    assert len(read_history(root / DEFAULT_HISTORY_PATH)) == 1

    assert main(["--root", str(root), "--output", str(out)]) == 0

    assert len(read_history(root / DEFAULT_HISTORY_PATH)) == 2, (
        "the history file exists and a successful scan did not append; the "
        "forgotten flag dropped the scan"
    )


def test_no_history_and_no_tty_records_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CI without the flag keeps today's behaviour: no write nobody asked for."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    root = _repo(tmp_path)
    out = tmp_path / "out.md"

    assert main(["--root", str(root), "--output", str(out)]) == 0

    assert not (root / DEFAULT_HISTORY_PATH).exists()


def test_the_first_interactive_run_creates_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At a terminal the tool may start the series itself (8.2)."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    root = _repo(tmp_path)
    out = tmp_path / "out.md"

    assert main(["--root", str(root), "--output", str(out)]) == 0

    assert (root / DEFAULT_HISTORY_PATH).exists(), (
        "the first interactive run did not create the history file"
    )
    assert len(read_history(root / DEFAULT_HISTORY_PATH)) == 1
