"""Checked-in semantic policy — repository intent, loaded and bounded.

ADR 003 option C: configuration supplies domain facts the generic
scanner cannot infer. It does not get to declare score weights, relabel
a candidate as a universal fact, or smuggle in a naming convention.
That last rule is structural here: paths are exact, never globs, so a
policy physically cannot say "every `*_id` must be a value object".
"""
from __future__ import annotations

from typing import Any

_GLOB_CHARS = set("*?[]")


def _exact_paths(entry: dict[str, Any]) -> list[str]:
    paths = [str(path) for path in entry.get("paths") or []]
    if not paths:
        raise ValueError(f"semantic_policy entry {entry.get('name')!r} names no paths")
    for path in paths:
        if set(path) & _GLOB_CHARS:
            raise ValueError(
                f"semantic_policy entry {entry.get('name')!r} uses a pattern "
                f"({path!r}); v1 policy takes exact paths only, never a "
                "convention over names"
            )
    return paths


def _named_entry(entry: dict[str, Any], block: str, required: tuple[str, ...]) -> dict[str, Any]:
    """Validate one policy entry and start its record.

    Both entry kinds are a named, path-scoped rule; only the fields that
    describe the rule differ. Requiring the shared half in one place
    keeps a rule that holds for `domain_types` from quietly not holding
    for `operations` — the way near-copies drift.
    """
    missing = [name for name in required if not entry.get(name)]
    if missing:
        raise ValueError(
            f"semantic_policy {block} entries need {' and '.join(required)}"
        )
    return {"name": str(entry["name"]), "paths": _exact_paths(entry)}


def _domain_type(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        **_named_entry(entry, "domain_types", ("name", "required_type")),
        "boundary": str(entry.get("boundary") or "public"),
        "symbol": str(entry.get("symbol") or ""),
        "required_type": str(entry["required_type"]),
    }


def _operation(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        **_named_entry(entry, "operations", ("name",)),
        "capability_type": str(entry.get("capability_type") or ""),
        "operation_contract": str(entry.get("operation_contract") or ""),
    }


def load_semantic_policy(config: dict[str, Any]) -> dict[str, Any] | None:
    """The validated policy block, or None when the repository has none.

    None is a real answer with a guaranteed consequence: no class-policy
    finding can exist (ADR 003 invariant 3). A malformed policy raises
    rather than degrades — a policy silently narrowed to its parseable
    half would report violations against rules nobody wrote.
    """
    block = config.get("semantic_policy")
    if not block:
        return None
    version = block.get("version")
    if version != 1:
        raise ValueError(f"semantic_policy version {version!r} is not supported (expected 1)")
    return {
        "version": 1,
        "domain_types": [_domain_type(entry) for entry in block.get("domain_types") or []],
        "operations": [_operation(entry) for entry in block.get("operations") or []],
    }
