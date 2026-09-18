"""The first-stage setup wording survives the staged rewrite (D192).

Covers existing behaviour: every assertion here describes what
`setup_instruction` already said on a first run, and all of them pass at
the base commit. They are here because D192 made that text conditional —
derived from the questions in the reply rather than written once — and a
conditional can get its common branch wrong.

The presentation recital matters most. D26 shipped a host offering two of
the three presentations, because the tool handed the question over as data
and never said what the options were. The recital exists to stop that, and
a rewrite that dropped it on the branch which *does* ask `default_format`
would bring it back silently.

Deliberately kept out of `test_setup_instruction_describes_its_own_reply`
and not cited as D192's closing tests: they defend the change rather than
prove it, and citing them would make that entry look better attested than
it is.
"""

from __future__ import annotations

import json

from maintainability_audit import _mcp_gate


def _configure(root, **overrides) -> None:
    config = {
        "version": 1,
        "analyzers": {"run": True, "depth": "heavy", "license_policy": "permissive"},
        "presentation": {"format": "chat"},
        "history": {"record": True},
        "test_execution": {"requested": False},
    }
    config.update(overrides)
    (root / "maintainability-agent.json").write_text(json.dumps(config), encoding="utf-8")


def _reply(root, reconfigure=False) -> dict:
    return _mcp_gate._setup_first(root, reconfigure=reconfigure)


def test_a_first_stage_reply_still_says_what_it_always_said(tmp_path) -> None:
    """The fix must not relabel a genuine first run."""
    _configure(tmp_path)

    assert "has not been set up" in _reply(tmp_path)["setup_instruction"]


def test_reconfigure_still_names_the_user_as_the_reason(tmp_path) -> None:
    """A user revisiting their answers is not a first run, and never was."""
    _configure(tmp_path)

    assert "asked to change" in _reply(tmp_path, reconfigure=True)["setup_instruction"]


def test_the_first_stage_reply_does_recite_the_presentation_options(tmp_path) -> None:
    """Because that reply does carry the question, and the options matter."""
    _configure(tmp_path)

    instruction = _reply(tmp_path)["setup_instruction"]

    assert "default_format" in instruction
    for presentation in ("chat", "markdown", "html"):
        assert presentation in instruction
