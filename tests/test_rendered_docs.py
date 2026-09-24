"""The documentation, all of it, in one readable form that cannot go stale.

`docs/html/` is a reading copy of every document this repository tracks:
the root documents, everything under `docs/`, and the standalone HTML pages
that already live there. The markdown stays the source of truth;
`tools/render_docs.py` produces the copy.

A reading copy is only worth having if it is complete and current, so both
are enforced rather than hoped for. The set of documents is read from git,
not from a list someone has to remember to extend — a new document that
has no page fails here, and so does a committed page that no longer
matches its markdown. That is docs-as-code applied to the docs' own
presentation: if the copy can drift without anything failing, it is
decoration.

Reading the set from git also keeps out what must never be published. The
agent instruction files are untracked on purpose in this public repository,
so a renderer that walked the directory would have shipped them.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "render_docs.py"
HTML = ROOT / "docs" / "html"


def _load():
    spec = importlib.util.spec_from_file_location("render_docs", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["render_docs"] = module
    spec.loader.exec_module(module)
    return module


render_docs = _load()


def _tracked_documents() -> set[str]:
    """What git tracks: root markdown, and markdown anywhere under docs/."""
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "*.md"],
                         capture_output=True, text=True, check=True).stdout.split()
    return {p for p in out if "/" not in p or p.startswith("docs/")}


def test_the_document_set_is_read_from_git() -> None:
    expected = _tracked_documents()
    assert len(expected) >= 60, "fewer documents than this repository has; the population is wrong"

    assert {str(p) for p in render_docs.sources(ROOT)} == expected


def test_every_tracked_document_has_a_page() -> None:
    missing = [rel for rel in sorted(_tracked_documents())
               if not (HTML / render_docs.page_name(Path(rel))).is_file()]

    assert not missing, f"documents with no rendered page — run tools/render_docs.py: {missing}"


def test_page_names_are_unique() -> None:
    """Three documents are called README.md; each still gets its own page."""
    names = [render_docs.page_name(p) for p in render_docs.sources(ROOT)]

    assert len(names) == len(set(names))


def test_an_untracked_file_is_never_rendered(tmp_path) -> None:
    """The agent instruction files are untracked on purpose; walking the tree would publish them."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("# Readme\n")
    (tmp_path / "docs" / "guide.md").write_text("# Guide\n")
    (tmp_path / "AGENTS.md").write_text("# Private\n")
    (tmp_path / "CLAUDE.md").write_text("# Private\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "README.md", "docs/guide.md"], check=True)

    assert {str(p) for p in render_docs.sources(tmp_path)} == {"README.md", "docs/guide.md"}


def test_the_index_reaches_every_page_and_every_standalone_html_document() -> None:
    index = (HTML / "index.html").read_text(encoding="utf-8")
    pages = {render_docs.page_name(p) for p in render_docs.sources(ROOT)}
    standalone = subprocess.run(["git", "-C", str(ROOT), "ls-files", "docs/*.html", "docs/**/*.html"],
                                capture_output=True, text=True, check=True).stdout.split()
    standalone = [p for p in standalone if not p.startswith("docs/html/")]
    assert standalone, "no standalone HTML documents found; this half of the check reads nothing"

    unreached = sorted(p for p in pages if f'href="{p}"' not in index)
    unreached += sorted(p for p in standalone if Path(p).name not in index)

    assert not unreached, f"the index does not link: {unreached}"


def test_every_link_between_pages_resolves() -> None:
    """A link to a document must land on its page, not on a missing file."""
    broken = []
    for page in HTML.glob("*.html"):
        for target in re.findall(r'href="([^"#:]+\.html)(?:#[^"]*)?"', page.read_text(encoding="utf-8")):
            if "/" not in target and not (HTML / target).is_file():
                broken.append(f"{page.name} -> {target}")

    assert not broken, broken[:20]


def test_rendering_is_deterministic(tmp_path) -> None:
    """No timestamps: the same markdown always renders the same bytes."""
    first, second = tmp_path / "a", tmp_path / "b"
    render_docs.render(ROOT, first)
    render_docs.render(ROOT, second)

    assert sorted(p.name for p in first.iterdir()) == sorted(p.name for p in second.iterdir())
    for page in first.iterdir():
        assert page.read_bytes() == (second / page.name).read_bytes(), page.name


def test_the_committed_copy_is_current(tmp_path) -> None:
    """A document changed without re-rendering fails here, not in a reader's tab."""
    fresh = tmp_path / "html"
    render_docs.render(ROOT, fresh)

    stale = sorted(p.name for p in fresh.iterdir()
                   if not (HTML / p.name).is_file() or (HTML / p.name).read_bytes() != p.read_bytes())
    orphaned = sorted(p.name for p in HTML.iterdir() if not (fresh / p.name).exists())

    assert not stale and not orphaned, (
        f"docs/html is out of date — run `python3 tools/render_docs.py`. "
        f"stale: {stale[:10]} orphaned: {orphaned[:10]}")
