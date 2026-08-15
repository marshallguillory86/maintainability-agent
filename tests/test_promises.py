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
        # The network half: no HTTP client in src/, and no tool fetched
        # unless the operator opted in (test_network_disclosure).
        "test_no_module_imports_an_http_client",
        "test_no_module_opens_a_network_connection",
        "test_the_analysis_opens_no_sockets",
        "test_a_missing_node_tool_is_not_fetched_by_default",
        "test_analyze_does_not_build_fetching_argv_when_acquisition_is_off",
    ),
    "P2": (
        "test_the_same_rubric_applies_at_every_repository_size",
        "test_filtering_never_changes_a_single_score",
        "test_scoring_never_imports_scanners_or_assembly",
    ),
    "P3": (
        "test_concealment_ordering_and_its_stated_limit",
        "test_unknown_evidence_blocks_the_top_grades",
        "test_hiding_evidence_can_never_raise_the_grade",
        "test_withholding_any_single_input_cannot_raise_the_floor_or_the_grade",
    ),
    "P4": ("test_the_overall_is_the_weighted_mean_of_the_printed_categories",),
    "P5": (
        "test_the_prompt_forbids_widening_the_work_order",
        "test_no_part_of_the_prompt_re_issues_an_escalated_finding",
        "test_every_prompt_target_is_a_finding_the_audit_produced",
    ),
    "P6": (
        "test_the_pool_document_states_the_catalogs_own_counts",
        "test_the_readme_table_matches_the_stamped_self_audit",
        "test_the_curve_constant_still_does_its_job",
        "test_a_quoted_study_result_matches_an_approved_summary_verbatim",
    ),
    # Every entry asserts `maintainability_estimate is None` for a
    # repository the scan could not support a number for. The three
    # causes are the three the report can actually hit: source it never
    # read, a population below the calibration floor, and a scope-limited
    # run. `test_one_scan_carries_no_trajectory` was listed here and is
    # gone: a single scan having no trend is ADR 009's history contract,
    # not a refusal to publish an absurd number.
    "P7": (
        "test_a_repository_of_unread_source_gets_no_score",
        "test_a_score_is_never_computed_from_a_minority_of_the_source",
        "test_a_repository_below_the_root_floor_gets_no_score",
        "test_no_limited_scope_produces_a_score",
        "test_changed_only_through_the_cli_withholds_the_score",
    ),
    # `test_a_python_only_tool_covers_nothing_for_cpp` and
    # `test_a_concern_no_tool_reads_for_a_language_is_named_as_a_gap` are
    # deliberately absent. Both `pytest.skip("mypy did not run")` when the
    # tool is missing, so on a machine without it they prove nothing while
    # still reading as enforcement — a green index over a skipped body is
    # the same false assurance as a name that resolves to a test checking
    # something else.
    "P8": (
        "test_the_built_in_detectors_appear_in_the_coverage_record",
        "test_the_default_report_names_the_built_in_tier_as_the_estimate_source",
        "test_live_surfaces_do_not_claim_analyzers_leave_the_estimate_alone",
        "test_scored_measurements_name_the_estimate_source",
        "test_both_skins_state_the_estimate_source",
        "test_json_names_which_selected_analyzers_ran_and_did_not",
    ),
}


# File-like ticks in the prompt. Dimension names (`duplication`),
# verification commands (`ruff check`), and prose examples (`getattr`)
# are not locations. A path is a location.
_PROMPT_TICK = re.compile(r"`([^`]+)`")
_SOURCE_SUFFIXES = (
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".java", ".go",
    ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs",
)


def _fileish_path(token: str) -> str | None:
    core = token.split(":")[0].strip()
    if not core or " " in core or "://" in core:
        return None
    if any(core.endswith(suffix) for suffix in _SOURCE_SUFFIXES) or "/" in core:
        return core
    return None


def _paths_named_in_prompt(prompt: str) -> set[str]:
    """Every file path the prompt shows the agent, in any section."""
    return {
        path
        for tick in _PROMPT_TICK.findall(prompt)
        if (path := _fileish_path(tick))
    }


def _paths_the_audit_produced(report: dict) -> set[str]:
    """Every file path the audit actually located as a finding or target."""
    paths: set[str] = set()
    for key in (
        "work_order",
        "hard_gate_failures",
        "function_hotspots",
        "largest_files",
        "risk_findings",
        "dead_code",
        "near_duplicates",
        "design_review_candidates",
    ):
        for item in report.get(key) or []:
            if not isinstance(item, dict):
                continue
            if item.get("path"):
                paths.add(item["path"])
            duplicate = item.get("duplicate_of") or {}
            if isinstance(duplicate, dict) and duplicate.get("path"):
                paths.add(duplicate["path"])
    for block in report.get("duplicate_blocks") or []:
        for location in block.get("locations") or []:
            paths.add(str(location).split(":")[0])
    return paths


