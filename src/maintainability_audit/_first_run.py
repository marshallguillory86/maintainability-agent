"""The interactive first run: ask once, write the answer down, never again.

Release-plan 6.1, and its exit condition is the whole design: *"Prompts
only on a TTY with no config; never in CI; the answer persists."* Every
clause is a refusal —

- **Only on a TTY.** A prompt in a pipeline is a hung build. The check
  is `sys.stdin.isatty()`, not an environment-variable heuristic,
  because CI systems disagree about `$CI` and none of them attach a
  terminal to stdin.
- **Only with no config.** A repository that has chosen its depth and
  policy is never re-asked, and its file is never rewritten. The prompt
  creates configuration where none exists; it does not revise it.
- **The answer persists** to ``maintainability-agent.json`` at the
  repository root — the same file ``discovered_config`` already reads.
  Persistence is not a second mechanism, which is what keeps the second
  run silent for free.

``analyzers.prompt_when_interactive`` gates the whole thing. The key
sat in ``DEFAULTS``, documented as reserved, read by nothing, from
0.6 until now.
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

from .config import read_operator_file
from ._catalog import DEFAULTS, DEPTH_ORDER, LICENSE_POLICIES
from .config import CONFIG_FILENAME, PathNotAllowed, discovered_config

# One retry per question, then the default. An audit must never be able
# to loop forever on a held-down return key.
_ATTEMPTS = 2


def maybe_prompt_first_run(root: Path, explicit_config: str | None) -> None:
    """Run first-run setup at a terminal, once, through the shared answers.

    One setup, not one per surface. `_mcp_setup` asks the identical
    question set over MCP elicitation and persists through the same
    `apply_answers`; this is that setup's terminal transport (the arch
    "chat-path twin"). The CLI had drifted to a depth/license-only subset
    that never answered pool execution, so the mere existence of the file
    it wrote defaulted the pool on and marked setup complete for a
    decision nobody made (Grok 63ab820 audit). Asking `run_pool` and
    `record_scan_history` here, and persisting through `apply_answers`,
    makes a repository configured at a terminal identical to one
    configured in chat.

    Economics (a staged, declinable add) and the presentation format
    (asked every invoke, ADR 011) keep their own prompts. Writes the
    config `discovered_config` then finds on any later run, so the prompt
    has no second code path into the audit.
    """
    if explicit_config or discovered_config(root) is not None:
        return
    if not _stdin_is_a_tty():
        return
    if not bool(DEFAULTS.get("prompt_when_interactive")):
        return

    from ._mcp_setup import apply_answers

    answers = {
        "run_pool": _ask(
            "Run the external analyzer pool? (yes/no) [yes]: ", ("yes", "no"), "yes"),
        "depth": _ask(
            f"Analyzer depth {DEPTH_ORDER} [{DEFAULTS['depth']}]: ",
            tuple(DEPTH_ORDER), str(DEFAULTS["depth"])),
        "license_policy": _ask(
            f"License policy {tuple(sorted(LICENSE_POLICIES))} [{DEFAULTS['license_policy']}]: ",
            tuple(LICENSE_POLICIES), str(DEFAULTS["license_policy"])),
        "record_scan_history": _ask(
            "Record scan history so recurrence can be tracked? (yes/no) [yes]: ",
            ("yes", "no"), "yes"),
        # Decision 9 amendment (Class 5): disclosed, default-off opt-in to
        # run the tree's own suite. Asked on every surface so a repository
        # configured at a terminal and one in chat stay byte-identical.
        "run_tests": _ask(
            "Run this repository's test suite for coverage? THIS EXECUTES THE "
            "TREE. (yes/no) [no]: ", ("yes", "no"), "no"),
    }
    apply_answers(root, answers)
    print(f"Wrote {root / CONFIG_FILENAME}")


def _stdin_is_a_tty() -> bool:
    try:
        return bool(sys.stdin.isatty())
    except (AttributeError, ValueError):
        # A closed or replaced stdin is not a terminal. Refusing to
        # prompt is the safe reading in every such environment.
        return False


def _ask(question: str, allowed: tuple[str, ...], default: str) -> str:
    """One answer from the catalog's vocabulary, or the default.

    An unknown answer gets one correction and then the default — the
    same value a non-interactive run would have used — rather than an
    error. First contact with the tool should not end in a traceback
    over a typo.
    """
    for _ in range(_ATTEMPTS):
        answer = input(question).strip().lower()
        if not answer:
            return default
        if answer in allowed:
            return answer
        print(f"  {answer!r} is not one of {allowed}")
    return default


# The three presentations, and what each means (ADR 011). Order matters:
# the first is what Enter selects.
PRESENTATIONS = ("chat", "markdown", "html")


def ask_presentation() -> str:
    """Which of the three skins, asked at every interactive invoke.

    Never persisted, deliberately (ADR 011 §3): a remembered answer is a
    flag the user cannot see, and the whole point of asking is that
    today's audience may not be yesterday's. Enter is chat, because chat
    is where the question was asked.
    """
    answer = input(
        "Report format — chat (Enter), markdown, or html: "
    ).strip().lower()
    if answer in PRESENTATIONS:
        return answer
    if answer:
        print(f"  {answer!r} is not one of {PRESENTATIONS}; using chat")
    return "chat"


def maybe_prompt_economics(root: Path, config: dict) -> None:
    """Ask for the labor range once, under exactly the 6.1 silence rules.

    Fires only at a TTY, only when no labor range is configured or
    supplied by environment for this run, and never when the operator
    set ``analyzers.prompt_when_interactive`` to false. Answers merge
    into ``maintainability-agent.json`` — merge, not overwrite, because
    the 6.1 ask may have written the analyzers block moments earlier.
    Enter declines: nothing is written and no block is produced, which
    is the honest reading of a question the user waved away.
    """
    from ._economics import economic_context_from

    if not _stdin_is_a_tty():
        return
    if (config.get("analyzers") or {}).get(
        "prompt_when_interactive", DEFAULTS["prompt_when_interactive"]
    ) is False:
        return
    if economic_context_from(config) is not None:
        return

    print("Optional: a labor-cost range adds a cost scenario beside the score.")
    labor: dict[str, float] = {}
    for bound in ("low", "base", "high"):
        answer = input(f"Loaded labor cost per hour, {bound} (Enter to skip): ").strip()
        if not answer:
            return  # declined; a partial range is not a range
        labor[bound] = float(answer)

    if not 0 < labor["low"] <= labor["base"] <= labor["high"]:
        print(f"  ignored: expected low <= base <= high, got {labor}")
        return

    from ._safe_write import write_bounded

    target = root / CONFIG_FILENAME
    # A symlink here would redirect both the read of the existing config
    # and the write. `write_bounded` refuses it on the write; refuse it
    # before the read too, so a linked config cannot be read out either.
    if target.is_symlink():
        raise PathNotAllowed(
            f"{target} is a symlink; the audited tree cannot redirect "
            "where first-run configuration is read or written."
        )
    existing = json.loads(read_operator_file(target)) if target.exists() else {}
    existing["economic_context"] = {
        "version": 1,
        "loaded_engineering_cost_per_hour": labor,
    }
    written = write_bounded(root, target, json.dumps(existing, indent=2) + "\n")
    config["economic_context"] = existing["economic_context"]
    print(f"Wrote {written}")


def _input_with_default(prompt: str, default: str) -> str:
    """`input()` with the line pre-filled, where the terminal allows it.

    `readline` is what makes the default *editable* rather than merely
    described: the text is inserted into the line buffer, so Enter submits
    it, backspace edits it, and clearing it returns the empty string that
    has always meant "cancel". Without that, a pre-filled default and a
    blank-means-cancel rule cannot both be true on one keystroke.

    Absent or unusable `readline` — Windows without pyreadline, a terminal
    that refuses the hook — falls back to a plain `input()`. The default is
    still named in the prompt text, so the operator loses the keystroke and
    not the information. Never let this be the thing that fails a setup.
    """
    if not default:
        return input(prompt)
    try:
        import readline
    except ImportError:
        return input(prompt)

    def _prefill() -> None:
        readline.insert_text(default)
        readline.redisplay()

    try:
        readline.set_startup_hook(_prefill)
        return input(prompt)
    except Exception:  # noqa: BLE001 - a cosmetic hook must not fail setup
        return input(prompt)
    finally:
        # Global state: a hook left installed would pre-type this command
        # into whatever the session asks next.
        with contextlib.suppress(Exception):
            readline.set_startup_hook()


def maybe_prompt_test_command(root: Path, config: dict) -> None:
    """Ask the opted-in operator for the test command, once -- the CLI half
    of the Class 5 second stage, mirroring the labor-rate ask. Fires only at
    a TTY, only when the suite was opted into and no command is stored, and
    a blank answer cancels the opt-in. Nothing runs until a command exists.

    Where the tree's manifests name a runner, the line is **pre-filled**
    with that command rather than merely mentioning it, so this surface and
    the MCP one carry the same default in the same field: Enter accepts,
    editing replaces, and clearing the line cancels exactly as before.
    """
    import shlex

    if not _stdin_is_a_tty():
        return
    if (config.get("analyzers") or {}).get(
        "prompt_when_interactive", DEFAULTS["prompt_when_interactive"]
    ) is False:
        return
    if not (config.get("test_execution") or {}).get("requested"):
        return
    if (config.get("expected_commands") or {}).get("test"):
        return

    from ._test_commands import suggested_test_command

    suggested = suggested_test_command(root)
    detected = " ".join(suggested.command) if suggested is not None else ""
    prompt = (
        f"Detected `{detected}` from {suggested.evidence}. The command that "
        "runs this repository's test suite (Enter to accept, clear the line "
        "to cancel running it): "
        if suggested is not None else
        "The command that runs this repository's test suite, e.g. `pytest` "
        "(Enter to cancel running it): "
    )
    answer = _input_with_default(prompt, detected).strip()

    from ._safe_write import write_bounded

    target = root / CONFIG_FILENAME
    if target.is_symlink():
        raise PathNotAllowed(
            f"{target} is a symlink; the audited tree cannot redirect "
            "where first-run configuration is read or written."
        )
    existing = json.loads(read_operator_file(target)) if target.exists() else {}
    if answer:
        commands = dict(existing.get("expected_commands") or {})
        commands["test"] = shlex.split(answer)
        existing["expected_commands"] = commands
        config["expected_commands"] = commands
    else:
        existing["test_execution"] = {"requested": False}  # declined cancels the opt-in
        config["test_execution"] = {"requested": False}
    written = write_bounded(root, target, json.dumps(existing, indent=2) + "\n")
    print(f"Wrote {written}")
