"""The corpus note's size and languages are the corpus's, not prose.

Every report carries a note saying how many repositories the anchor was
drawn from and in which languages. Both were typed into `scoring.py` —
"180 mature repositories" and a hand-written list of thirteen — so
extending the corpus to Kotlin and Shell would have left every report
naming 180 repositories and thirteen languages while the constants came
from 201 and fifteen. D143 was this defect in `standard.md`; this is the
same count, one file over.

Both now live beside `CORPUS_MEASURED` and are checked against
`corpus.json`, enumerated from the file rather than from memory.
"""

from __future__ import annotations

import json
from pathlib import Path

from maintainability_audit import _calibration
from maintainability_audit._metrics_types import KNOWN_SOURCE_SUFFIXES
from maintainability_audit.scoring import _reference_block

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tools" / "calibration" / "corpus.json"


def _corpus() -> list[dict]:
    return json.loads(CORPUS.read_text(encoding="utf-8"))["repos"]


def _display(identifier: str) -> str:
    names = {name.lower(): name for name in KNOWN_SOURCE_SUFFIXES.values()}
    spelled = {"cpp": "c++", "csharp": "c#"}.get(identifier, identifier)
    return names[spelled]


def test_the_corpus_size_is_the_number_of_pinned_repositories() -> None:
    assert len(_corpus()) == _calibration.CORPUS_SIZE


def test_the_corpus_languages_are_the_languages_pinned() -> None:
    assert set(_calibration.CORPUS_LANGUAGES) == {_display(r["language"]) for r in _corpus()}


def test_the_note_states_both() -> None:
    note = _reference_block()["corpus_note"]

    assert f"drawn from {len(_corpus())} mature repositories" in note
    assert _reference_block()["corpus_languages"] == list(_calibration.CORPUS_LANGUAGES)
