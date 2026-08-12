"""Adapters turn tool output into measurements and findings — ADR 006, 008.

The property that matters most: **a verdict emitter may never contribute a
rate.** Measured on eslint, the same one-function file at complexity 11 yields
1 finding at threshold 5 and 0 at threshold 15 — so its output encodes the
tool's own threshold, and at the higher one nothing reveals a function exists
at all. Consuming that as a rate would make the score a function of the
repository's lint config, falsifying P2, and would reintroduce the 0.5.0
count-not-rate defect from a new direction.

The second property: a tool that ran but whose output could not be read is a
**stated gap**, never silence. Output shapes drift between releases, and a
version bump quietly turning findings into a clean result is the hello-world
A+ one more time.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintainability_audit._adapters import (
    ADAPTERS,
    BaseAdapter,
    Extraction,
    Measurement,
    adapter_for,
    measurements_only,
)
from maintainability_audit._runner import Outcome, ToolResult


def _ran(stdout: str = "", stderr: str = "") -> ToolResult:
    return ToolResult(slug="t", outcome=Outcome.RAN, stdout=stdout, stderr=stderr, exit_code=0)


@pytest.mark.parametrize("slug", sorted(ADAPTERS))
def test_every_adapter_declares_its_shape_and_concepts(slug: str) -> None:
    """Swept over the registry, so a new adapter is covered when added."""
    adapter = adapter_for(slug)

    assert adapter is not None
    assert adapter.emits in {"metric", "verdict", "both"}
    assert adapter.concepts, f"{slug} measures nothing, so nothing can select it"
    assert adapter.executable, f"{slug} has no executable to invoke"
    assert adapter.version_argv()[0] == adapter.executable


@pytest.mark.parametrize("slug", sorted(ADAPTERS))
def test_no_adapter_raises_on_unusable_input(slug: str) -> None:
    """Garbage in must become a stated gap, never an exception or silence.

    Swept over every adapter and every failure shape, because "it happened
    to work on the output I had" is how a parser passes review and fails in
    the field.
    """
    adapter = adapter_for(slug)
    for result in (
        _ran(""),
        _ran("not json at all {{{"),
        _ran("\x00\x01binary"),
        _ran(json.dumps({"unexpected": "shape"})),
        ToolResult(slug=slug, outcome=Outcome.FAILED, detail="boom"),
        ToolResult(slug=slug, outcome=Outcome.TIMED_OUT, detail="slow"),
    ):
        extraction = adapter.parse(result)
        assert isinstance(extraction, Extraction)
        if not result.usable:
            assert extraction.parse_error, "a tool that did not run is not a clean result"


def test_a_tool_that_did_not_run_never_yields_a_clean_extraction() -> None:
    adapter = adapter_for("lizard")
    extraction = adapter.parse(ToolResult(slug="lizard", outcome=Outcome.NOT_INSTALLED,
                                          detail="lizard is not on PATH"))

    assert extraction.parse_error
    assert not extraction.measurements
    assert not extraction.findings


def test_a_verdict_emitter_cannot_contribute_measurements() -> None:
    """Enforced, not trusted.

    An adapter marked `verdict` that started returning measurements would
    silently reintroduce threshold-contaminated rates. This is the guard
    that stops a future edit doing it by accident.
    """
    verdict = BaseAdapter(slug="v", emits="verdict", executable="v")
    smuggled = Extraction(measurements=(
        Measurement(concept="complexity", unit="a::f", value=9.0, tool="v", path="a.py"),
    ))

    assert measurements_only(smuggled, verdict) == ()

    metric = BaseAdapter(slug="m", emits="metric", executable="m")
    assert measurements_only(smuggled, metric) == smuggled.measurements


def test_lizard_parses_real_csv() -> None:
    """A row from lizard's actual output, not an invented shape."""
    row = '31,14,220,4,48,"history_section@217-264@src/h.py","src/h.py","history_section",' \
          '"history_section( a , b )",217,264'
    extraction = adapter_for("lizard").parse(_ran(row))

    complexity = [m for m in extraction.measurements if m.concept == "complexity"]
    assert len(complexity) == 1
    assert complexity[0].value == 14.0
    assert complexity[0].unit == "src/h.py::history_section"
    assert complexity[0].tool == "lizard"


def test_radon_parses_real_json() -> None:
    payload = json.dumps({"src/cli.py": {"mi": 42.23, "rank": "A"}})
    extraction = adapter_for("radon").parse(_ran(payload))

    assert len(extraction.measurements) == 1
    assert extraction.measurements[0].value == pytest.approx(42.23)


def test_interrogate_reads_the_percentage_not_the_exit_code() -> None:
    """The tool's own pass/fail is against *its* threshold, and is ignored.

    The rubric owns thresholds. Reading interrogate's verdict instead of
    its number would import a default nobody chose.
    """
    failed = _ran("RESULT: FAILED (minimum: 80.0%, actual: 63.3%)\n")
    extraction = adapter_for("interrogate").parse(failed)

    assert len(extraction.measurements) == 1
    assert extraction.measurements[0].value == pytest.approx(63.3)


def test_vulture_locates_its_findings() -> None:
    output = "src/a.py:42: unused function 'old_helper' (90% confidence)\n"
    extraction = adapter_for("vulture").parse(_ran(output))

    assert len(extraction.findings) == 1
    finding = extraction.findings[0]
    assert (finding.path, finding.line) == ("src/a.py", 42)
    assert not extraction.measurements, "vulture is a verdict emitter"


def test_jscpd_is_never_invoked_through_a_downloader() -> None:
    """`npx --yes` would fetch a package mid-audit.

    That is a network action, and P1 promises none. A jscpd that is not
    installed must be reported unavailable rather than downloaded.
    """
    argv = adapter_for("jscpd").invocation(Path("/tmp/x")).argv

    assert argv[0] == "jscpd"
    assert "npx" not in argv
    assert "--yes" not in argv


def test_an_unknown_slug_has_no_adapter_rather_than_raising() -> None:
    """The catalog lists far more tools than have adapters.

    A missing adapter is an ordinary reportable state, not an error.
    """
    assert adapter_for("some-tool-nobody-wrote") is None
