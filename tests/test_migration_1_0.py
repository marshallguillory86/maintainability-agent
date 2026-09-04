"""7.4: the break from 0.7 has to be named, in one place, before 1.0.

0.7 already documented schema 3 and baseline v2. What landed after the
tag is a different incompatibility: ``--analyzers`` moves the point
estimate, and ``CALIBRATION_C`` moved 2.6279 → 2.2658. A hostile audit
found those facts in CHANGELOG Unreleased and nowhere a consumer would
look to migrate.

This file is the class lint. The guide may grow; it may not drop the
breaks, the old and new constants, or the index links.
"""
from __future__ import annotations

from pathlib import Path

from maintainability_audit.evidence import REPORT_SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "migration-1.0.md"


def test_the_1_0_migration_guide_exists() -> None:
    assert GUIDE.is_file(), "docs/migration-1.0.md is the 7.4 exit condition"


def test_the_guide_names_the_post_0_7_breaks() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "--analyzers" in text
    assert "point estimate" in lowered
    assert "2.6279" in text
    # The constant *this* transition moved to, not the one shipping today.
    # Asserting the live `CALIBRATION_C` was right while 1.0 was current and
    # became wrong the moment 2.0 re-fitted it: a guide describing the
    # 0.7 -> 1.0 step would have had to quote a number from a later release
    # to stay green, which is making history match the present. The live
    # constant is held by `migration-2.0.md`, whose job it is.
    assert "2.2658" in text
    assert str(REPORT_SCHEMA_VERSION) in text
    assert "baseline" in lowered


def test_the_guide_requires_regenerating_the_version_three_baseline() -> None:
    """The v3 identity records cannot be reconstructed from a v2 string list."""
    text = GUIDE.read_text(encoding="utf-8")
    baseline_row = next(
        line for line in text.splitlines() if line.startswith("| Baseline format |")
    )

    assert "version 3" in baseline_row.lower()
    assert "--write-baseline" in text
    assert "still **version 2**" not in text.lower()
    assert "do not regenerate a 0.7 baseline" not in text.lower()
    assert "schema_version" in text.lower() or "schema version" in text.lower()


def test_adr_006_states_the_environment_work_order_ships() -> None:
    """2.5c shipped. Flipped from asserting deferral, for the usual reason:
    an honesty lint that keeps insisting a shipped feature is absent is
    the same defect as prose claiming an absent one is present."""
    text = (ROOT / "docs" / "adr-006-analyzer-evidence.md").read_text(encoding="utf-8")
    assert "environment work order" in text.lower()
    assert "2.5c" in text
    assert "Not shipped (2.5c)" not in text, (
        "the ADR still defers the environment work order; report[\"environment_work_order\"] ships it"
    )
    # The blanket "never installs" was reconciled away (Grok UAT audit):
    # a user may enable acquisition, so the absolute was a user-visible
    # contradiction the moment they did. The line that may not blur is the
    # boundary that actually matters and must stay stated -- acquisition is
    # the user's to enable, and the audited tree's never.
    lowered = text.lower()
    assert "acquire_tools" in text and "cannot enable it" in lowered, (
        "the boundary that may not blur has to stay stated: a user may "
        "enable acquisition, an audited tree may not"
    )


def test_the_index_and_readme_point_at_the_1_0_guide() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "docs/migration-1.0.md" in readme or "migration-1.0.md" in readme
    assert "migration-1.0.md" in index
