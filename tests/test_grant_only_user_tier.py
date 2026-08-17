"""A standing D10 grant is not a setup answer.

Found by self-audit on the D9/D10 slice: persisting an "always" root
grant creates the user-tier config file, and two readers treated any
user config as "the user answered setup" — first-run setup stopped
asking everywhere and the analyzer-pool default flipped on. Presence
must not be read as an answer (the repo's own recorded bug class).
"""

from __future__ import annotations

from pathlib import Path

from maintainability_audit._mcp_setup import setup_pending
from maintainability_audit._user_config import (
    load_user_config,
    persist_root_grant,
    user_config_answers,
)
from maintainability_audit.config import load_config


def test_grant_only_user_config_neither_answers_setup_nor_flips_the_pool(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    persist_root_grant(tmp_path / "granted")

    assert load_user_config() is not None, "the grant itself must persist"
    assert user_config_answers() is None, "a grant is not a setup answer"
    assert setup_pending(repo), "an unconfigured repo must still be asked setup"
    assert load_config(None)["analyzers"]["run"] is False, (
        "a grant-only user tier flipped the pool default on"
    )
