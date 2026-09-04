"""ADR 001 stage 5: evidence sufficiency, separate from quality.

Contract tests, not the recursive state-space suite — that is stage 6
and is deliberately not attempted here. What these pin is the published
behaviour of two new fields and, just as importantly, that **nothing
else moved**: the compatibility score, the CLI's exit code and every
non-JSON artifact must be identical to what they were before
verification metadata existed.

Every case starts from a report `build_report` produced, per ADR 001 §6
and the closure rules: a hand-built summary carries whichever fields the
author remembered, and cannot show that a real report satisfies a
property.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_evidence_normalization import _commit, _report, _tested_repo

from maintainability_audit._verification import (
    DEFAULT_PROFILE,
    DEFAULT_V1_NOT_REQUIRED,
    DEFAULT_V1_REQUIRED,
    verification,
)
from maintainability_audit.config import load_config
from maintainability_audit.evidence import (
    EvidenceValidationError,
    Measured,
    NotApplicable,
    Unknown,
    UnsupportedReportSchema,
    normalize_report_evidence,
)
from maintainability_audit.prompts import render_agent_instructions, render_ai_prompt
from maintainability_audit.renderers import render_markdown, render_pr_comment
from maintainability_audit.report import build_report
from maintainability_audit.scoring import score_report

# The version-2 public score contract, minus the two evidence fields the
# tests below strip explicitly.
SCORE_V2_FIELDS = (
    "maintainability_estimate", "maintainability_range", "verified_grade_blockers",
    "categories", "aspects", "dimensions", "rubric", "reference", "worst_dimension", "standard",
    "analyzer_scored_dimensions",
)


#: The corpus the shipped reference block names. 2.0.0 extended it from
#: three languages to eight; `test_readme_claims` holds the report to
#: `corpus.json` itself, and this contract only asserts the block did not
#: change in any other way.
CORPUS_LANGUAGES = [
    "Python", "TypeScript", "JavaScript", "Java", "C", "C++", "C#", "Fortran",
]


def _complete(tmp_path: Path) -> dict:
    _tested_repo(tmp_path)
    _commit(tmp_path, "start")
    return _report(tmp_path)


def _shallow(tmp_path: Path) -> dict:
    _tested_repo(tmp_path)  # never committed: build_report emits history None
    return _report(tmp_path)


def test_complete_evidence_issues_a_verified_grade(tmp_path: Path) -> None:
    score = _complete(tmp_path)["score"]

    assert score["evidence_status"]["status"] == "complete"
    assert score["evidence_status"]["profile"] == DEFAULT_PROFILE
    assert score["evidence_status"]["reasons"] == []
    assert score["verified_grade"] is not None


def test_a_report_without_history_is_incomplete_and_names_what_is_missing(tmp_path: Path) -> None:
    """The shallow-clone case, which is the common one in CI.

    The compatibility grade still exists and still comes from the
    evidence floor; the verified grade is withheld rather than being
    reported as a bad letter, which is the distinction ADR 001 §1 draws.
    """
    score = _shallow(tmp_path)["score"]

    assert score["evidence_status"]["status"] == "incomplete"
    assert score["verified_grade"] is None
    named = {reason["measurement"] for reason in score["evidence_status"]["reasons"]}
    assert named == {
        "history.code_coupling_pairs", "history.files_changed", "history.multi_commit_files",
        "history.qualifying_hotspots", "history.single_author_files",
    }
    assert all(reason["reason"] and reason["provenance"] for reason in score["evidence_status"]["reasons"])
    assert score["verified_grade"] is None, "an incomplete report issues no grade at all"


def test_one_unknown_summary_measurement_withholds_the_verified_grade(tmp_path: Path) -> None:
    report = _complete(tmp_path)
    del report["summary"]["test_file_count"]

    score = score_report(report)

    assert score["evidence_status"]["status"] == "incomplete"
    assert score["verified_grade"] is None
    assert [reason["measurement"] for reason in score["evidence_status"]["reasons"]] == [
        "summary.test_file_count"
    ]


def test_measured_zero_is_complete_evidence(tmp_path: Path) -> None:
    """The distinction the whole evidence model exists for.

    A clean repository genuinely measures zero risk findings. Treating
    that as missing would withhold verification from exactly the
    repositories that earned it.
    """
    report = _complete(tmp_path)
    assert report["summary"]["risk_findings"] == 0, "fixture must actually measure zero"
    evidence = normalize_report_evidence(report)
    assert isinstance(evidence.summary.risk_findings, Measured)

    assert report["score"]["evidence_status"]["status"] == "complete"
    assert report["score"]["verified_grade"] is not None


def test_not_applicable_is_complete_evidence(tmp_path: Path) -> None:
    """"Looked, and there is nothing to measure" does not block a grade.

    A one-commit repository has no file with three commits, so ownership
    concentration has no population. That is resolved evidence, not a
    gap, and the fixture below relies on it being present.
    """
    report = _complete(tmp_path)
    evidence = normalize_report_evidence(report)
    assert isinstance(evidence.history.single_author_files, NotApplicable), (
        "fixture must actually exercise NotApplicable"
    )

    result = verification(evidence, "A")

    assert result["evidence_status"]["status"] == "complete"
    assert result["verified_grade"] == "A"
    assert report["score"]["verified_grade"] in {"A", "A+"}
    assert report["score"]["maintainability_range"] == [
        report["score"]["maintainability_estimate"],
        report["score"]["maintainability_estimate"],
    ]
    assert not any(
        "knowledge_concentration" in blocker
        for blocker in report["score"]["verified_grade_blockers"]
    )


def test_unknown_ownership_blocks_top_grades(tmp_path: Path) -> None:
    """Deleting one measured ownership count cannot retain an A+.

    Build three real commits by one author so the production history
    reports measured, maximally concentrated ownership. Deleting only
    that count changes it to Unknown. The compatibility grade must then
    demote because stage 7 consumers still read it.
    """
    _tested_repo(tmp_path)
    for index in range(3):
        (tmp_path / "app.py").write_text(
            f"def ok():\n    return {index}\n",
            encoding="utf-8",
        )
        _commit(tmp_path, f"change {index}")
    report = _report(tmp_path)
    complete_evidence = normalize_report_evidence(report)
    assert isinstance(complete_evidence.history.single_author_files, Measured)
    assert complete_evidence.history.single_author_files.value == 1
    assert report["history"]["multi_commit_files"] == 1
    assert report["score"]["verified_grade"] == "A+", "fixture must expose the top-grade boundary"
    assert report["score"]["maintainability_range"] == [
        report["score"]["maintainability_estimate"],
        report["score"]["maintainability_estimate"],
    ]

    del report["history"]["single_author_files"]
    incomplete_evidence = normalize_report_evidence(report)
    assert isinstance(incomplete_evidence.history.single_author_files, Unknown)

    score = score_report(report)

    assert score["evidence_status"]["status"] == "incomplete"
    assert score["verified_grade"] is None
    assert score["verified_grade_blockers"] == [], "no grade was issued, so nothing caps one"
    assert score["maintainability_range"][0] < score["maintainability_range"][1]
    assert any(
        reason["measurement"] == "history.single_author_files"
        for reason in score["evidence_status"]["reasons"]
    ), "the unmeasured ownership must still be named, now as an evidence reason"


def test_reason_order_is_deterministic(tmp_path: Path) -> None:
    report = _shallow(tmp_path)

    orders = [
        [reason["measurement"] for reason in score_report(report)["evidence_status"]["reasons"]]
        for _ in range(3)
    ]

    assert orders[0] == orders[1] == orders[2] == sorted(orders[0])


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda r: r["summary"].update({"risk_findings": -1}), EvidenceValidationError),
        (lambda r: r["summary"].update({"files_scanned": 1.5}), EvidenceValidationError),
        (lambda r: r.update({"schema_version": 99}), UnsupportedReportSchema),
    ],
)
def test_invalid_evidence_still_raises_rather_than_scoring(tmp_path: Path, mutate, expected) -> None:
    """Invalid is not a third status.

    ADR 001 §3 requires invalid combinations to fail validation. A
    serialized ``status: invalid`` document would let a malformed report
    flow onward carrying numbers nobody should trust.
    """
    report = _complete(tmp_path)
    mutate(report)

    with pytest.raises(expected):
        score_report(report)


PRE_STAGE5_SCORE = Path(__file__).parent / "fixtures" / "pre_stage5_score.json"


def _fixture_repo(root: Path) -> Path:
    """The exact tree the pinned pre-Stage-5 score was captured from.

    Content is fixed here rather than shared with the other helpers,
    because the pinned JSON is only meaningful against this tree.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (root / "app.py").write_text("def ok(value):\n    return value + 1\n", encoding="utf-8")
    (root / "test_app.py").write_text(
        "from app import ok\n\n\ndef test_ok():\n    assert ok(1) == 2\n", encoding="utf-8"
    )
    _commit(root, "start")
    return root


