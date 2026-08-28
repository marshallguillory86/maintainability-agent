"""D40: a repository's regex cannot hang the host that audits it.

`risk_patterns` are compiled from the audited repository's own
configuration and applied to every source line. Python's `re` has no
timeout and no step limit, so one nested quantifier is a denial of
service — an audit's `(a+)+$` against thirty-one characters had not
finished after ten seconds, and would not have finished this week.

The security policy names crafted-configuration denial of service as in
scope, which makes this a promise the code was breaking rather than a
new requirement someone invented.

Measured, not pattern-matched. Recognising "dangerous regexes"
syntactically means a blocklist that is simultaneously leaky and prone
to refusing honest patterns; running the thing against a probe asks the
only question that matters. The probe has to be short enough to
*return*, which is why there are two of them — see the constants.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from maintainability_audit.config import DEFAULT_CONFIG
from maintainability_audit.duplication import _compiled_within_budget, risk_findings

# Each is a distinct shape of catastrophic backtracking, and the last
# grows slowly enough that a single short probe misses it.
BOMBS = [
    pytest.param(r"(a+)+$", id="nested-plus"),
    pytest.param(r"(a*)*$", id="nested-star"),
    pytest.param(r"([a-z]+)*$", id="nested-class"),
    pytest.param(r"(a|aa)+$", id="overlapping-alternation"),
]


@pytest.mark.parametrize("pattern", BOMBS)
def test_a_backtracking_pattern_is_refused(pattern: str) -> None:
    assert _compiled_within_budget({"pattern": pattern, "name": "x"}) is None


def test_an_uncompilable_pattern_is_refused_rather_than_raised() -> None:
    """A typo in a repository's config is not an exception in this tool."""
    assert _compiled_within_budget({"pattern": r"(unclosed", "name": "x"}) is None


@pytest.mark.parametrize("rule", DEFAULT_CONFIG["risk_patterns"],
                         ids=lambda rule: rule["name"])
def test_every_shipped_pattern_survives_the_budget(rule: dict) -> None:
    """The guard must not quietly disarm the product's own detectors.

    A budget that refuses real patterns would silently stop reporting
    debt markers and absence-as-zero, and nothing else in the suite
    would notice: findings would simply be absent.
    """
    assert _compiled_within_budget(rule) is not None


def test_a_hostile_pattern_does_not_stall_a_scan(tmp_path: Path) -> None:
    """End to end, with the clock running.

    The unit checks above would still pass if `risk_findings` ignored
    the guard, so this one runs the real scanning path against the real
    attack and asserts it finishes.
    """
    source = tmp_path / "app.py"
    source.write_text("x = '" + "a" * 40 + "!'\n", encoding="utf-8")
    config = {
        "risk_patterns": [
            {"name": "bomb", "pattern": r"(a+)+$", "extensions": [".py"]},
            {"name": "real", "pattern": r"\bTODO\b", "extensions": [".py"]},
        ],
    }

    started = time.perf_counter()
    findings = risk_findings(tmp_path, [source], config)
    elapsed = time.perf_counter() - started

    assert elapsed < 5, f"a configured regex stalled the scan for {elapsed:.1f}s"
    assert not [item for item in findings if item.name == "bomb"], (
        "the refused pattern still produced findings"
    )


def test_a_refused_pattern_does_not_silence_the_others(tmp_path: Path) -> None:
    """One bad rule must not take the rest of the scan down with it."""
    source = tmp_path / "app.py"
    source.write_text("# TODO: real finding\n", encoding="utf-8")
    config = {
        "risk_patterns": [
            {"name": "bomb", "pattern": r"(a+)+$", "extensions": [".py"]},
            {"name": "real", "pattern": r"\bTODO\b", "extensions": [".py"]},
        ],
    }

    findings = risk_findings(tmp_path, [source], config)

    assert [item.name for item in findings] == ["real"]
