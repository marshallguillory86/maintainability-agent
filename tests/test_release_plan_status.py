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
    assert "0.1" not in open_row
    assert "0.5" not in open_row


def test_standing_table_names_the_tagged_release() -> None:
    table = _standing_table()
    assert "0.7.0" in table
    assert "0.6.1" not in table
    assert "unreleased" not in table.lower()


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


# ---------------------------------------------------------------------
# The class: a task marked Shipped may not be called open anywhere else
# ---------------------------------------------------------------------
#
# 7.2's defect runs in both directions. The famous half is prose
# describing an unimplemented component as present; the inverse — 2.5c
# shipped while the register still said "deferred to 1.0", 2.7 shipped
# while the standing table said "still has 2.7 open" — leaves a reader
# not looking for a feature that is right there, and it survives review
# because nobody proofreads for false modesty.

DECISIONS = Path(__file__).parents[1] / "docs" / "decisions.md"

_OPENNESS = re.compile(
    r"(?:\b(?P<id_first>\d\.\d[a-z]?)\b[^.\n|]{0,80}?\b(?:deferred|remains? open|still open|is open)\b"
    r"|\b(?:still has|retains)\b[^.\n|]{0,40}?\b(?P<id_second>\d\.\d[a-z]?)\b)",
    re.I,
)


def _shipped_task_ids() -> set[str]:
    """Task ids whose exit-condition cell opens with **Shipped.**"""
    text = RELEASE_PLAN.read_text(encoding="utf-8")
    return {
        match.group(1)
        for match in re.finditer(
            r"^\| (\d\.\d[a-z]?) \|[^|]*\|\s*\*\*Shipped\b", text, re.M
        )
    }


def test_no_shipped_task_is_still_called_open_or_deferred() -> None:
    """Cross-checked against the plan's own Shipped markers, so the rule
    needs no hand-kept list and covers the next task to ship."""
    shipped = _shipped_task_ids()
    assert shipped, "no task rows are marked Shipped; the parser has drifted"

    offenders = []
    for path in (RELEASE_PLAN, DECISIONS):
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for match in _OPENNESS.finditer(line):
                task = match.group("id_first") or match.group("id_second")
                if task in shipped:
                    offenders.append(f"{path.name}:{line_number}: {match.group(0)!r}")

    assert not offenders, (
        "shipped work described as open or deferred (the inverse of 7.2's "
        "defect, same class):\n  " + "\n  ".join(offenders)
    )


def test_the_band_matrix_is_not_listed_as_open_exit_work() -> None:
    """3.2 shipped. Calling it open work after the wire is 7.2 inverted."""
    table = _standing_table()
    for line in table.splitlines():
        if "band matrix" not in line.lower() and "3.2" not in line:
            continue
        lowered = line.lower()
        assert "shipped" in lowered or "done" in lowered, (
            f"the standing table still treats 3.2 as unfinished: {line!r}"
        )
        assert "open and queued" not in lowered


def test_phase_three_records_the_band_matrix_as_shipped() -> None:
    """The 3.2 row must name the tests that prove CCN 16 ≠ 45."""
    text = RELEASE_PLAN.read_text(encoding="utf-8")
    match = re.search(r"^\| 3\.2 \| (.+) \|", text, re.M)
    assert match, "release-plan is missing the 3.2 row"
    cell = match.group(1)
    assert "Shipped" in cell, f"3.2 is not marked shipped: {cell!r}"
    assert "test_band_pressures" in cell, (
        "3.2 shipped without naming the invariant-13 test"
    )
