"""A finding that keeps coming back is not a nit — ADR 009 §3b, task 5.4.

The feature that separates this from a linter with a database, and the
one a language model structurally cannot supply for itself.

A model evaluates each turn cold. It has no background process
integrating friction over time — no *"I have touched this module four
times and it keeps fighting me"* — so it will patch the same wrong
abstraction indefinitely without ever raising the design question.
Human threshold-crossing is affective: irritation integrated into a cost
signal, and that is real engineering information. This tool has git
history and a durable record, so it can compute externally what the
model cannot hold.

Three outcomes, each meaning something different:

- **cleared and stayed cleared** — the advice worked. Nothing to say.
- **never cleared** — ignored, or not actionable. Repeated across
  findings of one kind it indicts the *prompt*, not the developer.
- **cleared, then returned** — the strongest signal in the system.
  Someone was told exactly what to change, changed it, and the problem
  came back. That is evidence the finding is a *symptom* and the advice
  addressed the symptom, which should escalate to a design-review
  candidate rather than being re-issued as the same nit a third time.

Recurrence alone would be weak — code churns for many reasons, and "this
came back" says only that the file changed twice. What makes it strong
is that the tool *generated the advice*, so it knows which findings were
targeted. A linter can tell you a rule fired again; only something that
remembers what it advised can tell you its own advice is not working.
"""

from __future__ import annotations

import pytest

from maintainability_audit._recurrence import (
    Outcome,
    escalations,
    outcomes,
    recurrence,
)
from maintainability_audit._scan_history import ScanRecord, Segment


def _scan(n: int, findings: tuple[str, ...], targeted: tuple[str, ...] = ()) -> ScanRecord:
    return ScanRecord(
        recorded_at=f"2026-0{n + 1}-01T00:00:00Z", commit=str(n) * 40, branch="main",
        scope="full", rubric_version="0.7.0", calibration=2.6279,
        thresholds_digest="t", analyzers=("lizard",), scored_languages=("Python",),
        estimate=4.0, fingerprints=findings, targeted=targeted,
    )


def _segment(*records: ScanRecord) -> Segment:
    return Segment(records=list(records))


# --------------------------------------------------------------------
# Recurrence: gone, then back
# --------------------------------------------------------------------


def test_a_finding_that_left_and_returned_is_counted(tmp_path: object) -> None:
    """Present, absent, present is one return. Not two findings."""
    result = recurrence(_segment(
        _scan(0, ("a", "b")),
        _scan(1, ("b",)),
        _scan(2, ("a", "b")),
    ))

    assert result["a"].returns == 1
    assert "b" not in result, "a finding that never left has not returned"


def test_a_finding_that_returns_twice_is_a_design_review_candidate() -> None:
    """The escalation rule, and the whole point of the feature.

    Fixed, came back, fixed again, came back again. Re-issuing "shorten
    this function" a third time is the nit-loop; the honest response is
    that the abstraction is wrong.
    """
    result = recurrence(_segment(
        _scan(0, ("a",)), _scan(1, ()), _scan(2, ("a",)),
        _scan(3, ()), _scan(4, ("a",)),
    ))

    assert result["a"].returns == 2
    assert result["a"].design_review_candidate is True


def test_one_return_is_not_yet_an_escalation() -> None:
    """Code churns for many reasons and once is not a pattern.

    Escalating on a single return would flood the report with noise from
    ordinary refactoring, and an escalation that fires constantly is one
    nobody reads.
    """
    result = recurrence(_segment(_scan(0, ("a",)), _scan(1, ()), _scan(2, ("a",))))

    assert result["a"].returns == 1
    assert result["a"].design_review_candidate is False


def test_recurrence_names_the_commits_it_happened_in() -> None:
    """"It came back" is a claim; the commits are the evidence for it.

    A reader has to be able to go and look, or the escalation is an
    assertion about their code they cannot check.
    """
    result = recurrence(_segment(
        _scan(0, ("a",)), _scan(1, ()), _scan(2, ("a",)),
    ))

    assert result["a"].returned_in == ("2" * 40,)
    assert result["a"].cleared_in == ("1" * 40,)


# --------------------------------------------------------------------
# Remediation outcomes: did the advice work
# --------------------------------------------------------------------


def test_a_targeted_finding_that_cleared_is_recorded_as_working() -> None:
    """The loop nothing else in the design closes.

    The tool generated the prompt, so it knows what it asked for. Whether
    that specific thing then cleared is checkable, and is the only
    evidence the advice was any good.
    """
    result = outcomes(_segment(
        _scan(0, ("a", "b"), targeted=("a",)),
        _scan(1, ("b",)),
    ))

    assert result["a"] is Outcome.CLEARED


