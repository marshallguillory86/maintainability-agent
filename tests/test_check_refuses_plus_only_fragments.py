"""`--check` refuses a plus-only fragment for every declaration suffix (D146)."""
from __future__ import annotations

import copy

import pytest

from maintainability_audit._in_loop import check_content
from maintainability_audit.config import DEFAULT_CONFIG
from maintainability_audit.declarations import DECLARATION_SUFFIXES


def _config() -> dict:
    return copy.deepcopy(DEFAULT_CONFIG)


assert DECLARATION_SUFFIXES, "no declaration suffixes means this parametrization proves nothing"


@pytest.mark.parametrize("suffix", sorted(DECLARATION_SUFFIXES))
def test_plus_only_fragment_is_not_read_as_source(suffix: str) -> None:
    result = check_content(f"candidate{suffix}", "+function hello() {\n+ return 1\n+}\n", _config())
    assert result["declarations_read"] is False
    assert result["note"], "a refused fragment needs a stated reason"


def test_ordinary_source_and_diff_mentions_keep_their_existing_paths() -> None:
    """Covers existing behaviour: the mention-versus-assertion guard.

    A guard, not a falsifier. It proves the widening did not cost the
    behaviour that already worked — somebody writing *about* a diff
    still parses — so it passes at the base by design.
    """
    source = check_content("ordinary.py", "text = '+function hello()'\n", _config())
    assert source["declarations_read"] is True
    hunk = check_content("ordinary.py", "@@ -1 +1 @@\n+text = 1\n", _config())
    assert hunk["declarations_read"] is False
    assert hunk["note"]
