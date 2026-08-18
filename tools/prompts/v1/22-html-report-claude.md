# 22 Claude — rebuild the HTML report

You are Claude. Implementor. Do not rewrite Codex’s tests.

Repo: maintainability-agent. Owner marshallguillory86.
HTML is a consumable report, not a data dump and not a score poster.
Finding severity is Severe / High / Medium / Low. That is output.
It does not change the 0-5 score, range, or grade.

    git fetch origin
    git switch -c feat/html-executive origin/main
    git worktree add /tmp/ma-feat-html-executive feat/html-executive
    cd /tmp/ma-feat-html-executive

STOP if origin/test/html-executive does not contain
tests/test_html_executive.py.

    git checkout origin/test/html-executive -- \
      tests/test_html_executive.py \
      tests/test_three_presentations.py \
      docs/adr-011-three-report-presentations.md

Do not edit those after checkout.

Edit src/maintainability_audit/_html_view.py (split a module if it
would exceed 500 lines). Do not import scoring. No script. No http(s).

Severity from published class risk (CLASS_RISK_EFFORT / standard.md):
5 Severe, 4 High, 3 Medium, 1-2 Low. Hard-gate items display Severe.
Put the label on each finding row. Count them in the executive strip.

1. Executive strip first: estimate, grade, gate clear vs not,
   S/H/M/L counts, total findings, direction or empty history.
   Readable. Not a muted footnote under a giant score.

2. Metrics tables above or beside charts: S/H/M/L this scan;
   findings per recorded scan from len(fingerprints). No invented
   category-count time series.

3. SVG: axes, 0 and 5 ticks, titles, pillar legend, padding so
   labels do not clip or sit on the line. Same four chart ids.
   Schema-1 still gaps.

4. No Markdown-in-a-pre. Work order, semantic findings, coverage,
   finding tables as HTML. Same identities as render_markdown.

Leave cli.py and scoring alone.

Verify:

    source /Users/marshallguillory/repos/maintainability-agent/.venv/bin/activate
    cd /tmp/ma-feat-html-executive
    PYTHONPATH=src python -m pytest tests/test_html_executive.py tests/test_three_presentations.py tests/test_promises.py -q
    .venv/bin/ruff check src/maintainability_audit/_html_view.py

Then a broader suite. One commit. Push feat/html-executive. No PR
unless Marshall says so. Never push main.
