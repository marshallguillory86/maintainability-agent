"""What the AI prompt says about its own evidence.

The Markdown report is careful: it prints the evidence status in every
state, and it labels analyzer measurements as reported-but-not-scored.
The prompt is the artifact an agent is told to obey, and it was the less
honest of the two.

Two omissions, both silent:

- **Completeness only appeared when it was absent.** `remediation_note`
  returns nothing for a complete report, so a prompt whose evidence was
  complete never said so. A reader could not tell "verified against the
  full profile" from "nobody printed the status", and those two warrant
  different confidence in the number directly above.
- **The estimate was never qualified.** `--analyzers` can run ten tools
  whose findings appear further down the same prompt, while the headline
  estimate still comes only from the built-in detectors; analyzer
  disagreement widens the range and never moves the point. An agent
  reading "Maintainability estimate: 4.1 / 5" beneath a list of analyzer
  findings would reasonably assume the tools produced the number.

The rule these tests hold: the prompt states where its number came from,
and never implies a tool ran that did not.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from test_consumer_migration import _commit, _source

from maintainability_audit.config import load_config
from maintainability_audit.prompts import render_ai_prompt
from maintainability_audit.report import build_report

# One measurement and one finding in the shape `_analyzer_sections`
# produces. Injected rather than obtained by running the pool: this is a
# test about what the renderer says, and invoking ten external tools
# would make it slow, environment-dependent, and silent about the very
# thing it is checking on any machine missing them.
MEASUREMENTS = {
    "cyclomatic_complexity": [
        {"path": "app.py", "name": "ok", "value": 4, "tool": "lizard", "sources": 2},
    ],
}
FINDINGS = [
    {"concept": "complexity", "path": "app.py", "line": 1,
     "message": "function is too complex", "tool": "lizard", "emits": "metric"},
]


@pytest.fixture
def complete(tmp_path: Path) -> dict:
    """A committed tree whose evidence resolves completely."""
    root = tmp_path / "complete"
    _source(root)
    _commit(root)
    return build_report(root, load_config(None))


def test_a_complete_prompt_still_says_the_evidence_is_complete(complete: dict) -> None:
    """Silence is not a status.

    `remediation_note` prints the evidence section only when something is
    missing, so the complete case said nothing at all. An agent cannot
    distinguish evidence that was verified from a renderer that forgot to
    mention it, and the number above is worth different amounts in those
    two worlds.
    """
    assert complete["score"]["evidence_status"]["status"] == "complete", (
        "fixture must produce complete evidence or this proves nothing"
    )
    prompt = render_ai_prompt(complete)

    assert "Evidence status" in prompt, (
        f"a complete prompt never names its evidence status:\n{prompt[:600]}"
    )
    assert "complete" in prompt.lower()


def test_an_incomplete_prompt_names_its_status_exactly_once(tmp_path: Path) -> None:
    """The new line must not double the section that already exists.

    `remediation_note` already opens with a status sentence when evidence
    is missing. A summary field that repeated it verbatim would be two
    statements of one fact, and the second one drifts.
    """
    root = tmp_path / "incomplete"
    _source(root)
    report = build_report(root, load_config(None))
    assert report["score"]["evidence_status"]["status"] != "complete"

    prompt = render_ai_prompt(report)
    assert prompt.count("### Evidence") == 1, "the detailed evidence section was duplicated"


def test_analyzer_results_do_not_imply_the_estimate_came_from_them(complete: dict) -> None:
    """The caveat the Markdown has and the prompt did not.

    Ten analyzers can appear in this prompt while the headline estimate
    still comes from six built-in detectors. Disagreement widens the
    range; it never moves the point. Unstated, the layout says otherwise.
    """
    complete["analyzer_measurements"] = MEASUREMENTS
    complete["analyzer_findings"] = FINDINGS

    prompt = render_ai_prompt(complete)
    lowered = prompt.lower()

    assert "built-in detectors" in lowered, (
        f"the prompt reports analyzer results without saying the estimate is "
        f"not derived from them:\n{prompt[:800]}"
    )
    assert "range" in lowered and "widen" in lowered, (
        "the caveat must say what analyzer disagreement actually does"
    )


def test_a_report_without_analyzers_does_not_mention_them(complete: dict) -> None:
    """Do not describe a tool that never ran.

    The opposite failure, and the easier one to ship: a caveat printed
    unconditionally would tell every zero-install user about analyzer
    disagreement they never had.
    """
    assert not complete.get("analyzer_measurements")
    assert not complete.get("analyzer_findings")

    lowered = render_ai_prompt(complete).lower()
    assert "analyzer" not in lowered, (
        "a prompt with no analyzer results claims analyzers were involved"
    )


@pytest.mark.parametrize("key", ["analyzer_measurements", "analyzer_findings"])
def test_either_analyzer_section_alone_earns_the_caveat(complete: dict, key: str) -> None:
    """Findings and measurements arrive independently.

    A verdict-only tool contributes findings and no measurements; a
    metric emitter can contribute measurements and no findings. Either
    puts analyzer output in front of the agent, so either has to carry
    the caveat.
    """
    complete[key] = MEASUREMENTS if key == "analyzer_measurements" else FINDINGS

    assert "built-in detectors" in render_ai_prompt(complete).lower(), (
        f"{key} alone did not earn the caveat"
    )
