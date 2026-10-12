# What the analyzer pool runs

The validated analyzer pool is the primary evidence source. Built-in detectors
always run as the fallback for concepts the selected analyzers cannot measure.
The report names the evidence tier used for its estimate; missing evidence is
not a clean result.

Configuration selects tools by concern, depth, license policy, language, and
explicit allow/deny rules. `analyzers.run` controls whether the pool runs;
explicit per-call choices override it. Tool acquisition remains opt-in: a user
may enable `analyzers.acquire_tools` in user-tier configuration, but the
audited tree cannot enable it.

Every selected tool records an outcome and version or an unavailable reason.
When a selected analyzer cannot run, the top-level `environment_work_order`
names the tool, an install command, and the concepts installation would
restore. The chat host surfaces that order rather than hiding it inside a JSON
report body.

**Language decides which tools are eligible**, so the pool a repository gets is
not the pool the catalog holds. A tool is offered only for languages it
declares. That cuts both ways: a language the built-in scanner cannot parse may
still be measured by an adapter, and a language the scanner parses may still
have no adapter available — Fortran gained one in 1.5.0 (fortitude), but it
emits verdicts and cannot supply a declaration population, so the built-in
scanner remains the only path to one there. Where neither layer can measure a
concept, the report withholds rather than estimates.

Selection filters the catalog by the configured policy. Source-read and
artifact-read adapters compose in one report without manufacturing
agreement across unlike findings
(`tests/test_d15_composition.py`; D15 in the
[chat-surface defect register](../defect-register-chat-surface.md)).

## Analyzers your own pipeline runs

This tool runs a pinned handful of the analyzers it catalogs. The rest run
where you already run them — a .NET build runs the Roslyn analyzers, and
executes code from the repository it builds, which this tool never does — and
it reads what they wrote (Decision 17). Declare each SARIF file in
`maintainability-agent.json`, or answer `declare` at first-run setup:

```json
"analyzers": {"pipeline_results": [
  {"path": "artifacts/roslyn.sarif", "covers": ["style", "documentation", "dead-code"]}
]}
```

`covers` is yours to state, from the same concerns `analyzers.concerns`
takes, because one file can mix rule families. A declared file turns those
concerns from unexamined to examined for the languages its results name —
add `"languages": ["C#"]` for a clean run that names no file. Its findings
are listed and, for now, do not move the grade. The report says when the file
is older than the last commit, and when a declared file cannot be read.

