"""The developer's own analyzers, read from their pipeline (Decision 17).

The catalog holds some 760 tools and this one runs a pinned handful. The
rest run where they already run — the developer's own build — and this
tool reads the SARIF they wrote. A file is declared in
`analyzers.pipeline_results` with the concerns it covers; it turns those
concerns from unexamined to examined for the languages its results name,
its findings are listed, its age against the last commit is stated, and in
this slice nothing it holds moves the grade.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._analysis import Analysis
from maintainability_audit._catalog import PolicyError, settings_from
from maintainability_audit._coverage_notes import coverage_notes
from maintainability_audit._documents import coverage_document
from maintainability_audit._pipeline_results import add_pipeline_results


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _sarif(*uris: str, tool: str = "Roslynator") -> str:
    return json.dumps({"version": "2.1.0", "runs": [{
        "tool": {"driver": {"name": tool}},
        "results": [{"ruleId": "RCS1001", "message": {"text": "Add braces."},
                     "locations": [{"physicalLocation": {"artifactLocation": {"uri": uri},
                                                         "region": {"startLine": 3}}}]}
                    for uri in uris]}]})


def _repo(tmp_path: Path, sarif: str | None, *, older_than_commit: bool = False) -> Path:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "App.cs").write_text("class App {}\n", encoding="utf-8")
    (root / "tool.py").write_text("x = 1\n", encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", ".")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    if sarif is not None:
        (root / "artifacts").mkdir()
        path = root / "artifacts" / "roslyn.sarif"
        path.write_text(sarif, encoding="utf-8")
        if older_than_commit:
            os.utime(path, (1_000_000, 1_000_000))
    return root


def _analysis() -> Analysis:
    return Analysis(concerns=("all",), languages={"C#": "csharp", "Python": "python"},
                    scored_languages=("C#", "Python"))


def _config(**entry) -> dict:
    declared = {"path": "artifacts/roslyn.sarif", "covers": ["style", "documentation"], **entry}
    return {"analyzers": {"pipeline_results": [declared]}}


def test_a_declared_file_examines_its_concerns_for_the_languages_it_names_only(tmp_path: Path) -> None:
    root = _repo(tmp_path, _sarif("src/App.cs"))
    analysis = _analysis()

    add_pipeline_results(analysis, root, _config())

    gaps = analysis.gaps_by_language()
    assert "style" not in gaps["C#"] and "documentation" not in gaps["C#"]
    assert "style" in gaps["Python"]
    assert "dead-code" in gaps["C#"]  # not declared, still unexamined


def test_its_row_names_the_tool_the_file_and_the_findings_and_they_are_listed(tmp_path: Path) -> None:
    root = _repo(tmp_path, _sarif("src/App.cs", "src/App.cs"))
    analysis = _analysis()

    add_pipeline_results(analysis, root, _config())

    row = next(i for i in coverage_document(analysis)["by_outcome"]["ran"] if i["tier"] == "pipeline")
    assert row["tool"] == "Roslynator" and row["findings"] == 2
    assert "artifacts/roslyn.sarif" in row["detail"]
    assert [f.tool for f in analysis.findings] == ["Roslynator", "Roslynator"]


def test_a_file_older_than_the_last_commit_is_called_stale(tmp_path: Path) -> None:
    root = _repo(tmp_path, _sarif("src/App.cs"), older_than_commit=True)
    analysis = _analysis()

    add_pipeline_results(analysis, root, _config())

    row = next(i for i in analysis.coverage if i.tier == "pipeline")
    assert row.stale is True
    assert "older than the last commit" in row.detail


def test_a_missing_file_is_a_stated_failure_and_examines_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path, None)
    analysis = _analysis()

    add_pipeline_results(analysis, root, _config())

    row = next(i for i in analysis.coverage if i.tier == "pipeline")
    assert row.outcome == "failed" and "artifacts/roslyn.sarif" in row.detail
    assert "style" in analysis.gaps_by_language()["C#"]


def test_a_path_outside_the_repository_is_refused_and_examines_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path, _sarif("src/App.cs"))
    (tmp_path / "outside.sarif").write_text(_sarif("src/App.cs"), encoding="utf-8")
    analysis = _analysis()

    add_pipeline_results(analysis, root, _config(path="../outside.sarif"))

    row = next(i for i in analysis.coverage if i.tier == "pipeline")
    assert row.outcome == "failed" and "outside" in row.detail
    assert "style" in analysis.gaps_by_language()["C#"]


def test_a_clean_file_names_its_languages_from_the_declaration(tmp_path: Path) -> None:
    """No results means no paths to read a language from; one is declared."""
    root = _repo(tmp_path, _sarif())
    analysis = _analysis()

    add_pipeline_results(analysis, root, _config(languages=["C#"]))

    assert "style" not in analysis.gaps_by_language()["C#"]
    assert "style" in analysis.gaps_by_language()["Python"]


def test_a_clean_file_with_no_language_examines_nothing(tmp_path: Path) -> None:
    """Counting it for every language would claim Python was styled by a C# tool."""
    root = _repo(tmp_path, _sarif())
    analysis = _analysis()

    add_pipeline_results(analysis, root, _config())

    assert "style" in analysis.gaps_by_language()["C#"]
    row = next(i for i in analysis.coverage if i.tier == "pipeline")
    assert "languages" in row.detail


