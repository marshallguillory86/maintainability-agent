"""Guard the release-plan banner against known status drift."""

import re
from pathlib import Path


RELEASE_PLAN = Path(__file__).parents[1] / "docs" / "release-plan.md"


def _standing_table() -> str:
    text = RELEASE_PLAN.read_text(encoding="utf-8")
    section = text.split("## Where this actually stands", maxsplit=1)[1].split(
        "Two things are deliberately open", maxsplit=1
    )[0]
    return section


def test_release_plan_does_not_claim_phases_zero_through_five_are_finished() -> None:
    text = RELEASE_PLAN.read_text(encoding="utf-8")

    stale_claims = (
        r"phases?\s+complete\s*\|\s*0\s*[-\u2013\u2014]\s*5",
        r"phases?\s+0\s+(?:through|to)\s+5\s+(?:are\s+)?(?:built|complete|done)",
    )
    for pattern in stale_claims:
        assert re.search(pattern, text, flags=re.IGNORECASE) is None


def test_standing_table_does_not_list_shipped_phase_two_tests_as_open() -> None:
    table = _standing_table()
    open_row = next(
        line for line in table.splitlines() if "Known open exit conditions" in line
    )

    assert "2.6" not in open_row
    assert "2.8" not in open_row
    assert "2.5c" not in open_row


def test_release_plan_does_not_claim_all_accepted_adrs_are_implemented() -> None:
    text = RELEASE_PLAN.read_text(encoding="utf-8")

    assert re.search(
        r"ADRs\s+accepted\s+and\s+(?:\*\*)?not implemented(?:\*\*)?\s*\|\s*none",
        text,
        flags=re.IGNORECASE,
    ) is None


def test_release_plan_does_not_list_adr_008_as_implemented_without_a_gap() -> None:
    for line in RELEASE_PLAN.read_text(encoding="utf-8").splitlines():
        normalized = line.replace("**", "").lower()
        if "adrs accepted and implemented" not in normalized or "008" not in normalized:
            continue

        assert re.search(
            r"except|partial|remaining|gap|band matrix|binary rates",
            normalized,
        ), "ADR 008 must not be listed as implemented without its remaining gap"