def test_not_applicable_rollup_is_the_only_change_to_the_pre_stage_five_anchor(
    tmp_path: Path,
) -> None:
    """Preserve the old anchor and name the one intentional delta.

    The first version of this test compared the current scorer with
    another call to the current scorer. An audit pointed out that if
    Stage 5 had changed a compatibility calculation, both sides would
    have changed together and the test would still have passed: it
    could not establish the invariant it was named for. That is the same
    "self-consistency mistaken for invariance" shape as claiming
    enforcement from a test name.

    ``fixtures/pre_stage5_score.json`` was captured by running commit
    1499bad — the last commit before verification metadata existed —
    against the tree ``_fixture_repo`` builds. That fixture has complete
    NotApplicable ownership evidence. Excluding its absent population
    now deliberately changes the two affected categories, the interval,
    and the grade explanation. Everything else must still match the
    historical anchor exactly.
    """
    report = build_report(_fixture_repo(tmp_path / "fixture"), load_config(None))
    expected = json.loads(PRE_STAGE5_SCORE.read_text(encoding="utf-8"))
    assert "verified_grade" not in expected, "the anchor must predate Stage 5"

    # The anchor predates two renames. Stage 8 changed public field
    # names without changing any value, so the anchor is compared under
    # its own historical names rather than being rewritten — rewriting a
    # frozen artifact to match new code destroys what makes it an anchor.
    renamed = {"overall": "maintainability_estimate", "overall_range": "maintainability_range",
               "grade_blockers": "verified_grade_blockers"}
    expected = {renamed.get(key, key): value for key, value in expected.items()}

    shipped = {key: value for key, value in report["score"].items()
               if key not in {"evidence_status", "verified_grade", "analyzer_scored_dimensions"}}

    changed = {"categories", "maintainability_range", "grade",
               "verified_grade_blockers", "aspects", "rubric", "reference"}
    assert {key: value for key, value in shipped.items() if key not in changed} == {
        key: value for key, value in expected.items() if key not in changed | {"grade"}
    }
    # `reference` gained a disclosure, not a meaning: the corpus behind
    # "1.0x = the median mature-OSS repo" holds Python, TypeScript and
    # JavaScript, and this project parses seven languages. The multiple is
    # unchanged; the report now says what it is a multiple of.
    assert shipped["reference"] == {
        **expected["reference"],
        "corpus_languages": CORPUS_LANGUAGES,
        "corpus_note": shipped["reference"]["corpus_note"],
    }
    assert shipped["categories"] == {
        **expected["categories"],
        "analyzability": 4.6,
        "modifiability": 5.0,
    }
    # aspects gained the Class 5 opt-in coverage aspect. This fixture opts
    # no suite in, so test_effectiveness is NotApplicable — present and
    # None — and every aspect the anchor recorded is otherwise unchanged.
    assert shipped["aspects"] == {**expected["aspects"], "test_effectiveness": None}
    # The published rubric moved test_effectiveness from `unscored` to a
    # scored aspect and reweighted testability to seat it (the other three
    # scaled by 0.8 so the category renormalizes to its old value while
    # coverage is NotApplicable). Stated as deltas on the frozen anchor.
    class5_testability = {"test_presence": 0.40, "declaration_size": 0.24,
                          "policy_gates": 0.16, "test_effectiveness": 0.20}
    assert shipped["rubric"] == {
        **expected["rubric"],
        "category_aspects": {**expected["rubric"]["category_aspects"],
                             "testability": class5_testability},
        "unscored": {name: reason for name, reason in expected["rubric"]["unscored"].items()
                     if name != "test_effectiveness"},
    }
    assert shipped["maintainability_range"] == [shipped["maintainability_estimate"], shipped["maintainability_estimate"]]
    # The anchor recorded "A" and the verified grade is "A+". That delta
    # is stage 6's NotApplicable exclusion, documented above — not a
    # stage 8 effect, which renamed fields without moving any value.
    assert report["score"]["verified_grade"] == "A+"
    assert "grade" not in shipped, "stage 8 removed the compatibility grade"
    assert shipped["verified_grade_blockers"] == []


