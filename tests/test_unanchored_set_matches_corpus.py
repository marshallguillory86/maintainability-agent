"""The unanchored disclosure is parsed languages minus the measured corpus.

The corpus is allowed to lag a newly parsed language, but every presentation
of that fact starts with ``UNANCHORED_LANGUAGES``.  That constant therefore
has to be derived-equivalent to the corpus, not a historical list that only
grows.  In particular, adding a language already represented in the corpus
must fail this test even if every grade skin repeats the same stale constant.
"""
from __future__ import annotations

import json
from pathlib import Path

from maintainability_audit._anchor import UNANCHORED_LANGUAGES, unanchored_sentence
from maintainability_audit._html_view import _executive_strip
from maintainability_audit._metrics_types import KNOWN_SOURCE_SUFFIXES
from maintainability_audit.declarations import DECLARATION_SUFFIXES
from maintainability_audit.prompts import prompt_pressure_section
from maintainability_audit.renderers import summary_table
from maintainability_audit.scoring import _reference_block

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tools" / "calibration" / "corpus.json"

# corpus.json uses identifiers where the source inventory uses display names.
_CORPUS_SPELLING = {"cpp": "c++", "csharp": "c#"}


def _parsed_languages() -> set[str]:
    languages = {
        KNOWN_SOURCE_SUFFIXES[suffix].lower()
        for suffix in DECLARATION_SUFFIXES
        if suffix in KNOWN_SOURCE_SUFFIXES
    }
    assert languages, "DECLARATION_SUFFIXES produced no known source languages"
    return languages


def _corpus_languages() -> set[str]:
    payload = json.loads(CORPUS.read_text(encoding="utf-8"))
    languages = {
        _CORPUS_SPELLING.get(language, language)
        for repo in payload["repos"]
        if (language := str(repo.get("language", "")).lower())
    }
    assert languages, "corpus.json has no measured languages"
    return languages


def _display_names(languages: set[str]) -> str:
    displays = {
        display.lower(): display
        for suffix, display in KNOWN_SOURCE_SUFFIXES.items()
        if suffix in DECLARATION_SUFFIXES
    }
    return " and ".join(displays[language] for language in sorted(languages))


def test_unanchored_languages_are_exactly_parsed_minus_corpus() -> None:
    """A constant that names any anchored language is a false caveat."""
    unanchored = _parsed_languages() - _corpus_languages()

    assert unanchored, (
        "parsed languages and the corpus are equal; this disclosure test no "
        "longer has an unanchored population to exercise"
    )
    assert {language.lower() for language in UNANCHORED_LANGUAGES} == unanchored, (
        "UNANCHORED_LANGUAGES must be parsed languages minus corpus languages; "
        f"expected {sorted(unanchored)}, got {sorted(language.lower() for language in UNANCHORED_LANGUAGES)}"
    )


def test_corpus_note_only_calls_unanchored_languages_absent() -> None:
    """The reference caveat must not call a corpus member absent."""
    note = str(_reference_block()["corpus_note"])

    assert unanchored_sentence() in note, (
        "the corpus note no longer carries the unanchored-language caveat"
    )
    asserted_absent = {language.lower() for language in UNANCHORED_LANGUAGES}
    anchored = asserted_absent & _corpus_languages()
    assert not anchored, (
        "corpus_note calls measured corpus languages absent: "
        f"{sorted(anchored)}"
    )


def test_every_grade_skin_prints_the_derived_unanchored_caveat() -> None:
    """All rendered caveats must carry the same derived, not stale, names."""
    expected = _parsed_languages() - _corpus_languages()
    expected_names = _display_names(expected)
    score = {
        "maintainability_estimate": 4.0,
        "maintainability_range": [3.5, 4.5],
        "verified_grade": "B",
        "verified_grade_blockers": [],
        "evidence_status": {"status": "complete", "profile": "default-v1", "reasons": []},
        "analyzer_scored_dimensions": [],
        "reference": _reference_block(),
        "dimensions": {"declarations": 2.0},
    }
    summary = {
        "files_scanned": 0,
        "file_warnings": 0,
        "file_failures": 0,
        "function_warnings": 0,
        "function_failures": 0,
        "duplicate_blocks": 0,
        "risk_findings": 0,
        "hard_gate_failures": 0,
    }
    report = {"hard_gate_failures": [], "analyzer_coverage": None, "work_order": []}
    skins = {
        "corpus_note": str(score["reference"]["corpus_note"]),
        "markdown_summary": "\n".join(summary_table(summary, score)),
        "html_executive": "\n".join(_executive_strip(report, score, [])),
        "remediation_prompt": "\n".join(prompt_pressure_section(score)),
    }

    for name, text in skins.items():
        assert f"{expected_names} are parsed" in text, (
            f"{name} does not print the derived unanchored caveat for "
            f"{sorted(expected)}: {text!r}"
        )