def test_every_prompt_target_is_a_finding_the_audit_produced(tmp_path: Path) -> None:
    """P5's falsifier: no path instruction without a corresponding finding.

    Numbered work-order `Location:` lines are not the whole prompt.
    Focus sections (hotspots, large files, risks, dupes, dead code) also
    name paths. A test that only parses the numbered list stays green
    while those sections invent work.
    """
    from test_determinism import _repo

    from maintainability_audit.config import load_config
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.report import build_report

    report = build_report(_repo(tmp_path / "bounded"), load_config(None))
    prompt = render_ai_prompt(report)
    named = _paths_named_in_prompt(prompt)
    produced = _paths_the_audit_produced(report)

    assert named, "the fixture produced no concrete path targets in the prompt"
    invented = sorted(named - produced)
    assert not invented, (
        "the prompt named file paths the audit did not produce: " + ", ".join(invented)
    )


def test_a_focus_section_path_outside_the_audit_fails_p5(tmp_path: Path) -> None:
    """The class: inventing a path in a focus section is enough to fail.

    The previous test can stay green if the fixture's hotspots happen to
    be a subset of the work order. This injects a path that exists only
    in the focus list.
    """
    from test_determinism import _repo

    from maintainability_audit.config import load_config
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.report import build_report

    report = build_report(_repo(tmp_path / "ghost"), load_config(None))
    report = {
        **report,
        "function_hotspots": [
            {
                "path": "ghost/never_audited.py",
                "name": "invented",
                "start_line": 1,
                "status": "fail",
                "lines": 40,
                "complexity": 12,
            },
            *list(report.get("function_hotspots") or []),
        ],
    }
    prompt = render_ai_prompt(report)
    # Strip the injected hotspot from the audit's produced set so the
    # focus section is the only place the path appears.
    produced = _paths_the_audit_produced(report) - {"ghost/never_audited.py"}
    named = _paths_named_in_prompt(prompt)
    assert "ghost/never_audited.py" in named, (
        "the focus section never emitted the injected path; the probe is dead"
    )
    assert "ghost/never_audited.py" not in produced
    invented = named - produced
    assert "ghost/never_audited.py" in invented


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


# ---------------------------------------------------------------------------
# A resolving name is not enforcement
# ---------------------------------------------------------------------------
#
# `test_the_named_enforcement_actually_exists` checks that each entry is a
# `def test_...` somewhere under tests/. That is necessary and nowhere
# near sufficient: a renamed-but-unrelated test satisfies it, and the
# index goes on asserting a promise is kept by something that never
# mentions it. `test_one_scan_carries_no_trajectory` sat on P7 that way —
# a real test, correctly passing, about ADR 009's history contract rather
# than about refusing to publish an absurd number.
#
# So for the two promises 7.3 has to prove, each named test must argue the
# promise in its own words. Scoped to P7 and P8 deliberately: P1-P6 are
# not this phase's exit criterion, and a token rule applied to all eight
# would be a large edit justified by nothing measured.

FALSIFIER_TOKENS: dict[str, tuple[str, ...]] = {
    # "A number a reader with the repository in front of them would call
    # absurd" — the refusals that prevent one.
    "P7": ("withhold", "withheld", "unread", "floor", "absurd", "no score",
           "scope", "not scored"),
    # "A reported value with no attributable source, or a run whose
    # coverage cannot be recovered from its output."
    "P8": ("source", "coverage", "attributable", "built-in", "provenance"),
}


def _test_bodies() -> dict[str, str]:
    """Each test's docstring plus its leading comment block, by name."""
    import ast

    bodies: dict[str, str] = {}
    for path in sorted(ROOT.glob("tests/test_*.py")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            # The comment block immediately above the def, which is where
            # several tests here put their reasoning instead of a docstring.
            preamble = []
            cursor = min([d.lineno for d in node.decorator_list] + [node.lineno]) - 2
            while cursor >= 0 and lines[cursor].lstrip().startswith("#"):
                preamble.append(lines[cursor])
                cursor -= 1
            bodies[node.name] = " ".join(
                [ast.get_docstring(node) or "", *preamble]
            ).lower()
    return bodies


@pytest.mark.parametrize("promise", sorted(FALSIFIER_TOKENS))
def test_the_named_enforcement_argues_the_promise(promise: str) -> None:
    """The index must resolve to tests that are *about* the promise.

    Checked against the published falsifier's own vocabulary, so the
    rule is anchored to `product-intent.md` rather than to a list of
    words this file invented. A test that keeps the promise while never
    naming what it refuses is not evidence a reader can follow from the
    promise to the proof.
    """
    bodies = _test_bodies()
    tokens = FALSIFIER_TOKENS[promise]
    silent = [
        name for name in ENFORCEMENT[promise]
        if name in bodies and not any(token in bodies[name] for token in tokens)
    ]

    assert not silent, (
        f"{promise} names tests that never mention what the promise forbids "
        f"{tokens}: {silent}. A name in an index is not enforcement — say in the "
        "test why it keeps the promise, or take it off the list."
    )


def test_the_two_promises_this_phase_proves_are_still_published() -> None:
    """P7 and P8 are 7.3's exit criterion; the token rule follows them.

    If either is renamed or dropped from `product-intent.md`, the
    falsifier vocabulary above is describing something that no longer
    exists and has to move with it.
    """
    published = _published_promises()

    assert set(FALSIFIER_TOKENS) <= published, (
        f"falsifier tokens are defined for promises that are not published: "
        f"{sorted(set(FALSIFIER_TOKENS) - published)}"
    )
