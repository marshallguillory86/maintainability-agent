"""First-run setup over the local MCP boundary — D2, D3, D11.

First contact with an unconfigured repository is detectable (D13's
state file plus both config tiers absent), and the register says what
must happen then: ask, as structured choices with disclosed defaults,
then write the answers so the questions never repeat. This module owns
the three pieces: the question set, the persistence of answers to both
configuration tiers, and the elicitation round-trip through the MCP
context.

The questions are one elicitation, not five: the MCP elicitation
contract is a single flat object of primitive fields, and one modal
beats a five-step wizard in every host. A host that declines — or
cannot elicit at all — gets the same questions back as data, so its own
question UI can ask and call again.

What no longer happens is the audit. This module used to describe the
degradation path as costing the user nothing, because "the audit
proceeds on built-in defaults" — which meant a first-time user was
handed a letter grade computed with the analyzer pool off while the
question that turns the pool on rode along unasked (D26). Setup is a
precondition now: no answers, no audit. And answering does not start
one either — configuring the agent and running it are separate
decisions, and the user makes both (D27).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ._catalog import LICENSE_POLICIES
from ._setup_errors import SetupRequired as SetupRequired
from ._setup_persist import (
    BOUNDS,
    _accepted,
    _apply_bounds,
    _apply_command,
    _economics_block,
    _is_bounds_only,
    _is_command_only,
    _persist_answers,
)
from ._user_config import (
    user_config_answers,
)
from .config import _configured as _read_config
from .config import discovered_config, load_config

_DEPTHS = ("baseline", "moderate", "heavy")


# The composition note, verbatim requirement: a user deciding about the
# pool must understand what discovery and scanning will actually do.
_POOL_PROMPT = (
    "Run the validated analyzer pool? It is the primary evidence source; "
    "the built-in detectors always run as the fallback for whatever the "
    "pool cannot measure. Choosing no means built-ins only, and the "
    "report will label its evidence fallback-tier."
)


def setup_questions(config: dict[str, Any]) -> list[dict[str, Any]]:
    """The first-run question set: structured choices, defaults disclosed.

    Derived from the same vocabulary the config validates against
    (depths, license policies), so an option offered here is never an
    option `settings_from` would refuse.
    """
    del config  # the shipped vocabulary is not repository-dependent today
    return [
        {
            "name": "run_pool",
            "prompt": _POOL_PROMPT,
            "options": ["yes", "no"],
            "default": "yes",
        },
        {
            "name": "depth",
            "prompt": "Analyzer depth tier: how much of the pool is eligible.",
            "options": list(_DEPTHS),
            "default": "moderate",
        },
        {
            "name": "license_policy",
            "prompt": "License policy for analyzer selection.",
            "options": sorted(LICENSE_POLICIES),
            "default": "permissive",
        },
        *_economics_questions(),
        *run_tests_question(),
        {
            "name": "default_format",
            "prompt": "Default report presentation for this user.",
            "options": ["chat", "markdown", "html"],
            "default": "chat",
        },
        {
            # Decision 4: recording is a disclosed choice the person
            # makes, never something inferred from client capability.
            "name": "record_scan_history",
            "prompt": (
                "Record scan history (.maintainability/history.jsonl) so "
                "later audits can track recurrence and escalate repeat "
                "findings?"
            ),
            "options": ["yes", "no"],
            "default": "yes",
        },
    ]


def economics_bound_questions() -> list[dict[str, Any]]:
    """The three rates, asked only of someone who said yes to the gate."""
    return [
        {
            "name": name,
            "prompt": f"Labor rate, {label} (per hour).",
            "options": [suggestion],
            "default": suggestion,
        }
        for name, label, suggestion in BOUNDS
    ]


def _economics_questions() -> list[dict[str, Any]]:
    """The gate alone. The bounds are a second ask, and only on yes.

    This returned the gate *and* all three rates in one flat model, so
    a user whose answer was "skip" — the default — was still asked three
    labor-rate questions for a thing they had just declined. The
    docstring called it "the declinable ask" while nothing about it was
    declinable.

    It also lost the opposite case. `_economics_block` needs all three
    rates and returns None without them, so answering "include" in a
    round that carried no rates wrote no economic context at all: the
    user asked for money in the report and silently did not get it.
    Staging the ask fixes both, because the bounds are now asked exactly
    when they are wanted and setup stays pending until they arrive.
    """
    return [
        {
            "name": "economics",
            "prompt": (
                "Add the economic scenario (loaded labor rate per hour) "
                "beside the score? Skip leaves money out of reports."
            ),
            "options": ["include", "skip"],
            "default": "skip",
        },
    ]


def apply_answers(root: Path, answers: dict[str, Any]) -> dict[str, Any]:
    """Assemble a full reply's payload and hand it to `_persist_answers`.
    A staged reply (only rates, or only the test command) merges instead."""
    if _is_bounds_only(answers):
        return _apply_bounds(root, answers)
    if _is_command_only(answers):
        return _apply_command(root, answers)
    payload: dict[str, Any] = {
        "version": 1,
        "analyzers": {
            "run": _accepted(answers.get("run_pool", "yes")),
            "depth": str(answers.get("depth") or "moderate"),
            "license_policy": str(answers.get("license_policy") or "permissive"),
        },
        "presentation": {"format": str(answers.get("default_format") or "chat")},
        # Persisted consent for record_history=None, ahead of file-existence (decision 4).
        "history": {"record": _accepted(answers.get("record_scan_history", "yes"))},
        # Decision 9 (Class 5): the disclosed opt-in to run the tree's own
        # suite; the command is a staged second ask.
        "test_execution": {"requested": _accepted(answers.get("run_tests", "no"))},
    }
    economics = _economics_block(answers)
    if economics is not None:
        payload["economic_context"] = economics
    return _persist_answers(root, payload)


def economics_bounds_pending(root: Path) -> bool:
    """True when the user asked for the economic scenario and has no rates.

    The second stage of the first-run ask. It exists so the three labor
    questions are put only to someone who wants them, and so that
    wanting them is not silently discarded.
    """
    discovered = discovered_config(Path(root))
    stored = _read_config(Path(discovered)) if discovered is not None else None
    block = (stored or {}).get("economic_context")
    if not isinstance(block, dict):
        return False
    return bool(block.get("requested")) and not block.get(
        "loaded_engineering_cost_per_hour")


def run_tests_question() -> list[dict[str, Any]]:
    """The Class 5 opt-in to run the tree's own suite — the one place the
    agent may execute the audited code, default off (Decision 9 amendment)."""
    return [{
        "name": "run_tests",
        "prompt": (
            "Run this repository's documented test command so the report "
            "can measure test effectiveness (coverage / pass-fail)? THIS "
            "EXECUTES THE TREE, including any network the suite uses. Skip "
            "leaves test effectiveness unscored and says so."
        ),
        "options": ["yes", "no"],
        "default": "no",
    }]


def run_tests_pending(root: Path) -> bool:
    """A configured repository whose config predates the test-suite opt-in:
    it carries the `history` consent a first-run setup writes but no
    `test_execution` key, so the operator was never offered the opt-in. Used
    to surface it as a discovery line on the run/reconfigure choice — not a
    forced re-ask, which would break the configured-repo contract. A present
    key (even `requested: false`) means it was asked. Gated on `history` so a
    hand-maintained config — paths, thresholds, no setup answers — is not
    mistaken for a lapsed first run (this repository included).
    """
    discovered = discovered_config(Path(root))
    stored = _read_config(Path(discovered)) if discovered is not None else None
    return (isinstance(stored, dict) and "history" in stored
            and "test_execution" not in stored)


def test_command_questions() -> list[dict[str, Any]]:
    """The one command, asked only of someone who opted into running it.

    A free-text answer (empty options), the second stage of the opt-in the
    way the labor rates are the second stage of the economic scenario.
    """
    return [{
        "name": "test_command",
        "prompt": (
            "The command that runs this repository's test suite "
            "(e.g. `pytest`, `npm test`). It runs in the repository root, "
            "and leaving it blank cancels the opt-in."
        ),
        "options": [],
        "default": "",
    }]


def test_command_pending(root: Path) -> bool:
    """True when the operator opted to run tests and no command is stored.

    The second stage of the opt-in, mirroring `economics_bounds_pending`:
    the command is asked only of someone who said yes, and saying yes is
    not silently discarded.
    """
    discovered = discovered_config(Path(root))
    stored = _read_config(Path(discovered)) if discovered is not None else None
    if not isinstance(stored, dict):
        return False
    requested = bool((stored.get("test_execution") or {}).get("requested"))
    command = (stored.get("expected_commands") or {}).get("test")
    return requested and not command


def setup_pending(root: Path) -> bool:
    """Whether first-run setup still has questions to ask for `root`.

    Configuration absence only, never seen-state (M1): D2's stop
    condition is *written answers*. A declined ask is re-asked on the
    next call — the memo that an audit completed (D13) answers a
    different question and must not silence this one.

    Answers, not a file. This asked `discovered_config`, which is an
    `is_file()` check, so an empty `{}` ended setup and the repository
    was treated as configured while nobody had answered anything (D30).
    A file that parses to nothing is the same state as no file. A file
    that does not parse is neither, and says so rather than surfacing a
    `JSONDecodeError` from somewhere deeper.
    """
    # One parser, shared with `load_config`. This had its own
    # `json.loads` and its own exception, so a JSON array made the MCP
    # tool ask the setup questions while the CLI refused the file — one
    # repository state, two answers, which is the exact defect D32 set
    # out to remove and left standing here (D33).
    discovered = discovered_config(Path(root))
    if discovered is not None and _read_config(Path(discovered)):
        # Configured, unless a second-stage ask is still open: the economic
        # rates for someone who wanted the scenario, or the test command for
        # someone who opted to run the suite. Both are stage two of an ask
        # already begun, not a new one.
        return economics_bounds_pending(root) or test_command_pending(root)
    return user_config_answers() is None


async def maybe_elicit_setup(context: Any, root: Path) -> dict[str, Any] | None:
    """One structured elicitation on first contact; the merged config on accept.

    ``None`` for every other outcome — already configured, declined,
    or a host that cannot elicit. The caller then publishes the same
    questions as data and returns them unanswered; it does not audit.
    D3's degradation rule used to end "never hang an audit", and the
    audit it protected was one nobody had asked for (D26).

    Accepting writes the answers and still returns no report: the next
    call offers run-or-reconfigure, and the user says when (D27).
    """
    if context is None or not setup_pending(root):
        return None
    questions = setup_questions(load_config(None))
    try:
        outcome = await context.elicit(
            message=(
                "First run in this repository and no configuration found — "
                "configure maintainability-agent now? Defaults are "
                "pre-selected."
            ),
            schema=_schema_for(questions),
        )
    except Exception:  # noqa: BLE001 - any transport/capability failure means "cannot ask"
        return None
    if getattr(outcome, "action", "decline") != "accept":
        return None
    data = getattr(outcome, "data", None) or getattr(outcome, "content", None)
    answers = data.model_dump() if hasattr(data, "model_dump") else dict(data or {})
    return apply_answers(Path(root), answers)


def setup_schema(root: Path | None = None):
    """The elicitation model for whichever stage this repository is in.

    Two stages, because the three labor rates are only wanted by
    someone who said yes to the gate. Asking them of everyone is what
    Marshall called basic logic broken, and he was right: the default
    answer to the gate is "skip".
    """
    if root is not None and economics_bounds_pending(root):
        return _schema_for(economics_bound_questions())
    if root is not None and test_command_pending(root):
        return _schema_for(test_command_questions())
    return _schema_for(setup_questions(load_config(None)))


def _schema_for(questions: list[dict[str, Any]]):
    """The one flat elicitation model, built from the question set.

    Constructed lazily from pydantic (which arrives with the mcp
    extra) so importing this module never requires MCP to be installed.
    """
    from typing import Literal

    from pydantic import Field, create_model

    fields: dict[str, Any] = {}
    for question in questions:
        options = question["options"]
        if not options:
            kind: Any = str  # a free-text answer, e.g. a test command
        elif all(isinstance(option, str) for option in options):
            kind = Literal[tuple(options)]  # type: ignore[valid-type]
        else:
            kind = float
        fields[question["name"]] = (
            kind,
            Field(default=question["default"], description=question["prompt"]),
        )
    return create_model("FirstRunSetup", **fields)
