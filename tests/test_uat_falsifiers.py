"""Independent UAT falsifiers for defects found after the v1.0 audit.

These are deliberately behavior-level checks.  The register has repeatedly
shown that a test aimed at a symbol, a sentence, or a partial fixture can stay
green while the user-visible defect returns by another path.

**Authorship, recorded because it is the point.** Written by Codex from the
findings alone, without reading the implementations, as the first run of the
split set 2026-08-26: Claude writes code, Codex writes tests and docs, Grok
audits. The register records `*Roles:*` from D90; these two attach to earlier
entries, so the data lives here instead of being backfilled into a document
whose value is that its claims are checkable.

    *Roles:* found=grok prompt=marshall fix=claude test=codex run=local

Mutation-verified after delivery, which is the check the author could not run
on itself: reverting each fix fails the matching test here. The first one
earned its keep immediately. The Claude-written test it replaces searched the
*whole rendered document* for ``"42"`` and so depended on this repository's
12-month commit count containing those digits -- red at 142 commits, green at
145, and due to return around 420 and 1042. It was a time bomb on a wall
clock rather than a check. The version below manufactures the collision, so it
holds at any commit count.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintainability_audit.config import ConfigUnreadable, load_config
from maintainability_audit.renderers import render_markdown


def test_a_class_row_hides_its_complexity_even_when_history_contains_that_number() -> None:
    """A class's summed method complexity must not leak into its own row.

    The former regression test searched the entire rendered document for
    ``"42"``.  Its fixture read this repository's live Git history, and a
    newly rendered history count of 142 made the test fail even though the
    class row was correct.  This reproduces that collision intentionally and
    examines the class row, the only place the claim applies.

    A wrong fix would be to suppress history whenever a class finding exists;
    the assertion that the unrelated history count is rendered prevents that.
    A wrong fix would also be to omit class findings entirely; the row lookup
    prevents that.
    """
    from test_declaration_grading import CLASS_HOTSPOT, flagged_class_report

    report = flagged_class_report()
    report["history"] = {
        "window": "12 months ago",
        "commits_in_window": 142,
        "commits_considered": 1,
        "files_changed": 0,
        "hotspots": [],
        "change_coupling": [],
        "qualifying_hotspots": 0,
        "code_coupling_pairs": 0,
        "multi_commit_files": 0,
        "single_author_files": 0,
    }
    report["function_hotspots"] = [CLASS_HOTSPOT]

    rendered = render_markdown(report)
    assert "142 commits inside the history window" in rendered
    class_row = next(line for line in rendered.splitlines() if "`ScanWorker`" in line)
    assert "(class)" in class_row
    assert "42" not in class_row


def test_config_refuses_non_string_extension_entries_before_scanning(tmp_path: Path) -> None:
    """A malformed extension list must be refused as configuration, not scanned.

    A user could write ``paths.include_extensions: [1]``.  The old shape
    check accepted the list, so every source suffix failed membership and the
    report described an empty scan rather than the malformed file.  Refusal at
    config loading is required: a later insufficient-evidence message is not
    a repair because it does not name the broken configuration field.

    A wrong fix would be to coerce numbers to strings or silently drop them;
    this requires the named ConfigUnreadable refusal and the indexed field in
    its message.  A wrong fix would be to defer the error to scanning; loading
    the config alone must fail.
    """
    config = tmp_path / "maintainability-agent.json"
    config.write_text(
        json.dumps({"paths": {"include_extensions": [1]}}), encoding="utf-8"
    )

    with pytest.raises(ConfigUnreadable, match=r"paths\.include_extensions\[0\]"):
        load_config(str(config))
