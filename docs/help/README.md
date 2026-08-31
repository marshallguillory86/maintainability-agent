# Help for the chat workflow

The primary surface for maintainability-agent is an AI chat host driving the
local MCP process. After configuration is answered and the user chooses to
run, the deterministic audit measures the repository and returns a bounded
work order; the host shows it to the coding agent without granting permission
for unrelated refactoring. The CLI is the automation and CI surface.
**Chat, MCP, and an interactive CLI TTY are one setup: the same questions.**

Start with the part of the conversation you need:

- [First run and questions](first-run.md) — setup, repository grants, history
  consent, and when a report file may be saved.
- [What the analyzer pool runs](analyzer-pool.md) — analyzer-primary evidence,
  built-in fallback, selection, and missing-tool remedies.
- [Reading the report and its history](report-and-history.md) — estimate,
  range, grade, work order, recurrence, baselines, and economic context.

For integration details, see [IDE and agent integration](../ide-agent-integration.md).
For the binding product promises, see [product intent](../product-intent.md).
