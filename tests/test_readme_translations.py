"""The README's language row and badge row (Decision 20).

Each translation is a short page that points to the English README as the
only complete copy, says it is a machine translation, and carries no version
number, so a README change never leaves it stale. The set of languages is read
from the README's own language row, so a page added to the row without a file,
or a file the row does not reach, fails here.

Each badge is a shields.io image whose target is checked against this
repository: the package name, the owner, and a workflow file that exists.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
LANGUAGES = {"es", "de", "fr", "hi", "zh-CN"}
NOTICE = "<!-- machine translation of README.md; the English README is the complete copy -->"


def _language_row(text: str) -> list[str]:
    """The README.<code>.md targets of the first line that links any."""
    row = next(line for line in text.splitlines() if "](README." in line)
    return re.findall(r"\]\(README\.([A-Za-z-]+)\.md\)", row)


def test_the_readme_links_exactly_the_decided_languages() -> None:
    assert set(_language_row(README)) == LANGUAGES


@pytest.mark.parametrize("code", sorted(LANGUAGES))
def test_each_translation_is_a_short_dated_free_page_that_points_home(code: str) -> None:
    text = (ROOT / f"README.{code}.md").read_text(encoding="utf-8")

    assert text.startswith(NOTICE)
    assert "](README.md)" in text
    assert "pip install maintainability-agent" in text
    assert not re.search(r"\b\d+\.\d+\.\d+\b", text), "a version number goes stale"
    assert len(text.split()) < 400 or code == "zh-CN" and len(text) < 2000
    assert set(_language_row(text)) == LANGUAGES - {code}


def _badges(text: str) -> list[tuple[str, str]]:
    """(image, link) for every shields.io badge."""
    return re.findall(r"\[!\[[^\]]*\]\((https://img\.shields\.io/[^)]+)\)\]\(([^)]+)\)", text)


def test_every_badge_names_this_package_owner_and_a_real_workflow() -> None:
    badges = _badges(README)
    assert len(badges) >= 4

    for image, link in badges:
        assert "outcomes360" not in image + link
        if "/pypi/" in image:
            assert image.split("/pypi/")[1].split("/")[1].split("?")[0] == "maintainability-agent"
        if "/github/" in image:
            assert "marshallguillory86/maintainability-agent" in image
        for workflow in re.findall(r"workflows/([\w.-]+\.yml)", image + link):
            assert (ROOT / ".github" / "workflows" / workflow).is_file(), workflow