def test_a_targeted_finding_that_never_cleared_indicts_the_advice() -> None:
    """Ignored, or not actionable — and across many findings of one kind
    it is the prompt that is wrong, not the developer."""
    result = outcomes(_segment(
        _scan(0, ("a",), targeted=("a",)),
        _scan(1, ("a",)),
        _scan(2, ("a",)),
    ))

    assert result["a"] is Outcome.NEVER_CLEARED


def test_a_targeted_finding_that_cleared_and_returned_is_the_strongest_signal() -> None:
    """Told exactly what to change, changed it, and it came back.

    This is the case that must not be re-issued as the same nit. It is
    evidence the finding was a symptom and the advice treated the
    symptom.
    """
    result = outcomes(_segment(
        _scan(0, ("a",), targeted=("a",)),
        _scan(1, ()),
        _scan(2, ("a",)),
    ))

    assert result["a"] is Outcome.CLEARED_THEN_RETURNED


def test_a_finding_nobody_was_advised_about_has_no_outcome() -> None:
    """Absence of advice is not failure of advice.

    Counting untargeted findings as "never cleared" would blame the
    prompt for work it never asked for — the same absence-as-value
    mistake this project exists to remove.
    """
    result = outcomes(_segment(_scan(0, ("a", "b"), targeted=("a",)), _scan(1, ("a", "b"))))

    assert "b" not in result
    assert result["a"] is Outcome.NEVER_CLEARED


# --------------------------------------------------------------------
# What reaches the reader
# --------------------------------------------------------------------


def test_escalations_lead_with_the_returned_and_explain_why() -> None:
    """An escalation without its reason is a louder nit."""
    found = escalations(_segment(
        _scan(0, ("sym",), targeted=("sym",)), _scan(1, ()), _scan(2, ("sym",)),
        _scan(3, ()), _scan(4, ("sym",)),
    ))

    assert found, "a twice-returned targeted finding must escalate"
    first = found[0]
    assert first["fingerprint"] == "sym"
    assert first["returns"] == 2
    assert "symptom" in first["reason"].lower()
    assert first["commits"], "the reader can go and look"


def test_a_quiet_history_escalates_nothing() -> None:
    """The check must not fire on the case it does not describe."""
    assert escalations(_segment(_scan(0, ("a",)), _scan(1, ("a",)))) == []


def test_a_single_scan_cannot_show_recurrence() -> None:
    """Recurrence is a statement about change, and one scan has none."""
    assert recurrence(_segment(_scan(0, ("a",)))) == {}
    assert escalations(_segment(_scan(0, ("a",)))) == []


@pytest.mark.parametrize("history", [(), ((),)])
def test_an_empty_or_findingless_history_is_not_an_error(history: tuple) -> None:
    segment = _segment(*(_scan(n, f) for n, f in enumerate(history)))

    assert recurrence(segment) == {}
    assert outcomes(segment) == {}


# --------------------------------------------------------------------
# Closing the loop: the prompt records what it asked for
# --------------------------------------------------------------------


def test_the_recorded_scan_captures_what_the_prompt_targeted(tmp_path) -> None:
    """Without this, recurrence is only "a rule fired again".

    The tool generates the advice, so it knows which findings it asked
    somebody to fix. Recording that set is what lets a later run answer
    *did the advice work* — the loop nothing else in the design closes,
    and the thing a model cannot hold across sessions no matter how much
    context it is given.
    """
    import subprocess

    from maintainability_audit._scan_history import read_history
    from maintainability_audit.cli import main

    root = tmp_path / "loop"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    (root / "pkg").mkdir()
    for n in range(60):
        (root / "pkg" / f"mod{n}.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    body = "".join(f"    if x == {n}:\n        return {n}\n" for n in range(40))
    (root / "pkg" / "hot.py").write_text(f"def tangled(x):\n{body}    return -1\n",
                                         encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)

    assert main([
        "--root", str(root), "--output", str(tmp_path / "r.md"),
        "--prompt-output", str(tmp_path / "p.md"), "--record-history",
    ]) == 0

    record = read_history(root / ".maintainability" / "history.jsonl")[0]

    assert record.targeted, "the prompt named work and the record must say which"
    assert set(record.targeted) <= set(record.fingerprints), (
        "a prompt cannot target a finding this scan did not produce"
    )


def test_nothing_is_targeted_when_no_prompt_was_generated(tmp_path) -> None:
    """Advice not given is not advice ignored.

    A plain audit asks for nothing, so a later run must not read its
    findings as unfixed instructions and blame a prompt that never
    existed.
    """
    import subprocess

    from maintainability_audit._scan_history import read_history
    from maintainability_audit.cli import main

    root = tmp_path / "silent"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)

    main(["--root", str(root), "--output", str(tmp_path / "r.md"), "--record-history"])
    record = read_history(root / ".maintainability" / "history.jsonl")[0]

    assert record.targeted == ()


