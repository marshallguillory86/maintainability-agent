"""An instruction file an agent never opens is worse than no file.

`--init-agent-standards` writes each agent's standing instructions to the
path *that agent actually reads* — `CLAUDE.md`, `AGENTS.md`,
`.cursor/rules/…`. The table of those conventions will always trail the
market, and the first agent it trailed was a real one: an evaluation of
this tool against IBM Bob had to fall back to `--target generic` because no
Bob convention existed here, and neither the evaluator nor this project's
author knew where Bob reads from.

The wrong fix is to guess a filename. A generated `bob-maintainability.md`
looks configured, satisfies a reviewer glancing at the tree, and is never
opened — which is the failure this file exists to prevent. The right fix is
to let the person who runs the command say, and to refuse when nobody has.

That refusal replaced a fallback which was **unreachable anyway**: the code
generated `{target}-maintainability.md` for an unknown target, while the
CLI's `choices` rejected unknown targets before it could. Removing the
`choices` list without adding the refusal would have made a latent bug
live.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from maintainability_audit.instructions import (
    INSTRUCTION_TARGETS,
    UnknownTarget,
    instruction_path_for_target,
)

ROOT = Path(__file__).resolve().parents[1]


def test_every_known_target_maps_to_the_file_that_agent_reads() -> None:
    """The table is the claim; each entry is a real convention."""
    assert INSTRUCTION_TARGETS["claude-code"] == "CLAUDE.md"
    assert INSTRUCTION_TARGETS["codex"] == "AGENTS.md"
    for target, path in INSTRUCTION_TARGETS.items():
        assert path.strip(), f"{target} has no path"
        assert not Path(path).is_absolute(), f"{target} names an absolute path"


def test_the_cli_and_the_table_cannot_disagree() -> None:
    """The list was written out three times and is now written once.

    `cli.py` repeated it as `choices` and again as the default, so adding a
    target meant remembering all three places or shipping one the CLI
    refused to accept.
    """
    source = (ROOT / "src" / "maintainability_audit" / "cli.py").read_text(encoding="utf-8")

    assert "INSTRUCTION_TARGETS" in source, "the CLI no longer reads the shared table"
    for target in INSTRUCTION_TARGETS:
        assert f'"{target}"' not in source, (
            f"cli.py names the target {target!r} literally; it should read "
            "INSTRUCTION_TARGETS so the two cannot drift"
        )


def test_an_unknown_target_is_refused_rather_than_guessed(tmp_path: Path) -> None:
    """The Bob case. Refusing beats writing a file nobody reads."""
    with pytest.raises(UnknownTarget) as refusal:
        instruction_path_for_target("bob", tmp_path)

    message = str(refusal.value)
    assert "--target-path bob=PATH" in message, (
        "the refusal must say how to proceed, not merely that it failed"
    )
    assert "claude-code" in message, "the refusal must name the targets that do work"


def test_a_supplied_path_is_used_for_an_unknown_target(tmp_path: Path) -> None:
    path = instruction_path_for_target("bob", tmp_path, {"bob": ".bob/instructions.md"})

    assert path == tmp_path / ".bob" / "instructions.md"


def test_a_supplied_path_overrides_a_built_in_convention(tmp_path: Path) -> None:
    """A convention can change, or be site-specific; the caller wins."""
    path = instruction_path_for_target("codex", tmp_path, {"codex": "docs/AGENTS.md"})

    assert path == tmp_path / "docs" / "AGENTS.md"
    assert instruction_path_for_target("codex", tmp_path) == tmp_path / "AGENTS.md"


def test_the_cli_refuses_an_unknown_target_and_writes_nothing(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "maintainability_audit",
         "--config", "maintainability-agent.json", "--init-agent-standards",
         "--target", "bob", "--instructions-output-dir", str(tmp_path)],
        capture_output=True, text=True, timeout=180, cwd=ROOT,
    )

    assert result.returncode == 2, f"expected a refusal, got {result.returncode}"
    assert "--target-path bob=PATH" in result.stderr
    assert not list(tmp_path.iterdir()), "a refused run still wrote something"


def test_the_cli_writes_an_unknown_target_where_it_is_told(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "maintainability_audit",
         "--config", "maintainability-agent.json", "--init-agent-standards",
         "--target", "bob", "--target-path", "bob=.bob/instructions.md",
         "--instructions-output-dir", str(tmp_path)],
        capture_output=True, text=True, timeout=180, cwd=ROOT,
    )

    assert result.returncode == 0, result.stderr[-300:]
    written = tmp_path / ".bob" / "instructions.md"
    assert written.exists(), "the instructions were not written where the caller said"
    assert written.read_text(encoding="utf-8").strip(), "the file is empty"


def test_an_absolute_target_path_is_refused(tmp_path: Path) -> None:
    """`--instructions-output-dir` would be silently ignored otherwise."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "maintainability_audit",
         "--config", "maintainability-agent.json", "--init-agent-standards",
         "--target", "bob", "--target-path", "bob=/tmp/instructions.md",
         "--instructions-output-dir", str(tmp_path)],
        capture_output=True, text=True, timeout=180, cwd=ROOT,
    )

    assert result.returncode == 2
    assert "absolute" in result.stderr
