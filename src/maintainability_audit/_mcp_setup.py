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

import json
from pathlib import Path
from typing import Any

from ._catalog import LICENSE_POLICIES
from ._safe_write import write_bounded
from ._user_config import (
    user_config_answers,
    write_user_answers,
)
from .config import CONFIG_FILENAME, discovered_config, load_config
from .config import _configured as _read_config

_DEPTHS = ("baseline", "moderate", "heavy")


class SetupRequired(RuntimeError):
    """A read was asked for a repository that has not been set up.

    The tool answers this case with questions. A resource cannot: it has
    no elicitation seam and returns text or nothing. So it refuses, and
    names the door that can ask — which is better than the alternative
    an audit found on this path, serving the fallback-tier report D26
    exists to prevent (D30).
    """

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


def _economics_questions() -> list[dict[str, Any]]:
    """The declinable ADR 004 ask: one gate choice, three bounds."""
    bounds = (("labor_low", "lower bound", 90),
              ("labor_base", "central estimate", 140),
              ("labor_high", "upper bound", 210))
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
        *(
            {
                "name": name,
                "prompt": f"Labor rate, {label} (per hour).",
                "options": [suggestion],
                "default": suggestion,
            }
            for name, label, suggestion in bounds
        ),
    ]


def _accepted(value: Any) -> bool:
    return str(value).strip().lower() in {"yes", "true", "include", "1"}


def _numeric(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _economics_block(answers: dict[str, Any]) -> dict[str, Any] | None:
    """The ADR 004 shape, or None when declined or incomplete.

    Declining skips the block entirely — an absent economic context is
    a real answer, and a half-filled one would put invented money in a
    report (ADR 004).
    """
    if not _accepted(answers.get("economics")):
        return None
    bounds = {
        name: _numeric(answers.get(f"labor_{name}"))
        for name in ("low", "base", "high")
    }
    if any(value is None for value in bounds.values()):
        return None
    return {
        "version": 1,
        "loaded_engineering_cost_per_hour": {
            name: value for name, value in bounds.items()
        },
    }


def apply_answers(root: Path, answers: dict[str, Any]) -> dict[str, Any]:
    """Persist the answers to both tiers and return the merged config.

    The user tier carries the same payload as the repository file: the
    person answered once, and their next repository should inherit it
    (D13's whole point). Repository config still wins where they later
    diverge.
    """
    payload: dict[str, Any] = {
        "version": 1,
        "analyzers": {
            "run": _accepted(answers.get("run_pool", "yes")),
            "depth": str(answers.get("depth") or "moderate"),
            "license_policy": str(answers.get("license_policy") or "permissive"),
        },
        "presentation": {
            "format": str(answers.get("default_format") or "chat"),
        },
        # The persisted consent that resolves record_history=None ahead
        # of the file-existence rule (decision 4).
        "history": {
            "record": _accepted(answers.get("record_scan_history", "yes")),
        },
    }
    economics = _economics_block(answers)
    if economics is not None:
        payload["economic_context"] = economics

    # Bounded and staged: a dangling symlink at this name carried
    # first-run configuration outside the repository, and `is_file()`
    # reads false on a dangling link so setup believed nothing was
    # there (D34).
    config_path = Path(root) / CONFIG_FILENAME
    write_bounded(
        Path(root), config_path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )
    write_user_answers(payload)
    return load_config(str(config_path))


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
        return False
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


def setup_schema():
    """The one elicitation model for the current question set."""
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
        text_options = all(isinstance(option, str) for option in options)
        kind = Literal[tuple(options)] if text_options else float  # type: ignore[valid-type]
        fields[question["name"]] = (
            kind,
            Field(default=question["default"], description=question["prompt"]),
        )
    return create_model("FirstRunSetup", **fields)
