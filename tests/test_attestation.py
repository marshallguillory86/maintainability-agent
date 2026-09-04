"""The record an author cannot produce about their own work.

The three mechanisms each answer one question about a change. This composes
them into the artifact they were built for — and the value of that artifact
is entirely in what it refuses to overstate, so that is what is tested here.

Three properties, and all three are about honesty rather than plumbing:

- **A mixed result reads as mixed.** A change that stayed in scope while
  silencing a finding must not produce a document anyone could wave as a
  pass.
- **Not asked is not the same as passed.** A question nobody ran must not
  render as a verdict.
- **It claims reproducible, never signed.** Nothing here holds a key, and a
  document that implied otherwise would be the exact overclaim the rest of
  this project spends its time removing.
"""

from __future__ import annotations

from maintainability_audit._attestation import attestation_record, render_attestation

CLEAN = {
    "tool_version": "2.3.0",
    "git_commit": "a" * 40,
    "git_branch": "main",
    "git_status_short": "",
    "score": {
        "maintainability_estimate": 4.2,
        "verified_grade": "B",
        "evidence_status": {"status": "complete"},
    },
    "analyzer_coverage": {"by_outcome": {"ran": [{"tool": "lizard"}]}},
    "hard_gate_failures": [],
    "scope_conformance": {
        "revspec": "main...HEAD", "conformant": True, "out_of_scope": [],
        "suppressions_on_named_paths": 0, "clean": True,
    },
    "dimension_ratchet": {"comparable": True, "regressed": []},
}


def _with(**changes: object) -> dict:
    report = {key: dict(value) if isinstance(value, dict) else value
              for key, value in CLEAN.items()}
    report.update(changes)
    return report


def test_a_clean_change_says_so_on_every_question() -> None:
    text = render_attestation(CLEAN)

    assert "**Stayed inside the work order:** yes" in text
    assert "**Without silencing a finding:** yes" in text
    assert "**No dimension regressed:** yes" in text


def test_a_silenced_finding_is_not_hidden_by_staying_in_scope() -> None:
    """The mixed verdict the artifact exists to make unmissable.

    Scope and silence are separate questions, so a change that obeyed the
    first and failed the second must not produce a document that reads as a
    pass on either.
    """
    report = _with(scope_conformance={
        "revspec": "main...HEAD", "conformant": True, "out_of_scope": [],
        "suppressions_on_named_paths": 2, "clean": False,
    })

    text = render_attestation(report)

    assert "**Stayed inside the work order:** yes" in text
    assert "**Without silencing a finding:** no" in text
    assert attestation_record(report)["no_finding_silenced"] is False


def test_a_question_nobody_asked_is_not_reported_as_passed() -> None:
    """`None`, not `True`. An unrun check is not a clean result."""
    report = _with(scope_conformance=None, dimension_ratchet=None)

    record = attestation_record(report)

    assert record["stayed_in_scope"] is None
    assert record["no_finding_silenced"] is None
    assert record["no_dimension_regressed"] is None
    assert "Nothing was asked" in render_attestation(report)


def test_an_incomparable_ratchet_is_not_reported_as_no_regression() -> None:
    """Two scans under different calibration cannot be differenced.

    "Not established" is the honest rendering; "yes" would be a claim the
    evidence cannot support.
    """
    report = _with(dimension_ratchet={
        "comparable": False, "regressed": [],
        "reason": "calibration changed, so scans cannot be joined",
    })

    text = render_attestation(report)

    assert "not established" in text
    assert attestation_record(report)["no_dimension_regressed"] is None


def test_an_uncommitted_tree_is_disclosed() -> None:
    """A verdict about "the commit" that depends on unstaged work is a lie."""
    report = _with(git_status_short=" M src/thing.py")

    assert attestation_record(report)["tree_dirty"] is True
    assert "uncommitted changes present" in render_attestation(report)


def test_the_document_claims_reproducible_and_refuses_to_claim_signed() -> None:
    """Nothing here holds a key, and the artifact must not imply one.

    "Signed" is the word a reader reaches for with an attestation, which is
    exactly why the document has to say the opposite in its own text.
    """
    text = render_attestation(CLEAN)

    assert "not signed" in text.lower()
    assert "Digest:" in text


def test_the_digest_is_reproducible_and_content_bound() -> None:
    first = attestation_record(CLEAN)["digest"]
    second = attestation_record(CLEAN)["digest"]
    moved = attestation_record(_with(score={
        "maintainability_estimate": 3.1, "verified_grade": "C",
        "evidence_status": {"status": "complete"},
    }))["digest"]

    assert first == second, "the same inputs produced two different digests"
    assert first != moved, "the digest did not follow the record's content"


def test_the_record_carries_no_score_verdict_of_its_own() -> None:
    """It reports the estimate the audit produced; it never computes one."""
    record = attestation_record(CLEAN)

    assert record["estimate"] == 4.2
    assert "categories" not in record
    assert "dimensions" not in record


def test_the_document_states_that_it_never_opened_the_diff() -> None:
    text = render_attestation(CLEAN)

    assert "not** that the change to it was correct" in text
    assert "touches no score" in text
