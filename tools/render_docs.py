#!/usr/bin/env python3
"""Render every document in this repository into one readable HTML copy.

The markdown stays the source of truth; `docs/html/` is a reading copy of
all of it — the root documents, everything under `docs/`, and cards for
the standalone HTML documents that already live there — so the whole body
of documentation can be read in one place instead of file by file.

The set of documents is read from git rather than from a list: a new
document gets a page without anyone remembering to add it, and a file git
does not track is never rendered. That second half matters here. The agent
instruction files are untracked on purpose in this public repository, and a
renderer that walked the directory would publish them.

Output is deterministic — no timestamps — so `tests/test_rendered_docs.py`
can prove the committed copy matches its markdown. Change a document,
re-run this, commit both.

Adapted from the cq-team documentation renderer; styles in
`tools/render_docs.css`.

Usage: python3 tools/render_docs.py [output_dir]      # default: docs/html
"""

from __future__ import annotations

import html
import os
import re
import shutil
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Every git call in this repository goes through run_git: a fixed argv, never
# a shell, a timeout, and a read-only config. Code scanning flagged the first
# cut of this tool for calling subprocess itself.
from maintainability_audit.git_tools import run_git  # noqa: E402

STYLES = Path(__file__).with_suffix(".css")
BRAND = "maintainability-agent"
#: Where the reading copy lives, relative to the repository root.
HOME = Path("docs/html")

#: Groups, in index order. The first matching rule wins; anything unmatched
#: is Reference, so a new document always lands somewhere.
GROUPS = [
    ("Project", lambda rel: len(rel.parts) == 1),
    ("Product and standard", lambda rel: rel.name in {
        "product-intent.md", "why-this-exists.md", "philosophy.md", "standard.md",
        "report-contract.md", "language-support.md"}),
    ("Help", lambda rel: rel.parts[:2] == ("docs", "help")),
    ("Languages", lambda rel: rel.parts[:2] == ("docs", "languages")),
    ("Decisions", lambda rel: rel.name.startswith("adr-") or rel.name == "decisions.md"),
    ("Audits and registers", lambda rel: rel.parts[:2] == ("docs", "audits") or rel.name in {
        "self-audit.md", "defect-register-chat-surface.md", "security-queue.md", "track-record.md"}
        or rel.name.startswith("audit-")),
    ("Plan and evidence", lambda rel: rel.name in {
        "roadmap.md", "release-plan.md", "studies.md", "calibration-2.0-study.md",
        "semantic-prototype.md", "target-architecture.md"}),
]
DEFAULT_GROUP = "Reference"


def sources(repo: Path) -> list[Path]:
    """Every tracked markdown document at the root or under docs/."""
    listed = run_git(["ls-files", "*.md"], repo).split()
    return sorted(Path(p) for p in listed if "/" not in p or p.startswith("docs/"))


def standalone_html(repo: Path) -> list[Path]:
    """HTML documents that already exist, which the index links as they are."""
    listed = run_git(["ls-files", "docs/*.html", "docs/**/*.html"], repo).split()
    return sorted(Path(p) for p in listed if not p.startswith("docs/html/"))


def page_name(rel: Path) -> str:
    """One stable, unique page per document.

    Three documents are called README.md, so a nested page carries its
    folder: `docs/help/README.md` is `help.html`, `docs/languages/go.md` is
    `languages-go.html`. A version in a file name is dropped, so a bookmarked
    page survives a version bump.
    """
    stem = re.sub(r"[-_]v\d+\.\d+\.\d+$", "", rel.stem)
    if len(rel.parts) == 1:
        return f"{stem.lower()}.html"
    inner = rel.parts[1:-1]
    if stem == "README":
        return f"{'-'.join(inner) or 'docs'}.html"
    return f"{'-'.join((*inner, stem))}.html"


def group_of(rel: Path) -> str:
    for name, rule in GROUPS:
        if rule(rel):
            return name
    return DEFAULT_GROUP


def title_of(text: str, rel: Path) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return rel.stem


def _without_first_heading(text: str) -> str:
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("# "):
            return "".join(lines[:index] + lines[index + 1:])
    return text


