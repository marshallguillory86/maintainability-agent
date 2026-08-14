"""Each published promise, and the test that would catch it breaking — 7.3.

`docs/product-intent.md` publishes eight promises, each with a stated
falsifier: *"what would show this is false"*. That is the right shape —
a promise without a falsifier is marketing — but until now nothing
connected a promise to the code that keeps it. A promise enforced only
by intention is a promise that breaks quietly, and this project has
shipped exactly that failure in every other form: a name that drifted
from its measurement, a document that outlived its subject, a gate
chained so its result arrived too late to block anything.

So this file is the index. Every promise names the tests that enforce
it, and a promise with no enforcement fails the build rather than
sitting on a page looking reassuring.

It is deliberately not a second implementation of the checks. The tests
it points at already exist and are thorough; what did not exist was
anything noticing when a promise had no such test at all.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Promise -> the tests that would fail if it stopped being true. Names
# are checked against the suite, so a rename that orphans a promise is
# caught here rather than discovered when somebody relies on it.
ENFORCEMENT: dict[str, tuple[str, ...]] = {
    "P1": (
        "test_two_runs_on_one_tree_agree",
        "test_two_analyzer_runs_on_one_tree_agree",
        "test_a_history_is_an_input_and_the_report_says_so",
    ),
    "P2": (
        "test_the_same_rubric_applies_at_every_repository_size",
        "test_filtering_never_changes_a_single_score",
        "test_scoring_never_imports_scanners_or_assembly",
    ),
    "P3": (
        "test_concealment_ordering_and_its_stated_limit",
        "test_unknown_evidence_blocks_the_top_grades",
    ),
    "P4": ("test_the_overall_is_the_weighted_mean_of_the_printed_categories",),
    "P5": (
        "test_the_prompt_forbids_widening_the_work_order",
        "test_no_part_of_the_prompt_re_issues_an_escalated_finding",
    ),
    "P6": (
        "test_the_pool_document_states_the_catalogs_own_counts",
        "test_the_readme_table_matches_the_stamped_self_audit",
        "test_the_curve_constant_still_does_its_job",
    ),
    "P7": (
        "test_a_repository_of_unread_source_gets_no_score",
        "test_a_score_is_never_computed_from_a_minority_of_the_source",
        "test_one_scan_carries_no_trajectory",
    ),
    "P8": (
        "test_the_built_in_detectors_appear_in_the_coverage_record",
        "test_a_python_only_tool_covers_nothing_for_cpp",
        "test_a_concern_no_tool_reads_for_a_language_is_named_as_a_gap",
        "test_live_surfaces_do_not_claim_analyzers_leave_the_estimate_alone",
        "test_scored_measurements_name_the_estimate_source",
    ),
}


def _published_promises() -> set[str]:
    text = (ROOT / "docs" / "product-intent.md").read_text(encoding="utf-8")
    return set(re.findall(r"^\| (P\d) \|", text, re.M))


def _all_test_names() -> set[str]:
    names: set[str] = set()
    for path in (ROOT / "tests").glob("test_*.py"):
        names |= set(re.findall(r"^def (test_\w+)", path.read_text(encoding="utf-8"), re.M))
    return names


def test_every_published_promise_names_its_enforcement() -> None:
    """A promise nothing tests is a sentence, not a guarantee."""
    published = _published_promises()

    assert published, "no promises found in product-intent.md"
    unenforced = sorted(published - set(ENFORCEMENT))
    assert not unenforced, (
        f"promises published with no enforcement listed: {unenforced}"
    )
    orphaned = sorted(set(ENFORCEMENT) - published)
    assert not orphaned, (
        f"enforcement listed for promises no longer published: {orphaned}"
    )


@pytest.mark.parametrize("promise", sorted(ENFORCEMENT))
def test_the_named_enforcement_actually_exists(promise: str) -> None:
    """The index is only useful if its references resolve.

    A renamed test silently orphans the promise it was keeping, and the
    index would go on asserting coverage that no longer exists — the
    same shape as a document outliving its subject.
    """
    names = _all_test_names()
    missing = sorted(set(ENFORCEMENT[promise]) - names)

    assert not missing, f"{promise} names tests that do not exist: {missing}"
