# 12 Claude — Phase 8 (8.1–8.7): presentations and scoring continuity

Repo: maintainability-agent. Branch from current **main** after PR #37
merges (ADR 011 + Phase 8 on the plan). If #37 is not on main yet, wait
or rebase onto it. This prompt says implement. You are the coder.
One prompt. Do not wait on Codex.

Read first: `docs/adr-011-three-report-presentations.md`,
`docs/adr-009-scan-history.md` (schema 2 + append policy),
`docs/release-plan.md` Phase 8, `docs/architecture.md` presentation
rules. Do not invent product intent past those.

## Do (TDD: failing tests first if they are not on the tree)

**8.1 History schema 2.** New writes set `HISTORY_SCHEMA_VERSION` to 2
and store `categories`, `aspects`, `pillars`, `practice_level`,
`evidence_status` from the report that scan published. Schema 1 lines
still load. Pillars and practice are two series — never averaged
(ADR 007).

**8.2 Append when the file exists.** If `.maintainability/history.jsonl`
is present, a successful scan appends even without `--record-history`.
The first interactive run creates the file. CI / 6.4 still records
explicitly. A forgotten flag must not drop the current scan.

**8.3 One view model, three renderers.** Chat/CLI text (default),
Markdown file, one self-contained HTML file. Same report dict. None
compute a score. They must not disagree on estimate, range, grade, or
finding identity.

**8.4 Format ask.** Every TTY invoke with no format/output flag asks
which of the three; Enter = chat. Non-TTY never `input()`.
`--format` / `--output` / `--html-output` skip the question and win.
Do not persist the choice.

**8.5 MCP.** Prompt tells the host to ask, then call the tool with a
format argument. Tool does not prompt and does not write the tree.
Chat returns Markdown. Files are CLI-only.

**8.6 HTML.** One file, inlined CSS, deterministic SVG from **stored**
records (no CDN, no `http://`/`https://` resource loads). Executive
summary first (estimate, grade, range, series direction or “no history
yet”). Required charts: estimate+range over time, **pillars over
time**, **practice/maturity over time**, current-run category bars.
Schema-1 scans may appear on the rollup series and are gaps on
pillar/practice charts. Empty history = empty state, not a fake chart.

**8.7 Honesty.** Flip register / cli.md / README / Phase 8 rows to
**Shipped** only for what the tests prove. Do not mark 8.8–8.10 done.

## Do not

- Import `_bands` into the scorer or re-derive `CALIBRATION_C`.
- Start 7.5 / 8.8 / 8.9 / tag.
- Make MCP write files.
- Forecast. Average pillars with practice.
- Install tools. File budget 500, CCN 15.

## Verify

```
PYTHONPATH=src python3 -m pytest tests/test_scan_history.py tests/test_trends.py tests/test_cli.py tests/test_mcp_server.py tests/test_docs_links.py tests/test_release_plan_status.py -q
```

plus the new tests this slice adds.

Wrap-up: files, tests, still open.
