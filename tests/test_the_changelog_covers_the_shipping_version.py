"""A release's notes come from this file, so the section has to exist (D204).

The GitHub Release job extracts the `## X.Y.Z` section for the tag it is
publishing and, finding none, writes the sentence `Release X.Y.Z.` and
publishes that as the release notes:

    awk -v v="$version" '...' CHANGELOG.md > notes.md
    [ -s notes.md ] || echo "Release $version." > notes.md

The fallback is right for a re-pointed or recovery tag. It was not
supposed to be the normal path, and for twelve consecutive tags it was:
this file stopped at 3.7.7 while 3.7.8 through 3.7.19 shipped, each one
publishing that one sentence to everybody watching the repository.
Nothing failed, because the fallback is what "no section" means to
`awk`, and a substituted placeholder looks exactly like a deliberate
one-line release note from outside.

So the check is placed where a release is *prepared* rather than where
it is published — the ordinary suite, which the release build re-runs
against the installed wheel. By the time the publishing job could
notice, the tag exists, which is the same "after anyone would have
noticed" problem D124 and D200 both record.

The version is read from the package rather than named here, so this
follows every bump without being edited.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"


def _sections() -> list[str]:
    """Every version this file documents, in file order."""
    return re.findall(r"^## (\d+\.\d+\.\d+)", CHANGELOG.read_text(encoding="utf-8"), re.MULTILINE)


def test_the_shipping_version_has_a_changelog_section() -> None:
    """The one that would have failed twelve times in a row."""
    from maintainability_audit import __version__

    documented = _sections()

    assert documented, "no version sections at all; the extractor would find nothing to publish"
    assert __version__ in documented, (
        f"CHANGELOG.md has no `## {__version__}` section, so the release job "
        f"would publish the words 'Release {__version__}.' as its entire notes. "
        f"Newest documented: {documented[0]}"
    )


def test_the_section_is_not_empty() -> None:
    """A heading with nothing under it extracts to nothing, same as absent.

    `awk` prints the lines between this heading and the next. A section
    that is only a heading satisfies "the version is documented" and
    still leaves `notes.md` empty, which trips the same fallback — the
    check above would pass and the release would still say nothing.
    """
    from maintainability_audit import __version__

    text = CHANGELOG.read_text(encoding="utf-8")
    start = re.search(rf"^## {re.escape(__version__)}\b.*$", text, re.MULTILINE)

    assert start, "no section for the shipping version; the test above says why"
    rest = text[start.end():]
    body = rest.split("\n## ", maxsplit=1)[0]

    assert body.strip(), (
        f"the `## {__version__}` section is empty, so the extracted notes are "
        "empty and the release publishes its placeholder anyway"
    )
