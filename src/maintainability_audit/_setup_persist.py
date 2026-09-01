"""Persisting a first-run/reconfigure reply: the values, the economics
block, and the three writers (`_apply_bounds`, `_apply_command`, and the
full merge `_persist_answers`). Split from `_mcp_setup` for headroom
(#127); `apply_answers` stays there and delegates here. Imports nothing
from `_mcp_setup`, so the graph stays acyclic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._safe_write import write_bounded
from ._setup_errors import SetupRequired
from ._user_config import write_user_answers
from .config import CONFIG_FILENAME, discovered_config, load_config
from .config import _configured as _read_config

BOUNDS = (("labor_low", "lower bound", 90),
          ("labor_base", "central estimate", 140),
          ("labor_high", "upper bound", 210))


def _accepted(value: Any) -> bool:
    return str(value).strip().lower() in {"yes", "true", "include", "1"}


def _numeric(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _economics_block(answers: dict[str, Any]) -> dict[str, Any] | None:
    """The ADR 004 shape, a request awaiting its rates, or None.

    Declining skips the block entirely — an absent economic context is
    a real answer, and a half-filled one would put invented money in a
    report (ADR 004).

    Accepting without rates is neither of those. It used to return None,
    which is the same value as declining, so someone who asked for the
    economic scenario was recorded as having refused it. It now records
    the request, and `economics_bounds_pending` reads that to ask for
    the rates on the next call.
    """
    if not _accepted(answers.get("economics")):
        return None
    bounds = {
        name: _numeric(answers.get(f"labor_{name}"))
        for name in ("low", "base", "high")
    }
    if any(value is None for value in bounds.values()):
        return {"version": 1, "requested": True}
    if not 0 < bounds["low"] <= bounds["base"] <= bounds["high"]:
        # Refused here rather than written and left to explode later.
        # Setup accepted low=-1 and wrote both tiers happily; the next
        # `action="run"` raised a raw ValueError from the scoring path,
        # so the person who broke it was two calls away from the message.
        raise SetupRequired(
            "labor rates must satisfy 0 < low <= base <= high; got "
            f"low={bounds['low']}, base={bounds['base']}, high={bounds['high']}. "
            "Answer the three rates again."
        )
    return {
        "version": 1,
        "loaded_engineering_cost_per_hour": {
            name: value for name, value in bounds.items()
        },
    }


def _is_bounds_only(answers: dict[str, Any]) -> bool:
    """A stage-two reply: the rates, and nothing the first stage asked."""
    names = {name for name, _, _ in BOUNDS}
    given = {key for key, value in answers.items() if value is not None}
    return bool(given) and given <= names


def _apply_bounds(root: Path, answers: dict[str, Any]) -> dict[str, Any]:
    """Fill the rates into a configuration that already has its answers.

    A merge, never a rebuild: the first stage's answers are already
    written, and constructing the payload again from a reply that
    carries only rates would reset every one of them to a default.
    """
    economics = _economics_block({"economics": "include", **answers})
    discovered = discovered_config(Path(root))
    stored = dict(_read_config(Path(discovered)) or {}) if discovered else {}
    stored["economic_context"] = economics
    config_path = Path(root) / CONFIG_FILENAME
    write_bounded(
        Path(root), config_path,
        json.dumps(stored, indent=2, sort_keys=True) + "\n",
    )
    write_user_answers(stored)
    return load_config(str(config_path))


def _is_command_only(answers: dict[str, Any]) -> bool:
    """A stage-two reply carrying only the test command."""
    given = {key for key, value in answers.items() if value is not None}
    return given == {"test_command"}


def _apply_command(root: Path, answers: dict[str, Any]) -> dict[str, Any]:
    """Merge the test command into a configuration that already has its
    answers, exactly as `_apply_bounds` merges the rates. A blank command
    cancels the opt-in rather than looping the ask forever."""
    import shlex

    command = str(answers.get("test_command") or "").strip()
    discovered = discovered_config(Path(root))
    stored = dict(_read_config(Path(discovered)) or {}) if discovered else {}
    if command:
        commands = dict(stored.get("expected_commands") or {})
        commands["test"] = shlex.split(command)
        stored["expected_commands"] = commands
    else:
        stored["test_execution"] = {"requested": False}
    config_path = Path(root) / CONFIG_FILENAME
    write_bounded(
        Path(root), config_path,
        json.dumps(stored, indent=2, sort_keys=True) + "\n",
    )
    write_user_answers(stored)
    return load_config(str(config_path))


def _persist_answers(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Merge the answers over the existing config and write both tiers.

    Merge, never overwrite (D13: the user tier inherits to the next repo):
    a reconfigure must keep the fields the wizard never asks about — paths,
    thresholds, gates, commands, risk patterns, instruction pack, analyzer
    sub-keys beyond run/depth/license. Writing `payload` wholesale erased
    them — the bug that wiped a repository's scoping on reconfigure.
    """
    config_path = Path(root) / CONFIG_FILENAME
    discovered = discovered_config(Path(root))
    merged = dict(_read_config(Path(discovered)) or {}) if discovered else {}
    for section in ("analyzers", "presentation", "history", "test_execution"):
        merged[section] = {**merged.get(section, {}), **payload[section]}
    merged["version"] = 1
    if "economic_context" in payload:
        merged["economic_context"] = payload["economic_context"]
    write_bounded(
        Path(root), config_path,
        json.dumps(merged, indent=2, sort_keys=True) + "\n",
    )
    write_user_answers(payload)
    return load_config(str(config_path))