def test_an_escalation_reaches_the_report_and_stops_the_prompt_repeating_it() -> None:
    """The behaviour change, not just the label.

    An escalation that appears in the report while the prompt re-issues
    the same nit a third time has changed nothing. The point is that the
    tool stops giving advice it has evidence does not work.
    """
    from maintainability_audit._scan_view import escalations_markdown

    rendered = "\n".join(escalations_markdown([{
        "fingerprint": "function:src/a.py:tangled#0",
        "returns": 2, "targeted": True,
        "commits": ["c" * 40, "d" * 40],
        "reason": "cleared and returned 2 times after being named in a "
                  "remediation prompt: the advice addressed the symptom",
    }]))

    assert "## Design Review Candidates" in rendered
    assert "tangled" in rendered
    assert "2" in rendered
    assert "symptom" in rendered
    assert "cccccccc" in rendered, "the commits are shown so a reader can look"


def test_the_prompt_withholds_a_finding_it_has_already_failed_to_fix() -> None:
    """Re-issuing advice known not to hold is the nit-loop.

    A finding that cleared and returned twice after being targeted has
    earned a design conversation. Handing it to an agent a third time
    would produce the same patch and the same return.
    """
    from maintainability_audit._work_order import prompt_items

    items = [
        {"title": "a", "band": "quick-win", "delta": 0.2,
         "fingerprint": "function:src/a.py:tangled#0"},
        {"title": "b", "band": "quick-win", "delta": 0.1,
         "fingerprint": "function:src/b.py:other#0"},
    ]

    offered = [item["title"] for item in prompt_items(
        items, escalated={"function:src/a.py:tangled#0"})]

    assert offered == ["b"], "an escalated finding must not be re-issued as a nit"


def test_no_part_of_the_prompt_re_issues_an_escalated_finding() -> None:
    """Withholding it from the work order is not enough.

    The prompt has a second path: `prompt_focus_sections` lists function
    hotspots straight from the report and told an agent to "inspect
    first" the exact finding the work order had just withheld. Verified
    end to end on a real fix/return/fix/return history — the report
    escalated it correctly and the prompt still nagged about it once.

    A rule enforced on one path and not another is not enforced.
    """
    from maintainability_audit.prompts import render_ai_prompt

    report = {
        "summary": {"files_scanned": 1, "file_failures": 0, "function_failures": 1,
                    "duplicate_blocks": 0, "risk_findings": 0, "hard_gate_failures": 0},
        "score": {"maintainability_estimate": 4.0, "maintainability_range": [4.0, 4.0],
                  "evidence_status": {"status": "complete", "profile": "default-v1",
                                      "reasons": []},
                  "verified_grade": "B", "verified_grade_blockers": [],
                  "dimensions": {}, "worst_dimension": None, "categories": {},
                  "aspects": {}, "rubric": {}, "reference": {}, "standard": "s"},
        "function_hotspots": [{"path": "pkg/hot.py", "name": "tangled", "line": 1,
                               "lines": 82, "complexity": 41, "cognitive": 40,
                               "status": "fail", "kind": "function"}],
        "largest_files": [], "risk_findings": [], "duplicate_blocks": [],
        "near_duplicates": [], "dead_code": [], "idiom_concerns": [],
        "external_findings": [], "history": None, "hard_gate_failures": [],
        "missing_files": [], "work_order": [{"title": "tangled in pkg/hot.py", "band": "quick-win",
                        "delta": 0.1, "class_delta": 0.1, "class_count": 1,
                        "path": "pkg/hot.py", "line": 1, "target": "shorten it",
                        "rationale": "r", "verification": "v",
                        "finding_class": "oversized-declaration",
                        "fingerprint": "function:pkg/hot.py:tangled#0"}],
        "design_review_candidates": [{
            "fingerprint": "function:pkg/hot.py:tangled#0", "returns": 2,
            "targeted": True, "commits": ["a" * 40], "reason": "symptom"}],
    }

    prompt = render_ai_prompt(report)

    assert "tangled" not in prompt, (
        "an escalated finding was re-issued by a section other than the "
        "work order"
    )
    assert "design review" in prompt.lower(), (
        "and the agent is told why it is absent, or it will re-derive it"
    )
