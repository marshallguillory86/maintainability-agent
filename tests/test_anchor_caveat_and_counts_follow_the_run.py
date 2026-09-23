"""The anchor's limits are stated about the run in front of the reader.

D167 and D168, found on a Java repository's chat-door report, which said
"COBOL is parsed but is not in the reference corpus" and quoted the
corpus as "eight of the ten parsed languages" three lines above a note
saying thirteen of fourteen.

D167's claim: **a grade skin discloses an unanchored language exactly
when the run scanned that language.** D143 and D148 made the disclosure
reach every skin; this keeps it true on each. D168's claim: **every
count of the corpus's languages equals the corpus lists it describes.**

Populations are derived: the unanchored set and the corpus from the
report's own `score.reference`, each language's suffix from the
scanner's `KNOWN_SOURCE_SUFFIXES`, and the tree from every grammar
fixture on disk.
"""
from __future__ import annotations

import copy
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GRAMMAR = ROOT / "tests" / "fixtures" / "grammar"
CAVEAT = re.compile(r"parsed but (?:is|are) not in the reference corpus")


def _config() -> dict[str, Any]:
    from maintainability_audit.config import load_config

    config = copy.deepcopy(load_config(None))
    # Every declaration breaches, so a dimension is elevated and the
    # prompt prints its corpus comparison — the sentence D168 is about.
    config["thresholds"].update({
        "max_function_lines": 1, "warn_function_lines": 1,
        "max_class_lines": 1, "warn_class_lines": 1,
        "max_complexity": 0, "warn_complexity": 0,
    })
    return config


def _tree(tmp_path: Path, name: str, *, anchored_only: bool = False) -> Path:
    """Every grammar fixture, or only those the reference corpus measured.

    `anchored_only` is derived from the unanchored set rather than
    listing suffixes, because the set moves: Kotlin shipped a scanner in
    3.8.0 ahead of the corpus, so `constructs.kt` arrived in this
    directory and the "a tree with none of them" case silently stopped
    being one. Deriving it means the day Kotlin anchors, this corrects
    itself instead of pinning a language list written today.
    """
    fixtures = sorted(GRAMMAR.rglob("constructs.*"))
    assert fixtures, f"no grammar fixtures under {GRAMMAR}; this sweep would pass vacuously"
    if anchored_only:
        from maintainability_audit._anchor import UNANCHORED_LANGUAGES
        from maintainability_audit._metrics_types import KNOWN_SOURCE_SUFFIXES

        unanchored = set(UNANCHORED_LANGUAGES)
        fixtures = [
            fixture for fixture in fixtures
            if KNOWN_SOURCE_SUFFIXES.get(fixture.suffix) not in unanchored
        ]
        assert fixtures, (
            "every grammar fixture is an unanchored language, so there is "
            "no tree left to check the no-caveat case against"
        )
    tree = tmp_path / name
    tree.mkdir()
    for fixture in fixtures:
        shutil.copy(fixture, tree / fixture.name)
    return tree


def _unanchored(report: dict[str, Any]) -> tuple[str, ...]:
    return tuple(report["score"]["reference"]["unanchored_languages"])


def _skins(report: dict[str, Any]) -> dict[str, str]:
    """Every surface that prints a grade, rendered from the live report."""
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.renderers import render_html, render_markdown

    return {
        "markdown_complete": render_markdown(report, complete=True),
        "markdown_bounded": render_markdown(report, complete=False),
        "html": render_html(report, []),
        "prompt": render_ai_prompt(report),
    }


def test_no_skin_discloses_an_unanchored_language_the_run_did_not_scan(tmp_path) -> None:
    """D167: a tree with none of the unanchored languages prints no caveat."""
    from maintainability_audit.report import build_report

    report = build_report(
        _tree(tmp_path, "anchored", anchored_only=True), _config(), run_analyzers=False
    )
    missing = _unanchored(report)
    assert missing, "the anchor names no unanchored language; nothing here to disclose or withhold"
    present = set(report["summary"]["languages"])
    assert present, "the tree's language census is empty"
    assert not present & set(missing), (
        f"the grammar fixtures now include {present & set(missing)}; this test needs a tree without them"
    )
    wrong = {skin: CAVEAT.search(text).group(0)
             for skin, text in _skins(report).items() if CAVEAT.search(text)}
    assert not wrong, (
        f"skins disclosing {missing} on a tree whose languages are {sorted(present)}: {wrong}"
    )


