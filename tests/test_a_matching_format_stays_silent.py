"""An honoured presentation says nothing, and an override still works (D194).

Covers existing behaviour: every assertion here passes at the base
commit. `format` already took effect there, and the disclosure key did
not exist, so none of them could fail. They are here because D194 made
the result conditional, and the risk in a conditional is the branch you
did not mean to change.

Two failure modes they hold. Emitting the key on every run would pass the
disclosure tests and turn a signal into a field nobody reads — the
always-on alarm. Refusing the override rather than disclosing it would
break the CI door, which asks for json and must receive json.

The disclosure itself is held by `test_a_format_override_is_disclosed`.
These are split out so that file's citations stay evidence rather than
being diluted by assertions that prove nothing it shipped.
"""

from __future__ import annotations

import json

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
    _config(tmp_path, persisted)
    (tmp_path / "module.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    return _mcp_audit.audit_repository(
        str(tmp_path), action="run", format=requested,
        run_analyzers=False, record_history=False, include_prompt=False,
        roots=(tmp_path.resolve(),),
    )


def test_the_override_still_takes_effect(tmp_path) -> None:
    """Disclosure is not refusal. CI asks for json and must get json."""
    assert _result(tmp_path, persisted="html", requested="json")["format"] == "json"


def test_no_key_when_the_call_matches_what_the_user_chose(tmp_path) -> None:
    """A caller honouring the preference says nothing; the key is a signal."""
    assert "presentation_override" not in _result(
        tmp_path, persisted="html", requested="html"
    )


def test_no_key_when_the_caller_passes_nothing(tmp_path) -> None:
    """Unset takes the persisted default, which is not an override."""
    result = _result(tmp_path, persisted="html", requested=None)

    assert result["format"] == "html"
    assert "presentation_override" not in result


def test_no_key_when_the_user_never_chose(tmp_path) -> None:
    """Nothing to override.

    A repository with no recorded presentation falls back to chat, so a
    caller naming a format is making the only choice on record rather
    than displacing one.
    """
    assert "presentation_override" not in _result(
        tmp_path, persisted=None, requested="json"
    )
