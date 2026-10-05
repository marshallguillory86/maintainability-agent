"""Code a change touches is held to a stricter bar (Decision 15).

A repository adopting a quality gate cannot fix every old long function
first, and a gate that fails on all of them is a gate nobody turns on.
`policy.changed_code` sets stricter function limits, and on a run against a
change only the functions that change touched are held to them; untouched
code is judged by the standard as before.

A function is *touched* when the change added or altered a line inside it —
`git diff --unified=0` lines, so context does not count and a pure deletion
touches nothing. Classes are not held to it: their budget is a container's,
and their methods are functions in their own right.

Two rules from the decision, enforced here rather than trusted:

- **A policy only tightens.** A limit looser than the standard threshold is
  refused when the configuration loads, by name, as `PolicyError` — the
  refusal both doors already turn into a message.
- **It never moves the grade.** Its result is `report["policy"]`, beside the
  score rather than inside `hard_gate_failures`, which the scorer reads.
  `--fail-on-gate` reads both.
"""

from __future__ import annotations

from typing import Any

from ._catalog import PolicyError

#: Each policy key: the standard threshold it may only tighten, the
#: function-metric field it reads, and the name a failure reports.
LIMITS: dict[str, tuple[str, str, str]] = {
    "max_function_lines": ("max_function_lines", "lines", "function_lines"),
    "max_complexity": ("max_complexity", "complexity", "complexity"),
    "max_cognitive_complexity": ("max_cognitive_complexity", "cognitive", "cognitive_complexity"),
}


def changed_code_limits(config: dict[str, Any]) -> dict[str, int]:
    """The configured limits, or empty when the repository sets none."""
    return dict((config.get("policy") or {}).get("changed_code") or {})


def validate(config: dict[str, Any]) -> None:
    """Refuse a limit that is unknown, not a positive integer, or looser than the standard."""
    thresholds = config.get("thresholds") or {}
    for key, value in changed_code_limits(config).items():
        if key not in LIMITS:
            raise PolicyError(
                f"unknown policy.changed_code key {key!r}; expected one of {sorted(LIMITS)}")
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise PolicyError(f"policy.changed_code.{key} must be a positive integer, not {value!r}")
        standard = thresholds.get(LIMITS[key][0])
        if isinstance(standard, int) and value > standard:
            raise PolicyError(
                f"policy.changed_code.{key} is {value}, looser than the standard "
                f"thresholds.{LIMITS[key][0]} of {standard}; a policy may only tighten")


def evaluate(function_metrics: list[Any], touched_lines: dict[str, set[int]],
             config: dict[str, Any], revspec: str) -> dict[str, Any] | None:
    """Every touched function's breaches of the policy, or None without a policy."""
    limits = changed_code_limits(config)
    if not limits:
        return None
    touched = [metric for metric in function_metrics if _touched(metric, touched_lines)]
    return {
        "revspec": revspec,
        "limits": limits,
        "touched_functions": len(touched),
        "failures": [failure for metric in touched for failure in _breaches(metric, limits)],
    }


def failures(report: dict[str, Any]) -> list[dict[str, Any]]:
    """The policy's failures in a finished report; empty when no policy ran."""
    return list((report.get("policy") or {}).get("failures") or [])


def _touched(metric: Any, touched_lines: dict[str, set[int]]) -> bool:
    if getattr(metric, "kind", "function") == "class":
        return False
    lines = touched_lines.get(metric.path)
    if not lines:
        return False
    end = metric.start_line + metric.lines
    return any(metric.start_line <= line < end for line in lines)


def _breaches(metric: Any, limits: dict[str, int]) -> list[dict[str, Any]]:
    found = []
    for key, limit in limits.items():
        _standard, field, measure = LIMITS[key]
        value = getattr(metric, field, None)
        if isinstance(value, int) and value > limit:
            found.append({"path": metric.path, "name": metric.name, "start_line": metric.start_line,
                          "measure": measure, "value": value, "limit": limit})
    return found
