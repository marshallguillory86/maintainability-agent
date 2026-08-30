"""Class D (Grok 63ab820): one first-run setup, the same across surfaces.

The CLI terminal prompt (`_first_run`) and the MCP/chat elicitation
(`_mcp_setup`) are two transports for one setup, not two setups (the arch
calls `_first_run` the "chat-path twin"). The CLI had drifted to a
depth/license-only subset that never asked pool execution, and hand-rolled
its own persist. Because any non-empty config reads as "configured", that
partial file defaulted the analyzer pool on and marked setup complete for
a decision nobody made -- absence read as consent.

The fix routes both transports through the shared `apply_answers`, so a
repository configured at a terminal and one configured in chat end with a
byte-identical config, and pool execution is always an explicit
`analyzers.run` answer.

Population: the setup transports, derived from source -- every entry
module that persists first-run answers must do it through `apply_answers`,
so a future surface (or a regression to a hand-rolled persist) that writes
its own shape fails the structural guard even though only the two present
transports are exercised functionally.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from maintainability_audit import _first_run
from maintainability_audit._mcp_setup import apply_answers, setup_pending
from maintainability_audit.config import CONFIG_FILENAME, analyzers_run_default, load_config

SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"

# The one setup's answers, chosen to differ from the shipped defaults so a
# match proves the answer flowed through, not a coincidence of defaults.
_ANSWERS = {
    "run_pool": "no",
    "depth": "heavy",
    "license_policy": "copyleft-weak",
    "record_scan_history": "no",
}


def _calls_apply_answers(module: str) -> bool:
    tree = ast.parse((SRC / f"{module}.py").read_text(encoding="utf-8"))
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "apply_answers"
        for n in ast.walk(tree)
    )


# The transports of the one setup. `_mcp_setup` defines apply_answers;
# every other transport must call it rather than persist its own shape.
_SETUP_TRANSPORTS = {"_first_run"}


def test_every_setup_transport_persists_through_the_shared_answers() -> None:
    """The population is derived: a transport that hand-rolls its own
    persist (the drift that happened) fails here, so the config shape has
    exactly one author."""
    offenders = [m for m in _SETUP_TRANSPORTS if not _calls_apply_answers(m)]
    assert not offenders, (
        f"setup transports not routed through apply_answers: {offenders}; "
        "one setup means one persist path"
    )


def _cli_first_run(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive the terminal first-run with `_ANSWERS`, answering each prompt
    by keyword so prompt order does not matter."""
    monkeypatch.setattr(_first_run, "_stdin_is_a_tty", lambda: True)

    def respond(prompt: str = "") -> str:
        low = prompt.lower()
        if "pool" in low:
            return _ANSWERS["run_pool"]
        if "depth" in low:
            return _ANSWERS["depth"]
        if "policy" in low or "licen" in low:
            return _ANSWERS["license_policy"]
        if "history" in low:
            return _ANSWERS["record_scan_history"]
        return ""

    monkeypatch.setattr("builtins.input", respond)
    _first_run.maybe_prompt_first_run(root, None)


def test_the_cli_and_the_chat_setup_write_a_byte_identical_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same answers, the two transports, one file. If the CLI wrote a
    different shape (its old depth/license-only subset), these differ."""
    cli_root = tmp_path / "cli"
    cli_root.mkdir()
    _cli_first_run(cli_root, monkeypatch)

    chat_root = tmp_path / "chat"
    chat_root.mkdir()
    apply_answers(chat_root, dict(_ANSWERS))

    cli_config = json.loads((cli_root / CONFIG_FILENAME).read_text(encoding="utf-8"))
    chat_config = json.loads((chat_root / CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert cli_config == chat_config, (
        "the terminal and chat setups disagree on the config they write"
    )


def test_pool_execution_is_an_explicit_answer_not_a_file_side_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`run_pool="no"` must leave the pool off. The old CLI wrote no `run`
    key, so the file's mere existence defaulted the pool on -- the hole."""
    root = tmp_path / "repo"
    root.mkdir()
    _cli_first_run(root, monkeypatch)

    config = json.loads((root / CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert config["analyzers"]["run"] is False, "the pool answer was not persisted"
    resolved = load_config(str(root / CONFIG_FILENAME))
    assert analyzers_run_default(resolved) is False, (
        "a declined pool ran anyway -- file existence overrode the answer"
    )


def test_setup_is_complete_after_the_shared_answers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A terminal setup that answered pool execution completes setup, the
    same as the chat setup does -- one process, one completion state."""
    root = tmp_path / "repo"
    root.mkdir()
    _cli_first_run(root, monkeypatch)
    assert setup_pending(root) is False
