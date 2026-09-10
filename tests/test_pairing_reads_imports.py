"""A unit is paired when a test *imports* it, not only when one is named for it.

Pairing was filename-only: a production file counted as tested when some
test file's subject stem matched it. That encodes one convention —
`test_scoring.py` covers `scoring.py` — and reports every repository
organising its suite by *behaviour* as having untested production code.

`_test_pairing`'s own docstring already named this failure for a newly
added language: *"a confident finding, wrong on every project, of exactly
the kind this tool exists to prevent."* The rule did it to itself.
Measured on the repository that ships it: 58 modules reported unpaired,
52 imported by a test, suite coverage 94.46% (D149).

The population here is the import forms of every pairable language, taken
from `PAIRABLE` rather than listed by hand, so a language added to that
constant without teaching this scanner its import syntax fails here
instead of silently reporting that language's repositories as untested.
"""
from __future__ import annotations

import pytest

from maintainability_audit._metrics_types import FileMetric
from maintainability_audit._test_pairing import (
    PAIRABLE,
    describe_tdd,
    referenced_subjects,
)


def _file(path: str, status: str = "ok") -> FileMetric:
    return FileMetric(path=path, lines=10, status=status)


# --- the scanner, per language --------------------------------------------

@pytest.mark.parametrize(("source", "expected"), [
    ("from maintainability_audit._generic import parse_json_lines", "_generic"),
    ("import maintainability_audit.scoring", "scoring"),
    ("import scoring", "scoring"),
    ("from .renderers import summary_table", "renderers"),
    ("import { render } from './_html_view.ts'", "_html_view"),
    ("import thing from '../lib/report'", "report"),
    ("const r = require('./scoring.js')", "scoring"),
    ("const lazy = await import('./duplication.mjs')", "duplication"),
    ("import com.example.deep.Widget;", "widget"),
    ("import static com.example.Helper.thing;", "helper"),
    ("use gravity_mod", "gravity"),
    ("USE Gravity", "gravity"),
])
def test_an_import_form_names_its_subject(source: str, expected: str) -> None:
    assert expected in referenced_subjects(source), (
        f"{source!r} did not resolve to {expected!r}: {sorted(referenced_subjects(source))}"
    )


def test_a_file_extension_is_not_read_as_a_module_segment() -> None:
    """`./scoring.js` names `scoring`, never `js`.

    A dot separates module segments in `pkg.scoring` and introduces a
    file extension in `./scoring.js`. Reading the extension as the
    subject pairs every JavaScript file in a tree against any test that
    imports any other one — silently, and in the direction that reports
    less work than exists.
    """
    subjects = referenced_subjects("import x from './scoring.js'")
    assert "scoring" in subjects
    assert "js" not in subjects


def test_a_javascript_binding_name_is_not_a_subject() -> None:
    """`import y from './report'` names `report`, not `y`.

    Python's bare `import X` and JavaScript's `import X from '…'` start
    identically. Collecting the binding name pairs a production file
    that happens to share it against a test that never mentions it.
    """
    subjects = referenced_subjects("import y from '../lib/report'")
    assert "report" in subjects
    assert "y" not in subjects


def test_prose_that_merely_talks_about_importing_names_nothing() -> None:
    assert referenced_subjects('note = "we should import scoring here"') == set()
    assert referenced_subjects("") == set()


def test_every_pairable_language_has_an_import_form_exercised_here() -> None:
    """Derived from `PAIRABLE`, so a new language cannot arrive unexercised.

    Covers existing behaviour: this asserts the population of this file's
    own cases, which is the falsifier standard's non-vacuity clause.
    """
    assert PAIRABLE, "no pairable suffixes; every case here would be vacuous"
    families = {
        ".py": "python", ".js": "javascript", ".jsx": "javascript",
        ".mjs": "javascript", ".cjs": "javascript", ".ts": "typescript",
        ".tsx": "typescript", ".java": "java",
        ".f90": "fortran", ".f95": "fortran", ".f03": "fortran", ".f08": "fortran",
        ".F90": "fortran", ".F95": "fortran", ".F03": "fortran", ".F08": "fortran",
    }
    unknown = sorted(suffix for suffix in PAIRABLE if suffix not in families)
    assert not unknown, (
        f"PAIRABLE gained {unknown} with no import form exercised in this "
        "file; a language paired by filename alone reports its repositories "
        "as untested production code"
    )


# --- the rule end to end ---------------------------------------------------

def test_a_module_imported_by_a_behaviour_named_test_is_paired(tmp_path) -> None:
    """The defect, reproduced end to end and then absent.

    `test_declarative_parsers.py` covers `_generic.py`. No filename rule
    can see that; the import can.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "scoring.py").write_text("def total():\n    return 1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_it_adds_up.py").write_text(
        "from src.scoring import total\n\ndef test_total():\n    assert total() == 1\n",
        encoding="utf-8",
    )
    described = describe_tdd(
        tmp_path,
        [_file("src/scoring.py"), _file("tests/test_it_adds_up.py")],
        [],
    )
    assert described["paired_production_files"] == 1, (
        "a module imported by its test is unpaired; pairing is still "
        "filename-only"
    )


def test_a_module_no_test_names_or_imports_is_still_unpaired(tmp_path) -> None:
    """The rule must still find real gaps, or the fix removed the check.

    A widened rule that pairs everything is worse than the narrow one it
    replaced: it reports no work and looks clean.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "orphan.py").write_text("def lonely():\n    return 0\n", encoding="utf-8")
    (tmp_path / "tests" / "test_something_else.py").write_text(
        "def test_nothing():\n    assert True\n", encoding="utf-8")
    described = describe_tdd(
        tmp_path,
        [_file("src/orphan.py"), _file("tests/test_something_else.py")],
        [],
    )
    assert described["paired_production_files"] == 0, (
        "a module nothing names or imports was reported paired"
    )
