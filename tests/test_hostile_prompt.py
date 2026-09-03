"""ADR 013: the tool seeds the hostile audit and never performs it.

The adversarial loop is the highest-leverage quality process this project
has and was the only one with no artifact — a person hand-wrote a fresh
prompt into a fresh session each time, so runs were neither repeatable nor
comparable. This is the third emitter on the prompt seam, beside
`render_ai_prompt` and `render_agent_instructions`.

What is worth testing here is not the wording. It is the three things that
would make the emitter a liability:

- handing the adversary a **stale promise**, which aims the audit at a
  claim the project no longer makes;
- burying the evidence in a **stringified structure**, which is how the
  first render came out and is worse than the prompt it replaces;
- letting it **gate or score**, which would make an LLM's non-deterministic
  reading part of a deterministic result.
"""

from __future__ import annotations

import re
from pathlib import Path

from maintainability_audit._hostile_prompt import CONTRACT, PROMISES
from maintainability_audit.prompts import render_hostile_audit_prompt

ROOT = Path(__file__).resolve().parents[1]


def _report() -> dict:
    return {
        "schema_version": 3,
        "generated_at": "2026-09-03T00:00:00+00:00",
        "git_commit": "a" * 40,
        "git_branch": "main",
        "mode": "full",
        "hard_gate_failures": [],
        "score": {
            "maintainability_estimate": 4.1,
            "maintainability_range": [3.8, 4.6],
            "verified_grade": "B",
            "evidence_status": {"status": "complete", "profile": "default-v1", "reasons": []},
            "verified_grade_blockers": ["unmeasured aspects price at 0"],
            "worst_dimension": "file_size",
        },
        "analyzer_coverage": {
            "by_outcome": {
                "ran": [{"tool": "lizard", "version": "1.23.0", "languages": ["python", "c"]},
                        {"tool": "ruff", "version": "0.15.14"}],
                "unavailable": [{"tool": "pmd", "detail": "no java"}],
            },
            "concepts_unexamined": ["testing"],
            "concepts_single_source": ["duplication"],
        },
    }


def test_every_published_promise_reaches_the_adversary() -> None:
    """A promise missing from the table is one nobody is asked to break.

    Held to `docs/product-intent.md` in both directions. The table lives in
    code so the prompt works offline without `docs/` installed, and that is
    exactly the arrangement that drifts — this is the guard for it.
    """
    intent = (ROOT / "docs" / "product-intent.md").read_text(encoding="utf-8")
    published = set(re.findall(r"^\| (P[1-8]) \|", intent, re.M))
    assert published, "product-intent.md no longer publishes a promise table"

    named = {tag for tag, _claim, _falsifier in PROMISES}
    assert named == published, (
        f"the hostile-audit promise table and product-intent.md disagree: "
        f"only in code {sorted(named - published)}, only in the document "
        f"{sorted(published - named)}"
    )


def test_every_promise_carries_the_thing_that_would_falsify_it() -> None:
    """"Attack a claim" is useless without the shape of the evidence."""
    for tag, claim, falsifier in PROMISES:
        assert claim.strip(), f"{tag} has no claim"
        assert falsifier.strip(), f"{tag} names nothing that would falsify it"


def test_the_brief_names_the_commit_and_the_promises() -> None:
    text = render_hostile_audit_prompt(_report())

    assert "a" * 40 in text, "the audit must be pointed at a commit"
    for tag, _claim, _falsifier in PROMISES:
        assert f"| {tag} |" in text, f"{tag} is not in the rendered brief"
    for rule in CONTRACT:
        assert rule.split(".")[0] in text, "the audit contract must be stated in the brief"


def test_the_brief_hands_over_the_evidence_already_computed() -> None:
    """The point is that the audit starts where measurement ended."""
    text = render_hostile_audit_prompt(_report())

    assert "4.1" in text and "file_size" in text
    assert "evidence complete" in text, (
        "evidence_status is a dict in the report; printing it raw put "
        "{'status': 'complete', ...} in front of the adversary"
    )
    assert "testing" in text, "a concept nothing measured is where P7 is easiest to break"
    assert "lizard" in text and "pmd" in text, "the adversary needs to know what ran"


def test_no_stringified_structure_reaches_the_brief() -> None:
    """The defect the first render actually had.

    `by_outcome` maps an outcome to a list of tool dicts, and stringifying
    it pasted several thousand characters of nested dicts — including every
    language jscpd claims — into a single line. A brief that buries its own
    content is worse than the hand-written prompt it replaces.
    """
    text = render_hostile_audit_prompt(_report())

    assert "{'" not in text and '{"' not in text, (
        "a Python dict was rendered into the brief instead of a label"
    )
    assert "[{" not in text, "a list of dicts was rendered into the brief"
    longest = max(len(line) for line in text.splitlines())
    assert longest < 700, f"a line of {longest} characters is a dumped structure, not prose"


def test_the_brief_is_deterministic_for_one_report() -> None:
    """P1's own discipline applied to the emitter: same input, same text."""
    report = _report()
    assert render_hostile_audit_prompt(report) == render_hostile_audit_prompt(report)


def test_the_emitter_returns_text_and_touches_nothing() -> None:
    """ADR 013's boundary: it does not gate, score, or write.

    The report is passed in and must come back unchanged — an emitter that
    mutated the report could move a score, which is the one thing a QA aid
    must never do.
    """
    import copy

    report = _report()
    before = copy.deepcopy(report)
    text = render_hostile_audit_prompt(report)

    assert isinstance(text, str)
    assert report == before, "the emitter mutated the report it was handed"


def test_a_dirty_tree_is_disclosed_to_the_adversary() -> None:
    """Auditing a commit while uncommitted work sits beside it is a trap.

    A finding reported against "the commit" that actually depends on
    unstaged changes is unreproducible, and this project has spent real
    time refuting audit claims that were already false at the named commit.
    """
    report = _report()
    report["git_status_short"] = " M src/maintainability_audit/report.py"

    text = render_hostile_audit_prompt(report)

    assert "dirty" in text.lower(), "an uncommitted tree must be disclosed"


def test_a_sparse_report_still_renders() -> None:
    """An unconfigured or withheld run must not break the emitter."""
    text = render_hostile_audit_prompt({})

    assert "Hostile audit brief" in text
    for tag, _claim, _falsifier in PROMISES:
        assert f"| {tag} |" in text
