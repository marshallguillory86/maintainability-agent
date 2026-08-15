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

from maintainability_audit._calibration import CALIBRATION_C
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
    assert f"{CALIBRATION_C}" in text
    assert str(REPORT_SCHEMA_VERSION) in text
    assert "baseline" in lowered


def test_the_guide_does_not_reopen_the_0_7_baseline_break() -> None:
    """Identity and schema 3 already shipped in 0.7. Do not send people there twice."""
    text = GUIDE.read_text(encoding="utf-8")
    assert "Do not regenerate a 0.7 baseline" in text
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
    assert "never installs" in text.lower(), "the line that may not blur has to stay stated"


def test_the_index_and_readme_point_at_the_1_0_guide() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "docs/migration-1.0.md" in readme or "migration-1.0.md" in readme
    assert "migration-1.0.md" in index
