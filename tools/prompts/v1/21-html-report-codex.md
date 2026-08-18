# 21 Codex — HTML report that an executive can read

You are Codex. Tests and the one doc paragraph below. No src/.

Repo: maintainability-agent. Owner marshallguillory86.
Marshall rejected the HTML skin: unmarked charts, unreadable labels,
no glanceable result except the score, Markdown dumped in a pre.
Findings need Severe / High / Medium / Low. That is output, not a
score. Do not invent a second rubric.

Read docs/adr-011-three-report-presentations.md and
docs/standard.md (risk 1-5 on finding classes). One report dict.
No http(s). No script. Deterministic SVG.

    git fetch origin
    git switch -c test/html-executive origin/main
    git worktree add /tmp/ma-test-html-executive test/html-executive
    cd /tmp/ma-test-html-executive

If that branch exists on the remote, stop.

In docs/adr-011-three-report-presentations.md HTML section, add:
finding rows carry Severe/High/Medium/Low derived from the published
class risk (1-5 in standard.md / CLASS_RISK_EFFORT). Mapping:
5 Severe, 4 High, 3 Medium, 1-2 Low. Hard-gate failures display as
Severe. This label does not change estimate, range, or grade.

Write tests/test_html_executive.py from a real build_report fixture
(see tests/test_three_presentations.py audited). Do not import scoring.

1. Executive strip first, before charts. A skimmer reads without a
   chart: estimate, grade, gate clear vs not (hard_gate_failures),
   counts of Severe / High / Medium / Low findings, total findings,
   direction or empty-history sentence. A first screen that is only
   a score fails.

2. Metrics tables, not charts alone: S/H/M/L counts this scan;
   total findings per recorded scan (len(record.fingerprints)).
   Do not invent per-ISO-category finding counts over time. Category
   *scores* from stored record.categories may be a table.

3. Charts chart-estimate, chart-pillars, chart-practice,
   chart-categories: visible 0 and 5 ticks on 0-5 scales, pillar
   legend, no two text nodes at the same x,y, viewBox height > 200
   or explicit y-axis labels.

4. No single pre of the Markdown file. Finding tables are HTML.
   Each finding row shows S/H/M/L. Semantic findings still appear
   with the same paths as markdown.

5. Still: no script, no link css, no http(s), byte-identical twice,
   no scoring import. test_three_presentations headline tests stay.
   Enlarge test_the_executive_summary_leads's window if needed.

Verify (fails on origin/main):

    source /Users/marshallguillory/repos/maintainability-agent/.venv/bin/activate
    cd /tmp/ma-test-html-executive
    PYTHONPATH=src python -m pytest tests/test_html_executive.py tests/test_three_presentations.py -q

One commit. Push origin test/html-executive. No PR. Never push main.