def test_nothing_it_reports_counts_as_an_analyzer_the_tool_ran(tmp_path: Path) -> None:
    root = _repo(tmp_path, _sarif("src/App.cs"))
    analysis = _analysis()

    add_pipeline_results(analysis, root, _config())

    document = coverage_document(analysis)
    assert document["tools_attempted"] == 0 and document["selection"]["runnable"] == []


@pytest.mark.parametrize("entry", [
    {"path": "a.sarif", "covers": ["vibes"]},
    {"path": "a.sarif", "covers": []},
    {"covers": ["style"]},
])
def test_a_malformed_declaration_is_refused_when_the_settings_load(entry: dict) -> None:
    with pytest.raises(PolicyError, match="pipeline_results"):
        settings_from({"analyzers": {"pipeline_results": [entry]}})


def test_an_unexamined_concern_names_the_pipeline_route() -> None:
    text = "\n".join(coverage_notes({"concepts_unexamined": ["style"]}))

    assert "pipeline_results" in text



def test_first_run_asks_whether_there_are_any_as_a_structured_choice() -> None:
    """Stage one is choices on every surface; the file list is stage two."""
    from maintainability_audit._mcp_setup import setup_questions
    from maintainability_audit.config import load_config

    question = next(q for q in setup_questions(load_config(None)) if q["name"] == "pipeline_results")

    assert question["options"] == ["none", "declare"] and question["default"] == "none"
    assert "SARIF" in question["prompt"]


def test_an_answer_becomes_the_declarations() -> None:
    from maintainability_audit._catalog import pipeline_results_from_answer

    assert pipeline_results_from_answer(
        "artifacts/roslyn.sarif: style, documentation; build/lint.sarif: dead-code") == [
        {"path": "artifacts/roslyn.sarif", "covers": ["style", "documentation"]},
        {"path": "build/lint.sarif", "covers": ["dead-code"]},
    ]
    assert pipeline_results_from_answer("  ") == []
    with pytest.raises(PolicyError, match="pipeline_results"):
        pipeline_results_from_answer("a.sarif: vibes")


def test_declare_opens_the_second_stage_and_its_answer_is_written(tmp_path: Path) -> None:
    from maintainability_audit._mcp_setup import apply_answers, pipeline_files_pending, staged_questions

    root = _repo(tmp_path, None)
    apply_answers(root, {"pipeline_results": "declare"})

    assert pipeline_files_pending(root)
    assert [q["name"] for q in staged_questions(root)] == ["pipeline_files"]
    assert staged_questions(root)[0]["options"] == []

    merged = apply_answers(root, {"pipeline_files": "artifacts/roslyn.sarif: style"})

    assert merged["analyzers"]["pipeline_results"] == [
        {"path": "artifacts/roslyn.sarif", "covers": ["style"]}]
    assert not pipeline_files_pending(root)


def test_none_asks_nothing_further(tmp_path: Path) -> None:
    from maintainability_audit._mcp_setup import apply_answers, pipeline_files_pending

    root = _repo(tmp_path, None)
    apply_answers(root, {"pipeline_results": "none"})

    assert not pipeline_files_pending(root)


def test_the_published_schema_accepts_a_declaration_and_refuses_an_unknown_concern() -> None:
    import jsonschema

    schema = json.loads((Path(__file__).resolve().parents[1] / "maintainability-agent.schema.json")
                        .read_text(encoding="utf-8"))
    good = {"version": 1, "analyzers": {"pipeline_requested": True, "pipeline_results": [
        {"path": "artifacts/roslyn.sarif", "covers": ["style", "documentation"], "languages": ["C#"]}]}}

    jsonschema.validate(good, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"version": 1, "analyzers": {"pipeline_results": [
            {"path": "a.sarif", "covers": ["vibes"]}]}}, schema)


def test_a_config_the_analysis_already_refused_does_not_end_the_audit(tmp_path: Path) -> None:
    """`analyze` records a bad analyzer block as an error and never raises; nor does this."""
    root = _repo(tmp_path, _sarif("src/App.cs"))
    analysis = _analysis()

    add_pipeline_results(analysis, root, {"analyzers": {"depth": "light", **_config()["analyzers"]}})

    assert not [i for i in analysis.coverage if i.tier == "pipeline"]


def test_the_elicited_second_stage_says_it_is_asking_for_the_files(tmp_path: Path) -> None:
    from maintainability_audit._mcp_setup import apply_answers
    from maintainability_audit.mcp_server import _setup_stage_message

    root = _repo(tmp_path, None)
    apply_answers(root, {"pipeline_results": "declare"})

    assert "SARIF" in _setup_stage_message(str(root))


def test_declare_stays_with_the_repository_and_never_reaches_the_person(tmp_path: Path) -> None:
    """Which files a build writes is a fact about one repository, not a preference."""
    from maintainability_audit._mcp_setup import apply_answers
    from maintainability_audit._user_config import user_config_answers

    apply_answers(_repo(tmp_path, None), {"pipeline_results": "declare"})

    assert "pipeline_requested" not in ((user_config_answers() or {}).get("analyzers") or {})
