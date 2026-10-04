"""A committed docs site rendered from Markdown is not scored as source (#292).

Every repository now commits an HTML site rendered from its Markdown, and
the audit scored it as source: each page duplicated its Markdown, so
duplicate blocks doubled; a debt marker in `README.md` was reported again in
`docs/html/readme.html`, where editing it is forbidden and re-rendering
reproduces it; and a long page drew "split along a real boundary" advice
with nobody to take it. secure-code-agent measured it: files 160 → 195,
duplicate blocks 22 → 44, risk findings 5 → 8, from the site alone.

Not a `docs/html/` exclusion: a directory-name rule is what ADR 010 rejected.
The renderer declares what it wrote, with the `@generated` banner discovery
already honours, and discovery does the rest for any repository whose
renderer says so.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from maintainability_audit.config import load_config
from maintainability_audit.report import build_report

ROOT = Path(__file__).resolve().parents[1]


def _renderer():
    spec = importlib.util.spec_from_file_location("render_docs_under_test", ROOT / "tools" / "render_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_rendered_page_declares_itself_generated(tmp_path: Path) -> None:
    out = tmp_path / "html"
    _renderer().render(ROOT, out)
    pages = sorted(out.glob("*.html"))

    # `render` returns the Markdown sources, not the pages; reading the
    # output directory is what makes this about what was written.
    assert len(pages) > 10, "the renderer wrote too few pages; this test would pass vacuously"
    unstamped = [p.name for p in pages
                 if "@generated" not in p.read_text(encoding="utf-8").splitlines()[0]]
    assert unstamped == []


def test_a_stamped_page_is_not_scored_beside_its_markdown(tmp_path: Path) -> None:
    banner = _renderer().GENERATED_BANNER
    (tmp_path / "README.md").write_text("# Title\n\nTODO: settle this.\n", encoding="utf-8")
    (tmp_path / "docs" / "html").mkdir(parents=True)
    (tmp_path / "docs" / "html" / "readme.html").write_text(
        f"{banner}\n<!doctype html><html><body><p>TODO: settle this.</p></body></html>\n",
        encoding="utf-8")
    (tmp_path / "app.py").write_text("def f():\n    return 1\n", encoding="utf-8")

    report = build_report(tmp_path, load_config(None))

    paths = {finding["path"] for finding in report["risk_findings"]}
    assert "docs/html/readme.html" not in paths
    assert "README.md" in paths