def test_every_grade_skin_discloses_each_unanchored_language_the_run_scanned(tmp_path) -> None:
    """D167's other half: narrowing the caveat must not drop it where it applies.

    Covers existing behaviour: before D167 every skin disclosed on every tree,
    so a tree that does scan an unanchored language passed then too. It guards
    the fix against over-narrowing (D143, D148).
    """
    from maintainability_audit._metrics_types import KNOWN_SOURCE_SUFFIXES
    from maintainability_audit.report import build_report

    probe = build_report(_tree(tmp_path, "probe"), _config(), run_analyzers=False)
    missing = _unanchored(probe)
    assert missing, "the anchor names no unanchored language"
    tree = _tree(tmp_path, "unanchored")
    for language in missing:
        suffixes = sorted(s for s, name in KNOWN_SOURCE_SUFFIXES.items() if name == language)
        assert suffixes, f"no source suffix maps to {language}"
        (tree / f"sample{suffixes[0]}").write_text("       IDENTIFICATION DIVISION.\n", encoding="utf-8")
    report = build_report(tree, _config(), run_analyzers=False)
    assert set(missing) <= set(report["summary"]["languages"]), report["summary"]["languages"]
    for skin in ("markdown_complete", "markdown_bounded", "html", "prompt"):
        text = _skins(report)[skin]
        unnamed = [language for language in missing if language not in text]
        assert CAVEAT.search(text) and not unnamed, (
            f"{skin} scanned {missing} and does not disclose {unnamed or missing}"
        )


def test_a_report_without_a_language_census_still_discloses() -> None:
    """D167: an older stored report cannot rule the language out, so it keeps the caveat.

    Covers existing behaviour: without a census the caveat reads as it did
    before D167; this pins that the narrowing never applies to a report that
    cannot say which languages it scanned.
    """
    from maintainability_audit._evidence_view import unanchored_caveat
    from maintainability_audit.scoring import _reference_block

    score = {"reference": _reference_block()}
    assert score["reference"]["unanchored_languages"], "nothing unanchored to disclose"
    assert CAVEAT.search("\n".join(unanchored_caveat(score)))


_WORDS = {word: index for index, word in enumerate([
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty",
])}
_COUNT = re.compile(r"\b(\w+) of the (\w+) (?:parsed )?languages\b")


def _as_int(token: str) -> int:
    return int(token) if token.isdigit() else _WORDS[token.lower()]


def test_every_stated_count_of_corpus_languages_matches_the_corpus_lists(tmp_path) -> None:
    """D168: the prompt, every skin and the corpus note count the same two lists."""
    from maintainability_audit.report import build_report

    report = build_report(_tree(tmp_path, "counted"), _config(), run_analyzers=False)
    reference = report["score"]["reference"]
    held = len(reference["corpus_languages"])
    parsed = held + len(reference["unanchored_languages"])
    assert held, "the corpus lists no languages"
    surfaces = {**_skins(report), "corpus_note": reference["corpus_note"]}
    stated = {name: _COUNT.findall(text) for name, text in surfaces.items()}
    assert stated["prompt"], "the prompt printed no corpus count; nothing examined there"
    assert stated["corpus_note"], "the corpus note printed no count; nothing examined there"
    wrong = {
        name: [f"{a} of the {b}" for a, b in matches if (_as_int(a), _as_int(b)) != (held, parsed)]
        for name, matches in stated.items()
    }
    wrong = {name: bad for name, bad in wrong.items() if bad}
    assert not wrong, f"counts that disagree with {held} of {parsed}: {wrong}"
