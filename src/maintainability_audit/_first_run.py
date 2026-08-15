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

import json
import sys
from pathlib import Path

from ._catalog import DEFAULTS, DEPTH_ORDER, LICENSE_POLICIES
from .config import CONFIG_FILENAME, discovered_config

# One retry per question, then the default. An audit must never be able
# to loop forever on a held-down return key.
_ATTEMPTS = 2


def maybe_prompt_first_run(root: Path, explicit_config: str | None) -> None:
    """Ask for depth and license policy, once, when that is appropriate.

    Called before configuration is loaded. Writes the answers to the
    repository root and returns; the caller's ordinary ``discovered_config``
    then finds the file it would have found on any later run, so the
    prompt has no second code path into the audit.
    """
    if explicit_config or discovered_config(root) is not None:
        return
    if not _stdin_is_a_tty():
        return
    if not bool(DEFAULTS.get("prompt_when_interactive")):
        return

    depth = _ask(
        f"Analyzer depth {DEPTH_ORDER} [{DEFAULTS['depth']}]: ",
        tuple(DEPTH_ORDER), str(DEFAULTS["depth"]),
    )
    policy = _ask(
        f"License policy {tuple(sorted(LICENSE_POLICIES))} [{DEFAULTS['license_policy']}]: ",
        tuple(LICENSE_POLICIES), str(DEFAULTS["license_policy"]),
    )
    _persist(root, depth, policy)


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


def _persist(root: Path, depth: str, policy: str) -> None:
    """The answers, in the file every later run already looks for.

    Only the two answered keys are written. Restating the rest of the
    defaults would freeze today's defaults into the repository, so a
    later release could never improve them for this user.
    """
    target = root / CONFIG_FILENAME
    target.write_text(
        json.dumps(
            {"analyzers": {"depth": depth, "license_policy": policy}},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {target}")


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
