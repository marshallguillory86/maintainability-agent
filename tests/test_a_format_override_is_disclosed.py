"""Overriding the presentation the user chose is stated, not silent (D194).

`format` is a per-call override and must stay one: CI asks for json and
has to get json. What it may not be is invisible. A caller passing
`format` when the repository has a persisted `presentation.format` is
substituting its own presentation for the one the person recorded during
setup, and the result said nothing about it — `format: "json"` with no
mention that `html` was chosen.

That is D26's failure with the report produced rather than withheld.
There, a user never saw the html report because the question was handed
over as data and never asked. Here the question was asked and answered,
and the answer was overridden on the way out. From the result alone a
reader cannot tell "the user asked for json" from "the agent preferred
json".

It is the one divergence this tool does not disclose. Coverage says
reported-not-scored and why; pillars say not-measured and why; the
environment work order names what could not run; the delegate prints the
score without its declarations. Presentation was the gap.

The silent cases — an honoured preference, an unset call, a repository
that chose nothing — are held by `test_a_matching_format_stays_silent`,
which passes at this change's base and is kept out of here so these
citations stay evidence.
"""

from __future__ import annotations

import json

import pytest

from maintainability_audit import _mcp_audit


def _config(tmp_path, persisted: str | None) -> dict:
    config = {
        "version": 1,
        "analyzers": {"run": False},
        "history": {"record": False},
    }
    if persisted is not None:
        config["presentation"] = {"format": persisted}
    (tmp_path / "maintainability-agent.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    return config


def _result(tmp_path, persisted: str | None, requested: str | None) -> dict:
    """Run the audit through the MCP door and return its top-level result."""
    _config(tmp_path, persisted)
    (tmp_path / "module.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    return _mcp_audit.audit_repository(
        str(tmp_path), action="run", format=requested,
        run_analyzers=False, record_history=False, include_prompt=False,
        roots=(tmp_path.resolve(),),
    )


def test_a_different_format_than_the_user_chose_is_disclosed(tmp_path) -> None:
    """The shape that shipped: html chosen, json delivered, nothing said."""
    result = _result(tmp_path, persisted="html", requested="json")

    assert result["presentation_override"] == {
        "requested": "json", "persisted": "html",
    }


@pytest.mark.parametrize("requested", ["chat", "html", "json"])
def test_every_presentation_discloses_the_same_way(tmp_path, requested) -> None:
    """Not just json. Any format that is not the recorded one is a
    substitution, including one this tool happens to prefer."""
    result = _result(tmp_path, persisted="markdown", requested=requested)

    assert result["presentation_override"]["persisted"] == "markdown"
    assert result["presentation_override"]["requested"] == requested
