"""An interactive terminal asks the setup questions chat and MCP ask.

`docs/cli.md` says a first run on a TTY is "the **same** setup questions
as chat/MCP", and `_first_run`'s own docstring calls itself "one setup,
not one per surface". It asked five of seven. The missing one was the
economic scenario, so a terminal user was never offered money in their
reports and nothing told them the option existed (D150).

The claim was true of every question except the one nobody noticed was
absent — which is why the population here is **derived from
`setup_questions`**, the shared definition both other surfaces render,
rather than listed by hand. A question added there without teaching the
terminal about it fails this file instead of silently reaching only two
of the three doors.

Two questions are legitimately absent and are named with their reason,
because an exemption nobody states is indistinguishable from an
oversight — the exact shape of the defect this file exists to close.
"""
from __future__ import annotations

import ast
from pathlib import Path

from maintainability_audit._mcp_setup import setup_questions
from maintainability_audit.config import load_config

ROOT = Path(__file__).resolve().parents[1]
FIRST_RUN = ROOT / "src" / "maintainability_audit" / "_first_run.py"

#: Asked somewhere other than the first-run reply, with the reason.
ASKED_ELSEWHERE = {
    # ADR 011 §3: asked on every invoke, never persisted, because a
    # remembered answer is a flag the user cannot see.
    "default_format": "ask_presentation, on every interactive invoke",
}


def _terminal_answer_keys() -> set[str]:
    """The keys `maybe_prompt_first_run` puts in its answers dict.

    Read from the source rather than by running it, because running it
    needs a TTY and thirteen scripted answers — and a test that mocks
    the prompt loop would pass on a function that asks nothing.
    """
    tree = ast.parse(FIRST_RUN.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "maybe_prompt_first_run"):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Dict):
                keys = {k.value for k in inner.keys if isinstance(k, ast.Constant)}
                if "depth" in keys:          # the answers dict, not some other literal
                    return keys
    raise AssertionError("maybe_prompt_first_run no longer builds an answers dict")


def test_the_terminal_asks_every_setup_question() -> None:
    """Derived from the shared definition, so a new question cannot hide."""
    shared = {q["name"] for q in setup_questions(load_config(None))}
    assert shared, "setup_questions returned nothing; this comparison is vacuous"

    asked = _terminal_answer_keys()
    missing = shared - asked - set(ASKED_ELSEWHERE)
    assert not missing, (
        f"the interactive terminal does not ask {sorted(missing)}, which "
        "chat and MCP both ask. docs/cli.md promises the same questions on "
        "every surface: add the prompt, or name the question in "
        "ASKED_ELSEWHERE with the reason it is asked somewhere else"
    )


def test_every_stated_exemption_is_a_real_question() -> None:
    """An exemption for a question that no longer exists hides the next one.

    Covers existing behaviour: this guards the exemption list above
    rather than the fix, so it passes at any base where the names are
    real.
    """
    shared = {q["name"] for q in setup_questions(load_config(None))}
    stale = sorted(set(ASKED_ELSEWHERE) - shared)
    assert not stale, (
        f"ASKED_ELSEWHERE names {stale}, which setup_questions no longer "
        "asks; a stale exemption silently excuses a real gap later"
    )


def test_the_economic_scenario_is_among_them() -> None:
    """The instance D150 was reported from, pinned by name.

    The sweep above is the check; this is the reproduction. It fails
    loudly on the specific regression rather than leaving a reader to
    infer which question went missing.
    """
    assert "economics" in _terminal_answer_keys(), (
        "the terminal stopped asking the economic scenario; a TTY user is "
        "again never offered money in their reports (D150)"
    )
