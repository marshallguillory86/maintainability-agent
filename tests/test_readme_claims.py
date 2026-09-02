"""The front page is a claim, and it is checked like one.

Split from `test_written_record.py` in 1.5.1, which had crossed this
project's 500-line file gate — the same reason `test_release_plan.py`
was split out of it before.

They belong together anyway. `docs/` is held to the code by several
guards; the README carries its own shorter version of the same claims
and is what most people actually read, so it drifted while the
documentation it summarises stayed true. Its version line sat at 1.0.0
through five releases, and its language table named neither the JS/TS
suffixes nor half of Fortran's.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_readme_names_the_shipped_version() -> None:
    """D45 again, one file over.

    `SECURITY.md` is guarded because it went eight release lines stale
    and nobody looked. The README's own version line had no guard at
    all, and it sat at **1.0.0** through 1.1, 1.2, 1.3, 1.4 and 1.5 —
    the first thing a reader sees, naming a release five behind, while
    four languages were added underneath it.

    Checked against `config.VERSION` rather than a written-in number, so
    the next release either updates the line or fails here.
    """
    from maintainability_audit.config import VERSION

    readme = _read(ROOT / "README.md")
    assert f"Version **{VERSION}**" in readme, (
        f"README.md does not name the shipped version {VERSION}; its "
        "header has drifted from the package"
    )


def test_the_readme_language_table_lists_every_parsed_language() -> None:
    """The claim a reader scans first must match the parser.

    `docs/language-support.md` is already held to `DECLARATION_SUFFIXES`
    in both directions. The README carries its own shorter table, which
    is what most people actually read, and nothing tied it to anything —
    so a language could ship parsed, documented in `docs/`, and missing
    from the front page.
    """
    import re

    from maintainability_audit.declarations import DECLARATION_SUFFIXES

    readme = _read(ROOT / "README.md")
    table = readme.split("## Language support", maxsplit=1)[1].split(
        "## What it produces", maxsplit=1
    )[0]
    named = {
        suffix
        for row in table.splitlines() if row.startswith("| ")
        for suffix in re.findall(r"`(\.[A-Za-z][A-Za-z0-9]*)`", row)
    }
    missing = sorted(DECLARATION_SUFFIXES - named)
    assert not missing, (
        f"the README language table does not name {missing}, which the "
        "parser reads; the front page under-claims what ships"
    )