def _anchor(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _rewrite_links(body: str, rel: Path, pages: dict[str, str], out_rel: Path) -> str:
    """Point each relative link at its page, or at the file it names."""
    def repl(match: re.Match) -> str:
        href = match.group(1)
        if href.startswith(("http:", "https:", "#", "mailto:")):
            return match.group(0)
        path, _, fragment = href.partition("#")
        target = Path(os.path.normpath(rel.parent / path)).as_posix()
        suffix = f"#{fragment}" if fragment else ""
        if target in pages:
            return f'href="{pages[target]}{suffix}"'
        return f'href="{Path(os.path.relpath(target, out_rel)).as_posix()}{suffix}"'
    return re.sub(r'href="([^"]+)"', repl, body)


def _nav(groups: list[str]) -> str:
    return "".join(f'<a href="index.html#{_anchor(g)}">{html.escape(g)}</a>' for g in groups)


def _page(title: str, body: str, toc: str, nav: str, meta: str, footer: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · {BRAND}</title>
<link rel="stylesheet" href="style.css"></head><body>
<div class="top"><div class="top-inner"><a class="brand" href="index.html">{BRAND} docs</a><nav>{nav}</nav></div></div>
<div class="layout"><aside><p class="label">On this page</p>{toc}</aside>
<main><div class="meta">{meta}</div>{body}
<footer>{footer}</footer>
</main></div></body></html>
"""


def _render_document(repo: Path, rel: Path, out: Path, pages: dict[str, str], nav: str) -> tuple[str, str]:
    """Write one document's page; return its group and title."""
    text = (repo / rel).read_text(encoding="utf-8")
    title = title_of(text, rel)
    converter = markdown.Markdown(extensions=["tables", "toc", "fenced_code", "sane_lists"],
                                  extension_configs={"toc": {"toc_depth": "2-3"}})
    body = converter.convert(_without_first_heading(text))
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    body = _rewrite_links(body, rel, pages, HOME)
    group = group_of(rel)
    footer = (f"Rendered from <code>{html.escape(rel.as_posix())}</code> in the {BRAND} repository. "
              "The markdown is the source of truth.")
    (out / pages[rel.as_posix()]).write_text(
        _page(title, f"<h1>{html.escape(title)}</h1>{body}", converter.toc, nav, group, footer),
        encoding="utf-8")
    return group, title


def _render_index(out: Path, cards: dict[str, list[tuple[str, str, str]]], counts: tuple[int, int], nav: str) -> None:
    """Write the index: one card per page, grouped, then the standalone documents."""
    filled = [(g, items) for g, items in cards.items() if items]
    sections = "".join(
        f'<h2 id="{_anchor(g)}">{html.escape(g)}</h2><div class="cards">'
        + "".join(f'<a class="card" href="{href}"><div class="t">{html.escape(t)}</div>'
                  f'<div class="v">{html.escape(sub)}</div></a>' for t, href, sub in items)
        + "</div>"
        for g, items in filled)
    toc = "<ul>" + "".join(f'<li><a href="#{_anchor(g)}">{html.escape(g)}</a></li>' for g, _ in filled) + "</ul>"
    intro = (f"<h1>{BRAND} documentation</h1><p>Every document in the repository, in one readable place: "
             f"{counts[0]} rendered from markdown, plus {counts[1]} standalone pages. The markdown "
             "in the repository remains the source of truth.</p>")
    (out / "index.html").write_text(
        _page("Documentation", intro + sections, toc, nav, "Index",
              "Rendered by <code>tools/render_docs.py</code>. The markdown is the source of truth."),
        encoding="utf-8")


def render(repo: Path, out: Path) -> list[Path]:
    """Write the whole reading copy into `out`, replacing what was there.

    Links to repository files are written for where the copy lives,
    docs/html (`HOME`), wherever this call writes it. Computing them from
    `out` made a copy rendered elsewhere differ from the committed one.
    """
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("*.html")) + list(out.glob("*.css")):
        old.unlink()

    docs = sources(repo)
    pages = {rel.as_posix(): page_name(rel) for rel in docs}
    group_names = [g for g, _ in GROUPS] + [DEFAULT_GROUP]
    nav = _nav(group_names)
    cards: dict[str, list[tuple[str, str, str]]] = {g: [] for g in group_names}
    for rel in docs:
        group, title = _render_document(repo, rel, out, pages, nav)
        cards[group].append((title, pages[rel.as_posix()], rel.as_posix()))

    standalone = [(p.stem.replace("_", " "), Path(os.path.relpath(p, HOME)).as_posix(), p.as_posix())
                  for p in standalone_html(repo)]
    if standalone:
        cards["Standalone documents"] = standalone
    _render_index(out, cards, (len(docs), len(standalone)), nav)
    shutil.copyfile(STYLES, out / "style.css")
    return docs


def main(argv: list[str]) -> int:
    out = Path(argv[1]).expanduser() if len(argv) > 1 else ROOT / "docs" / "html"
    docs = render(ROOT, out)
    print(f"rendered {len(docs)} documents and an index to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