def test_verification_does_not_disturb_the_rest_of_the_document(tmp_path: Path) -> None:
    """The incomplete case, where a withheld grade could leak sideways."""
    for report in (_complete(tmp_path / "full"), _shallow(tmp_path / "shallow")):
        score = report["score"]
        assert set(SCORE_V2_FIELDS) <= set(score)
        stripped = {k: v for k, v in score.items() if k not in {"evidence_status", "verified_grade"}}
        assert set(stripped) == set(SCORE_V2_FIELDS), sorted(set(stripped) ^ set(SCORE_V2_FIELDS))


def test_every_typed_scoring_input_is_classified_by_the_profile() -> None:
    """A new scoring input must force a versioning decision.

    ``default-v1`` used to be computed as "everything ``walk_evidence``
    returns", so adding a field to either evidence dataclass silently
    changed what the name required — two materially different contracts
    both calling themselves v1, which defeats the reason profiles are
    named at all.

    The requirement list is frozen now, and this fails until a new input
    is either required under a **new** profile name or recorded in
    ``DEFAULT_V1_NOT_REQUIRED``. Editing v1's set in place is a v2.
    """
    from maintainability_audit.evidence import HistoryEvidence, SummaryEvidence

    model = {f"summary.{field.name}" for field in SummaryEvidence.__dataclass_fields__.values()}
    model |= {f"history.{field.name}" for field in HistoryEvidence.__dataclass_fields__.values()}
    classified = DEFAULT_V1_REQUIRED | DEFAULT_V1_NOT_REQUIRED

    assert model == classified, (
        f"unclassified scoring inputs: {sorted(model - classified)} — require them under a new "
        f"profile name or list them in DEFAULT_V1_NOT_REQUIRED; "
        f"classified but absent from the model: {sorted(classified - model)}"
    )


