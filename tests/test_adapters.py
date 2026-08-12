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
    # A Node tool may be reached through `npx`, so the executable need only
    # appear in the probe rather than lead it.
    assert adapter.executable in adapter.version_argv()


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

    complexity = [m for m in extraction.measurements
                  if m.concept == "cyclomatic_complexity"]
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


def test_an_unknown_slug_has_no_adapter_rather_than_raising() -> None:
    """The catalog lists far more tools than have adapters.

    A missing adapter is an ordinary reportable state, not an error.
    """
    assert adapter_for("some-tool-nobody-wrote") is None


def test_ruff_findings_are_located_and_classified() -> None:
    """Ruff is a verdict emitter whose findings are most of its value.

    The tool exists to improve code, not only to score it, and "unused
    import at line 12" is directly actionable in a way no aggregate is.
    """
    payload = json.dumps([
        {"code": "F401", "filename": "m.py", "location": {"row": 1},
         "message": "`os` imported but unused"},
        {"code": "C901", "filename": "m.py", "location": {"row": 9},
         "message": "`f` is too complex"},
        {"code": "E501", "filename": "m.py", "location": {"row": 3},
         "message": "line too long"},
    ])
    extraction = adapter_for("ruff").parse(_ran(payload))

    assert not extraction.measurements, "a verdict emitter contributes no rate"
    by_rule = {f.rule: f for f in extraction.findings}
    assert by_rule["F401"].concept == "dead-code"
    assert by_rule["C901"].concept == "complexity"
    assert by_rule["E501"].concept == "style", "unclassified rules default to style"
    assert all(f.path and f.line for f in extraction.findings), "findings must be locatable"


def test_a_projects_lint_config_shapes_findings_but_never_a_rate() -> None:
    """Both halves are deliberate.

    A team's rule selection is their policy about their code, so it should
    change what they are told. It must not change their score, or two
    repositories stop being comparable (P2) — and ruff cannot affect a
    score because it contributes no measurements at all.
    """
    adapter = adapter_for("ruff")

    assert adapter.emits == "verdict"
    assert measurements_only(
        Extraction(measurements=(
            Measurement(concept="style", unit="u", value=1.0, tool="ruff", path="m.py"),
        )),
        adapter,
    ) == ()


def test_a_node_tool_prefers_a_local_install_over_fetching(monkeypatch) -> None:
    """Fetching is permitted but should not be the first choice.

    P1 separates analysis from acquisition: analysis never touches the
    network, acquisition may. Using an installed binary when one exists
    keeps the fetch to first run and lets a user pin a version.
    """
    from maintainability_audit import _adapters

    monkeypatch.setattr(_adapters.shutil, "which", lambda _tool: "/usr/local/bin/jscpd")
    assert _adapters._npx("jscpd", "--version") == ("jscpd", "--version")

    monkeypatch.setattr(_adapters.shutil, "which", lambda _tool: None)
    assert _adapters._npx("jscpd", "--version") == ("npx", "--yes", "jscpd", "--version")


def test_jscpd_writes_its_report_outside_the_audited_tree(tmp_path: Path) -> None:
    """Writing into the repository would change what later tools see."""
    adapter = adapter_for("jscpd")
    argv = adapter.invocation(tmp_path).argv
    output = argv[argv.index("--output") + 1]

    assert not Path(output).is_relative_to(tmp_path)


@pytest.mark.parametrize("slug", sorted(ADAPTERS))
def test_raw_output_survives_a_parse_failure(slug: str) -> None:
    """The case where raw output matters most.

    A parse error means *this agent* could not read the output. A language
    model reading the report usually can, and discarding it would throw
    away the one artifact that still had value. Swept over every adapter,
    because the adapter most likely to break is the one nobody expected to.
    """
    unreadable = _ran("!!! not the shape this parser expects !!!")
    extraction = adapter_for(slug).parse(unreadable)

    if extraction.parse_error:
        assert extraction.raw, f"{slug} discarded output its parser could not read"
        assert "retained" in extraction.parse_error, (
            "the reader must be told the output is still there"
        )


def test_raw_output_is_bounded_but_marked_when_cut() -> None:
    """A report is a document, not a log.

    Truncating silently would let a reader draw conclusions from a
    fragment they believed was the whole.
    """
    from maintainability_audit._adapters import RAW_INLINE_LIMIT

    extraction = adapter_for("lizard").parse(_ran("x" * (RAW_INLINE_LIMIT + 500)))

    assert len(extraction.raw) == RAW_INLINE_LIMIT
    assert extraction.truncated


