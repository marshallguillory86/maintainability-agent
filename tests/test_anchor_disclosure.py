"""F1, second time: the grade must not claim the corpus covers every
parsed language while Swift and COBOL sit outside it.

v2.0.0 closed the first instance by putting ``score.reference`` on the
report. The note then said "every language this scanner parses". Swift
(2.4.0) and COBOL (2.7.0) shipped unanchored. The note is now false,
the markdown/HTML executive strip never prints it, and the remediation
prompt still describes a Python/TypeScript/JavaScript corpus.

Population: parsed languages from ``DECLARATION_SUFFIXES`` via
``KNOWN_SOURCE_SUFFIXES``; corpus languages from
``tools/calibration/corpus.json``. Not a list typed here.

Unanchored-as-policy is decided. This file does not demand a corpus
extension. It demands that the surfaces that show the grade tell the
truth while ``parsed - corpus`` is non-empty.

*Mutation:* ``corpus_note``'s "every language this scanner parses"
sentence. The assertion matches that phrase wherever it is written, not
``_reference_block`` by name.
"""

from __future__ import annotations

import json
from pathlib import Path

from maintainability_audit._html_view import _executive_strip
from maintainability_audit._metrics_types import KNOWN_SOURCE_SUFFIXES
from maintainability_audit.declarations import DECLARATION_SUFFIXES
from maintainability_audit.prompts import prompt_pressure_section
from maintainability_audit.renderers import summary_table
from maintainability_audit.scoring import _reference_block

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tools" / "calibration" / "corpus.json"

#: corpus.json spells C++ and C# as cpp/csharp. Display names from
#: KNOWN_SOURCE_SUFFIXES use the punctuation. One map, used only to
#: compare the two derived sets.
_CORPUS_SPELLING = {"cpp": "c++", "csharp": "c#"}

_EVERY_PARSED = "every language this scanner parses"
_EVERY_PARSED_README = "every language the scanner parses"


def _parsed_languages() -> set[str]:
    names = {KNOWN_SOURCE_SUFFIXES[suffix].lower() for suffix in DECLARATION_SUFFIXES if suffix in KNOWN_SOURCE_SUFFIXES}
    assert names, "DECLARATION_SUFFIXES produced no language names"
    return names


def _corpus_languages() -> set[str]:
    payload = json.loads(CORPUS.read_text(encoding="utf-8"))
    repos = payload["repos"]
    assert repos, "corpus.json has no repos; this test would pass vacuously"
    held = {_CORPUS_SPELLING.get((repo.get("language") or "").lower(), (repo.get("language") or "").lower()) for repo in repos}
    held.discard("")
    assert held, "corpus.json named no languages"
    return held


def _unanchored() -> set[str]:
    return _parsed_languages() - _corpus_languages()


def _surfaces() -> dict[str, str]:
    """Every place a reader meets the grade, as produced today."""
    score = {
        "maintainability_estimate": 4.0,
        "maintainability_range": [3.5, 4.5],
        "verified_grade": "B",
        "verified_grade_blockers": [],
        "evidence_status": {
            "status": "complete",
            "profile": "default-v1",
            "reasons": [],
        },
        "analyzer_scored_dimensions": [],
        "reference": _reference_block(),
        "dimensions": {"declarations": 2.0},
    }
    summary = {
        "files_scanned": 100,
        "file_warnings": 0,
        "file_failures": 0,
        "function_warnings": 0,
        "function_failures": 0,
        "duplicate_blocks": 0,
        "risk_findings": 0,
        "hard_gate_failures": 0,
    }
    report = {
        "hard_gate_failures": [],
        "work_order": [],
        "analyzer_coverage": None,
        "score": score,
    }
    return {
        "corpus_note": str(score["reference"]["corpus_note"]),
        "markdown_summary": "\n".join(summary_table(summary, score, False)),
        "html_executive": "\n".join(_executive_strip(report, score, [])),
        "prompt_pressure": "\n".join(prompt_pressure_section(score)),
        "standard": (ROOT / "docs" / "standard.md").read_text(encoding="utf-8"),
        "packaged_standard": (ROOT / "src" / "maintainability_audit" / "_assets" / "standard.md").read_text(encoding="utf-8"),
        "readme": (ROOT / "README.md").read_text(encoding="utf-8"),
        "prompts_module": (ROOT / "src" / "maintainability_audit" / "prompts.py").read_text(encoding="utf-8"),
    }


def test_parsed_and_corpus_languages_are_derived_and_not_empty() -> None:
    parsed = _parsed_languages()
    held = _corpus_languages()
    assert parsed
    assert held
    # The sets are different today (Swift, COBOL). If a recalibration
    # makes them equal, the disclosure tests below become no-ops on
    # purpose: the phrase is then true.
    _ = parsed - held


def test_the_live_note_does_not_say_every_parsed_language_while_some_are_missing() -> None:
    missing = _unanchored()
    if not missing:
        return
    surfaces = _surfaces()
    offenders = [name for name, text in surfaces.items() if _EVERY_PARSED in text.lower() or _EVERY_PARSED_README in text.lower()]
    assert not offenders, (
        "parsed languages missing from the corpus: "
        f"{sorted(missing)}. These surfaces still say the scanner's "
        f"languages are all in the anchor: {offenders}"
    )


def test_unanchored_languages_are_named_in_the_corpus_note() -> None:
    missing = _unanchored()
    if not missing:
        return
    note = _surfaces()["corpus_note"].lower()
    unnamed = [lang for lang in sorted(missing) if lang not in note]
    assert not unnamed, (
        "score.reference.corpus_note does not name the parsed languages "
        f"the corpus omits: {unnamed}. Unanchored is policy; silence at "
        "the grade is the F1 shape that already shipped once."
    )


def test_the_grade_skins_name_unanchored_languages() -> None:
    """Markdown summary and HTML executive strip are where the letter is read.

    ``score.reference`` on the JSON report does not travel with the
    skins. A disclosure only in JSON is the last close of this class.
    """
    missing = _unanchored()
    if not missing:
        return
    surfaces = _surfaces()
    for skin in ("markdown_summary", "html_executive", "prompt_pressure"):
        text = surfaces[skin].lower()
        unnamed = [lang for lang in sorted(missing) if lang not in text]
        assert not unnamed, (
            f"{skin} prints a grade and does not name unanchored languages {unnamed}. The limit has to sit where the number is read."
        )


def test_the_prompt_does_not_describe_a_three_language_corpus() -> None:
    missing = _unanchored()
    if not missing:
        return
    text = _surfaces()["prompt_pressure"].lower()
    three = "python, typescript and javascript" in text
    assert not three or all(lang in text for lang in missing), (
        "the remediation prompt still describes 1.0x as the median of a "
        "Python, TypeScript and JavaScript corpus while "
        f"{sorted(missing)} are parsed and unanchored"
    )
