# Changelog

All notable changes to Maintainability Agent will be documented here.

## 0.3.0 - 2026-05-23

Bug-fix release. Three independent false-positive sources observed during a downstream audit are eliminated; no breaking config changes.

- **fix(metrics): use `ast.end_lineno` for Python function/class line counts.** The detector previously computed the end of a function as "next sibling start − 1" (with end-of-file as the fallback), so a 4-line `Enum` followed by 300 lines of unrelated code reported 321 lines / complexity 23. Short Python functions and classes now report their actual indented body length. Non-Python files keep the regex fallback. `async def` is also detected now (the regex never matched it). New helpers: `_python_function_ranges`, `_regex_function_ranges` in `metrics.py`.
- **fix(scoring): testability/analyzability no longer punish test-only function pressure.** Refactoring duplicate test boilerplate into a shared fixture used to drop testability 0.9 → 0.4 and analyzability 0.7 → 0.3 even though the same assertions still passed. The summary now exposes `production_file_failures` / `production_function_failures` / `production_hard_gate_failures` (plus their warning + test-side counterparts), and `scoring.score_report` uses the production-only pressure for `testability` and `analyzability`. `modularity`, `reusability`, and `modifiability` keep their original combined-pressure formulas. New helper: `is_test_path` in `metrics.py`.
- **fix(metrics): duplicate-block detector skips low-information lines.** Five-line column-name lists collided between an INSERT column tuple and a function's keyword-argument signature, even though that shared ordering IS the architectural contract. Blocks made entirely of bare identifiers (e.g. `name,`), simple kwarg passthroughs (`x=x,`), or pure punctuation are now ignored. Real cross-file code duplication still surfaces (covered by a new regression test).
- **refactor(metrics):** extract `_compute_gates_and_summary`, `_function_hotspots`, `_count_status`, `_split_by_test_path` so the main `build_report` and `report_summary` stay inside the self-audit complexity threshold after the new logic lands.
- **tests:** +10 regression tests in `tests/test_audit_components.py` covering the three bugs (Enum-after-300-lines, single-return-then-def, empty-class-then-long-func, async def, fallback-on-SyntaxError, identifier-list dup skipping, real duplication still flagged, test-only function failure not dropping testability/analyzability, production/test summary split).
- **dogfood:** self-audit on this repo post-fix scores **4.6 / 5 (A)** under the project's strict local config (zero function failures, zero hard gates, 98% coverage).

## 0.2.0 - 2026-05-12

- Adds a portable invokable skill under `skills/maintainability-agent/` that drops into Codex, Claude Code, and GitHub Copilot Chat so `/maintainability-agent` is one keystroke away in any of them.
- Adds per-host adapters: `agents/openai.yaml` (Codex, already present), `agents/anthropic.yaml` (Claude Code install paths), `agents/copilot.yaml` (Copilot prompt-file source/destination).
- Adds `copilot/maintainability-agent.prompt.md` — VS Code Copilot Chat prompt file shaped for Copilot's prompt-file frontmatter; reuses the SKILL.md body verbatim.
- Documents the new install paths in README ("Invokable Skill / Slash Command" section + 5th bullet in the feature list).
- Updates SKILL.md description so Claude's relevance ranker fires correctly while staying valid for Codex.

## 0.1.0 - 2026-05-11

- Initial local implementation of deterministic maintainability auditing.
- Adds Markdown, JSON, SARIF, PR comment, baseline, and AI remediation prompt outputs.
- Adds model/tool-specific instruction generation for Claude Code, Codex, Cursor, Copilot, Windsurf, and generic agents.
- Adds 92% coverage gating, `coverage.xml` output, SonarQube Cloud starter config, and external quality-tool readiness docs.
- Self-audit on this codebase: **5.0 / 5 (A+)**, zero warnings across every category. Checked in at [docs/self-audit.md](docs/self-audit.md).