def test_a_successful_parse_also_keeps_the_raw_output() -> None:
    """Not only a failure path.

    The engine maps output onto nine concerns, which is lossy by design;
    a model reading the report is not bound by that vocabulary.
    """
    payload = json.dumps([{"code": "F401", "filename": "m.py",
                           "location": {"row": 1}, "message": "unused"}])
    extraction = adapter_for("ruff").parse(_ran(payload))

    assert extraction.findings
    assert not extraction.parse_error
    assert extraction.raw == payload


@pytest.mark.parametrize("slug", sorted(ADAPTERS))
def test_every_adapter_honours_the_audits_exclusions(slug: str, tmp_path: Path) -> None:
    """A tool that walks `.venv` reports someone else's code as yours.

    Measured before this existed: vulture returned 517 dead-code findings
    on this repository and **all 517 were inside `.venv`**. A report that
    blames a user for a vendored library is worse than no report, so the
    exclusions the built-in scan honours are passed to every analyzer —
    each in its own dialect.

    Swept over the registry: an adapter added without exclusion support
    fails here rather than in someone's report.
    """
    adapter = adapter_for(slug)
    # A real tree: adapters whose tool has no exclusion flag apply the
    # filter by choosing which files to name, so an empty directory would
    # make both invocations identical and the assertion vacuous.
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / ".venv" / "lib").mkdir(parents=True)
    (repo / "src" / "real.py").write_text("x = 1\n", encoding="utf-8")
    (repo / ".venv" / "lib" / "vendored.py").write_text("y = 2\n", encoding="utf-8")

    excluded = " ".join(adapter.invocation(repo, excludes=(".venv/", "node_modules/")).argv)
    plain = " ".join(adapter.invocation(repo).argv)

    assert excluded != plain, f"{slug} ignores exclusions and will scan vendored code"
    assert "vendored.py" not in excluded, f"{slug} still names a vendored file"


def test_an_adapter_without_an_exclusion_flag_is_visible_as_such() -> None:
    """Not every tool can be told to skip a path.

    Silently accepting that would let vendored findings through unnoticed,
    so the absence is expressed in the adapter rather than assumed away.
    """
    naked = BaseAdapter(slug="n", emits="metric", executable="n")

    assert naked.exclusions((".venv/",)) == (), "no flag means no exclusions to add"
    assert naked.exclude_flag == "", "and the adapter says so plainly"


def test_eslint_classifies_its_rules_and_locates_findings() -> None:
    payload = json.dumps([{
        "filePath": "/repo/m.js",
        "messages": [
            {"ruleId": "complexity", "line": 1, "message": "complexity of 11"},
            {"ruleId": "max-params", "line": 1, "message": "too many parameters"},
            {"ruleId": "no-unused-vars", "line": 4, "message": "'x' is unused"},
            {"ruleId": "semi", "line": 6, "message": "missing semicolon"},
        ],
    }])
    extraction = adapter_for("eslint").parse(_ran(payload))

    by_rule = {f.rule: f.concept for f in extraction.findings}
    assert by_rule == {
        "complexity": "complexity", "max-params": "structure",
        "no-unused-vars": "dead-code", "semi": "style",
    }
    assert not extraction.measurements, "eslint is a verdict emitter"


def test_eslint_knows_when_it_cannot_run(tmp_path: Path) -> None:
    """Flat config is mandatory from v9.

    Without one eslint exits having done nothing, and recording that as
    "ran, found nothing" would be a clean result nobody earned.
    """
    adapter = adapter_for("eslint")
    assert not adapter.has_config(tmp_path)

    (tmp_path / "eslint.config.mjs").write_text("export default [];\n", encoding="utf-8")
    assert adapter.has_config(tmp_path)


def test_xenon_is_deliberately_unadapted() -> None:
    """A gate over radon adds no independent reading.

    xenon re-ranks radon's own cyclomatic numbers against thresholds. An
    adapter would put a fourth "independent" complexity source into the
    pool that is strictly derived from one already counted, inflating
    apparent corroboration without adding evidence. Two tools agreeing
    because one *is* the other is worse than one tool alone, because it
    looks like confirmation.
    """
    assert adapter_for("xenon") is None
