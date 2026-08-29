"""P5: an escalated finding is presented once in an AI prompt."""

from __future__ import annotations

from pathlib import Path

from maintainability_audit._identity import risk_identities
from maintainability_audit._work_order import work_order
from maintainability_audit.config import load_config
from maintainability_audit.prompts import render_ai_prompt
from maintainability_audit.report import build_report


def _risk_display(finding: dict[str, object]) -> str:
    return (
        f"`{finding['path']}:{finding['line']}` "
        f"{finding['name']}: {finding['text']}"
    )


def test_an_escalated_risk_is_withheld_or_listed_but_never_both(
    tmp_path: Path,
) -> None:
    """A live prompt must not contradict its own escalation note.

    ``prompt_escalation_note`` presents these candidates as deliberately
    withheld, while ``prompt_items(..., escalated=...)`` removes their
    matching work-order rows. Risk findings travel through a separate focus
    section, so the test renders the production prompt rather than testing
    either helper in isolation.
    """
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text(
        "# TODO: ESCALATED-FIRST\n"
        "# TODO: ESCALATED-SECOND\n"
        "def keep():\n"
        "    return 1\n",
        encoding="utf-8",
    )

    report = build_report(root, load_config(None))
    risks = report["risk_findings"]
    assert len(risks) == 2, f"fixture must produce two distinct risks: {risks}"

    identities = risk_identities(report)
    candidates = [
        {
            "fingerprint": identities[(risk["path"], risk["name"], risk["line"])],
            "returns": 2,
            "targeted": True,
            "commits": ["a" * 40],
            "reason": "the prior narrow repair returned",
        }
        for risk in risks
    ]
    report["work_order"] = work_order(report)
    report["design_review_candidates"] = candidates
    escalated = {candidate["fingerprint"] for candidate in candidates}
    assert escalated <= {item.get("fingerprint") for item in report["work_order"]}

    prompt = render_ai_prompt(report)
    withheld = "**2 finding(s) are deliberately excluded from this prompt.**" in prompt
    assert withheld, "the escalation note did not represent the withheld candidates"

    for risk in risks:
        identity = _risk_display(risk)
        listed = identity in prompt
        presentations = int(withheld) + int(listed)
        assert presentations == 1, (
            f"{identity} was presented {presentations} times: the prompt says it is "
            f"withheld={withheld}, then lists it={listed}"
        )
