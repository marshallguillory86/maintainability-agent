"""Corpus selection queries every language the scanner parses.

`UNANCHORED_LANGUAGES` discloses a parsed language the corpus lacks, and
`test_unanchored_set_matches_corpus` keeps that disclosure honest. Neither
says anything about whether the gap will ever close: Kotlin and Shell
shipped parsers ahead of the corpus, "to anchor at the next
recalibration", and `select_corpus.LANGUAGES` still did not name them, so
re-running selection would have measured the same thirteen languages
again and left both provisional.

A parsed language is either queried or recorded in `UNSELECTABLE` with
the reason no corpus-grade repositories exist, as COBOL is.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from test_unanchored_set_matches_corpus import _CORPUS_SPELLING, _parsed_languages

ROOT = Path(__file__).resolve().parents[1]


def _selection():
    path = ROOT / "tools" / "calibration" / "select_corpus.py"
    spec = importlib.util.spec_from_file_location("select_corpus_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_parsed_language_is_selected_or_recorded_as_unselectable() -> None:
    selection = _selection()
    covered = {_CORPUS_SPELLING.get(name, name)
               for name in (*selection.LANGUAGES, *selection.UNSELECTABLE)}

    assert _parsed_languages() - covered == set()
