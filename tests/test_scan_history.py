"""An append-only record per scan, and the gate that keeps a series honest.

ADR 009 §2 and §4. These two land together on purpose: the comparability
rule decides what a record has to contain, and building the record first
and bolting the gate on afterwards produces a history that cannot answer
the question it exists for.

**Why the gate is the load-bearing half.** Yesterday this repository's
own tooling changed under it several times in one day — a line-count
column corrected, generated code excluded, unread source discovered. The
same fourteen repositories scored differently at 09:00 and 17:00, and
every one of those changes was a fix. A trend line drawn through those
runs would be a chart of my bug fixes presented as a statement about
someone's code. That is ADR 006's defect arriving through the time
dimension, and it is worse there, because a wrong snapshot is obviously
a snapshot while a wrong trend looks like knowledge.

So two scans are comparable only when the rubric, the analyzer coverage
and the scope all match. Where they differ the series is **segmented at
that boundary** and the report says why. A silently spliced series is
worse than none.

**Append-only means no run rewrites another.** A history a later scan can
edit is a history that can be made to say anything, and the first thing
anyone would want to edit is the run that made their number look bad.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._scan_history import (
    COMPARABILITY_FIELDS,
    HISTORY_SCHEMA_VERSION,
    ScanRecord,
    append_scan,
    comparability_key,
    read_history,
    segments,
)


def _repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _record(**overrides: object) -> ScanRecord:
    """A record with everything the gate reads, varied per test."""
    base: dict[str, object] = {
        "recorded_at": "2026-08-13T09:00:00Z",
        "commit": "a" * 40,
        "branch": "main",
        "scope": "full",
        "rubric_version": "0.7.0",
        "calibration": 2.6279,
        "thresholds_digest": "t-abc",
        "analyzers": ("lizard", "ruff"),
        "scored_languages": ("Python",),
        "estimate": 4.2,
        "populations": {"files_scanned": 100, "declarations_scanned": 400},
        "fingerprints": ("f1", "f2"),
    }
    base.update(overrides)
    return ScanRecord(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------
# 5.1 — the record
# --------------------------------------------------------------------


def test_a_scan_appends_one_line_and_rewrites_nothing(tmp_path: Path) -> None:
    """Append-only, enforced by reading the bytes back.

    A history a later run can edit is a history that can be made to say
    anything, and the first line anyone would want to edit is the run
    that made their number look bad.
    """
    history = _repo(tmp_path / "r") / ".maintainability" / "history.jsonl"

    append_scan(history, _record(commit="a" * 40, estimate=4.2))
    first = history.read_bytes()
    append_scan(history, _record(commit="b" * 40, estimate=4.4))
    second = history.read_bytes()

    assert second.startswith(first), "the earlier record was rewritten"
    assert len(read_history(history)) == 2
    assert [r.estimate for r in read_history(history)] == [4.2, 4.4]


def test_the_record_carries_its_own_schema_version(tmp_path: Path) -> None:
    """Versioned separately from the report.

    The report contract and the history format change for different
    reasons and at different times; one version number for both would
    force a break in either to break the other.
    """
    history = tmp_path / "history.jsonl"
    append_scan(history, _record())

    line = json.loads(history.read_text(encoding="utf-8").splitlines()[0])

    assert line["history_schema_version"] == HISTORY_SCHEMA_VERSION
    assert "schema_version" not in line, "the report's version is a different number"


def test_a_record_retains_populations_not_only_the_score(tmp_path: Path) -> None:
    """The score alone cannot answer *why* anything moved.

    A run that drops from 4.4 to 4.0 because the repository doubled in
    size is a different event from one that drops because the same code
    got worse, and only the populations distinguish them.
    """
    history = tmp_path / "history.jsonl"
    append_scan(history, _record())

    stored = read_history(history)[0]

    assert stored.populations["declarations_scanned"] == 400
    assert stored.fingerprints == ("f1", "f2"), "identity is retained for recurrence"


def test_an_unreadable_line_does_not_destroy_the_history(tmp_path: Path) -> None:
    """One corrupt line loses one scan, never the series.

    A history that refuses to load because something truncated a write
    is a history that gets deleted by whoever hits it first.
    """
    history = tmp_path / "history.jsonl"
    append_scan(history, _record(commit="a" * 40))
    with history.open("a", encoding="utf-8") as handle:
        handle.write("{not json at all\n")
    append_scan(history, _record(commit="c" * 40))

    records = read_history(history)

    assert [r.commit for r in records] == ["a" * 40, "c" * 40]


# --------------------------------------------------------------------
# 5.2 — comparability
# --------------------------------------------------------------------


@pytest.mark.parametrize("field", [
    "rubric_version", "calibration", "thresholds_digest", "analyzers",
    "scored_languages", "scope",
])
def test_every_field_that_changes_meaning_breaks_comparability(field: str) -> None:
    """Each of these changes what a score *means*, so a series cannot cross it.

    Swept rather than spot-checked: the failure mode is someone adding a
    seventh input to the score and not adding it here, at which point
    trends silently start spanning a change in the instrument.
    """
    changed = {
        "rubric_version": "0.8.0",
        "calibration": 2.7,
        "thresholds_digest": "t-xyz",
        "analyzers": ("lizard",),
        "scored_languages": ("Python", "TypeScript"),
        "scope": "changed-only",
    }[field]

    assert comparability_key(_record()) != comparability_key(_record(**{field: changed}))


def test_things_that_do_not_change_meaning_keep_a_series_intact() -> None:
    """The gate must not fire on ordinary progress.

    A new commit, a later timestamp, a different branch and a moved score
    are what a trend is *made of*. A gate that segmented on those would
    withhold every trend that ever existed.
    """
    baseline = comparability_key(_record())

    for field, value in (
        ("commit", "f" * 40), ("recorded_at", "2026-09-01T00:00:00Z"),
        ("branch", "release"), ("estimate", 3.1),
        ("populations", {"files_scanned": 900}), ("fingerprints", ("f9",)),
    ):
        assert comparability_key(_record(**{field: value})) == baseline, (
            f"{field} changed the comparability key; a trend can never span it"
        )


def test_the_analyzer_set_is_compared_as_a_set_not_a_sequence() -> None:
    """Tool order is an artifact of iteration, not a change in coverage."""
    assert comparability_key(_record(analyzers=("ruff", "lizard"))) == comparability_key(
        _record(analyzers=("lizard", "ruff")))


def test_a_series_is_segmented_at_the_boundary_rather_than_spliced() -> None:
    """The whole point. Yesterday's runs would have produced this shape.

    Three scans on one instrument, then the instrument changed, then two
    more. The honest answer is two series with the break named — not one
    line through five points that reads as a five-scan trend.
    """
    before = [_record(commit=str(n) * 40, estimate=4.0 + n / 10) for n in range(3)]
    after = [_record(commit=str(n) * 40, estimate=3.0 + n / 10,
                     analyzers=("lizard", "ruff", "vulture")) for n in range(3, 5)]

    found = segments(before + after)

    assert len(found) == 2, "a coverage change must split the series"
    assert [len(s.records) for s in found] == [3, 2]
    assert "analyzers" in found[1].break_reason, (
        f"the break must name what changed; said: {found[1].break_reason!r}"
    )
    assert found[0].break_reason == "", "the first segment breaks from nothing"


def test_a_single_scan_is_a_segment_and_not_a_trend() -> None:
    """One point is not a direction, and must not be reported as one."""
    found = segments([_record()])

    assert len(found) == 1
    assert not found[0].comparable_trend, "a trend needs at least two comparable scans"


def test_an_empty_history_yields_no_segments_rather_than_an_error() -> None:
    """A first run has no history, which is a state and not a failure."""
    assert segments([]) == []


# --------------------------------------------------------------------
# Wiring: recording is asked for, reading is not
# --------------------------------------------------------------------


def _tree(root: Path) -> Path:
    _repo(root)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for n in range(60):
        (root / "pkg").mkdir(exist_ok=True)
        (root / "pkg" / f"mod{n}.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)
    return root


def test_an_audit_writes_no_history_unless_asked(tmp_path: Path) -> None:
    """Every write in this tool is an explicit flag, and this is a write.

    `--write-baseline`, `--sarif-output`, `--output`: nothing touches
    disk unasked. A scan that silently created a file inside someone's
    repository would break that convention for a feature they may not
    want, and the file is one they would then have to decide whether to
    commit.
    """
    from maintainability_audit.cli import main

    root = _tree(tmp_path / "quiet")

    assert main(["--root", str(root), "--output", str(tmp_path / "r.md")]) == 0
    assert not (root / ".maintainability").exists(), "an unasked-for file appeared"


def test_recording_appends_one_scan(tmp_path: Path) -> None:
    """`--record-history` is the opt-in, and it opts in permanently.

    Once the file exists, later runs read it without being asked —
    reading has no side effect, and a trend nobody is shown is a trend
    nobody benefits from.
    """
    from maintainability_audit.cli import main

    root = _tree(tmp_path / "recorded")
    history = root / ".maintainability" / "history.jsonl"

    main(["--root", str(root), "--output", str(tmp_path / "a.md"), "--record-history"])
    main(["--root", str(root), "--output", str(tmp_path / "b.md"), "--record-history"])

    records = read_history(history)
    assert len(records) == 2
    assert records[0].scope == "full"
    assert records[0].populations["files_scanned"] >= 60
    assert records[0].rubric_version, "the rubric that produced it is recorded"


def test_a_recorded_scan_carries_what_the_gate_needs(tmp_path: Path) -> None:
    """Every comparability field, populated from the real run.

    A record missing one of them cannot be compared and silently joins a
    series it does not belong to.
    """
    from maintainability_audit.cli import main

    root = _tree(tmp_path / "complete")
    main(["--root", str(root), "--output", str(tmp_path / "a.md"), "--record-history"])

    record = read_history(root / ".maintainability" / "history.jsonl")[0]

    for name in COMPARABILITY_FIELDS:
        value = getattr(record, name)
        assert value not in (None, ""), f"{name} was not recorded"


def test_a_changed_only_scan_does_not_join_a_whole_repository_series(
    tmp_path: Path,
) -> None:
    """The case that will happen constantly: CI diffs beside local full scans.

    Both are legitimate scans and both belong in the history. Joining
    them into one trend would compare a two-file diff against a whole
    repository, which is the scope error ADR 005 already refuses in the
    snapshot — arriving through the time dimension.
    """
    from maintainability_audit.cli import main

    root = _tree(tmp_path / "mixed")
    history = root / ".maintainability" / "history.jsonl"

    main(["--root", str(root), "--output", str(tmp_path / "a.md"), "--record-history"])
    main(["--root", str(root), "--output", str(tmp_path / "b.md"), "--record-history",
          "--changed-only", "HEAD"])

    found = segments(read_history(history))

    assert len(found) == 2, "a scope change must split the series"
    assert "scope" in found[1].break_reason


def test_a_record_identifies_the_commit_it_describes(tmp_path: Path) -> None:
    """Without it the history is a list of scores with no anchor.

    The first wiring stored `report["git_commit"]`, which the report has
    never had — so every record carried an empty string and nothing
    noticed, because no test asked. Recurrence work lands on top of this:
    "cleared, then returned, in these commits" needs the commits.
    """
    from maintainability_audit.cli import main

    root = _tree(tmp_path / "anchored")
    expected = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()

    main(["--root", str(root), "--output", str(tmp_path / "a.md"), "--record-history"])
    record = read_history(root / ".maintainability" / "history.jsonl")[0]

    assert record.commit == expected
    assert record.branch, "and the branch it was on"


def test_every_sequence_field_survives_the_round_trip(tmp_path: Path) -> None:
    """JSON has one list type, so a missed field returns as a list.

    `targeted` was added and not converted, so a stored record stopped
    comparing equal to a freshly built one — silently, because a list
    and a tuple of the same items look identical in most assertions.
    Swept over the dataclass so the next sequence field cannot be
    forgotten the same way.
    """
    from dataclasses import fields

    history = tmp_path / "roundtrip.jsonl"
    original = _record(targeted=("t1",))
    append_scan(history, original)

    restored = read_history(history)[0]

    assert restored == original, "the record did not survive its own storage"
    for spec in fields(ScanRecord):
        value = getattr(restored, spec.name)
        assert not isinstance(value, list), (
            f"{spec.name} came back as a list; it must be converted in read_history"
        )