def test_rendered_artifacts_surface_the_evidence_contract(tmp_path: Path) -> None:
    """Stage 7 inverted this test, deliberately.

    Through stage 6 it asserted the renderers did **not** mention
    `evidence_status` or `verified_grade`, because consumer migration was
    explicitly out of scope and silently half-migrating them would have
    been worse than leaving them alone. Stage 7 migrates them, so the
    assertion flips: the artifacts must now carry the distinction.

    The detailed per-consumer behaviour lives in
    tests/test_consumer_migration.py; this keeps the stage-5 fields
    tethered to the artifacts so a regression here fails in both places.
    """
    from maintainability_audit._evidence_view import NOT_VERIFIED

    complete = _complete(tmp_path / "full")
    incomplete = _shallow(tmp_path / "shallow")

    for report in (complete, incomplete):
        rendered = "\n".join((
            render_markdown(report),
            render_pr_comment(report),
            render_ai_prompt(report),
            render_agent_instructions(report),
        ))
        verified = report["score"]["verified_grade"]
        if verified:
            assert verified in rendered
            assert NOT_VERIFIED not in rendered
        else:
            assert NOT_VERIFIED in rendered


@pytest.mark.parametrize("committed", [True, False], ids=["complete", "incomplete"])
def test_fail_on_gate_exit_code_is_unchanged_by_evidence_completeness(
    tmp_path: Path, committed: bool
) -> None:
    """`--fail-on-gate` depends on hard-gate findings and nothing else.

    This is the invariant ADR 002 was rejected for assuming otherwise:
    the flag never consumed the grade, so a withheld verified grade must
    not start making builds fail.
    """
    _tested_repo(tmp_path)
    if committed:
        _commit(tmp_path, "start")
    report = build_report(tmp_path, load_config(None))
    assert not report["hard_gate_failures"], "fixture must be gate-clean"

    result = subprocess.run(
        [sys.executable, "-m", "maintainability_audit", "--root", str(tmp_path), "--fail-on-gate"],
        capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr[-400:]
