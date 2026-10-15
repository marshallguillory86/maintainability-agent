"""Child-only probe for D231; inert unless `MA_D231_CHILD=1` is set.

Written by the Claude Sonnet test seat (Codex at its usage limit); Codex reviews.

`test_suite_isolation.py` spawns pytest on this file with git's location
variables pointing at a sentinel repository. The normal suite never
collects it (no `test_` prefix); a path named on the command line is
collected regardless.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(
    os.environ.get("MA_D231_CHILD") != "1",
    reason="only meaningful when spawned by the D231 isolation test",
)
def test_fixture_repository_commit(tmp_path: Path) -> None:
    """What every fixture in the suite does: init, configure, commit."""
    repo = tmp_path / "fixture"
    repo.mkdir()
    for args in (
        ["init", "-q"],
        ["config", "user.name", "X"],
        ["config", "user.email", "x@example.invalid"],
        ["commit", "-q", "--allow-empty", "-m", "fixture"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True)
