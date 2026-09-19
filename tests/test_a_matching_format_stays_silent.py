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

from _presentation_fixtures import audit  # noqa: E402 - tests dir on sys.path


def test_the_override_still_takes_effect(tmp_path) -> None:
    """Disclosure is not refusal. CI asks for json and must get json."""
    assert audit(tmp_path, persisted="html", requested="json")["format"] == "json"


def test_no_key_when_the_call_matches_what_the_user_chose(tmp_path) -> None:
    """A caller honouring the preference says nothing; the key is a signal."""
    assert "presentation_override" not in audit(
        tmp_path, persisted="html", requested="html"
    )


def test_no_key_when_the_caller_passes_nothing(tmp_path) -> None:
    """Unset takes the persisted default, which is not an override."""
    result = audit(tmp_path, persisted="html", requested=None)

    assert result["format"] == "html"
    assert "presentation_override" not in result


def test_no_key_when_the_user_never_chose(tmp_path) -> None:
    """Nothing to override.

    A repository with no recorded presentation falls back to chat, so a
    caller naming a format is making the only choice on record rather
    than displacing one.
    """
    assert "presentation_override" not in audit(
        tmp_path, persisted=None, requested="json"
    )
