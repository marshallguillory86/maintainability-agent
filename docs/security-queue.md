# Security queue — 2026-08-23

Two independent audits of `897c3d7` / `20b2460`, one by Grok (S-numbers)
and one by Codex (C-numbers), against seams three rounds of chat-surface
auditing had never looked at: write primitives, read boundaries, git
argv, supply chain, and analyzer trust.

Register entries are the record; this page is the working order. It
exists because the audits arrived as prose and the operator left for a
flight — a queue nobody can read is a queue that gets reordered by
whoever touches it last.

## The one decision that is not mine

**Are repositories trusted?** Both audits converge here (Grok R1,
Codex 2), and it is genuinely product intent, so it stays open until
Marshall rules.

Today the agent runs `eslint` such that it *requires* and executes the
audited tree's own configuration, and mypy and pylint can load
configured plugins. `SECURITY.md` says the agent does not execute
scanned code. Both cannot be true.

Two coherent answers:

1. **Repositories are trusted.** Correct `SECURITY.md`, the MCP
   annotations, and the architecture docs to say so plainly. Cheap,
   honest, and narrows who can safely run the tool.
2. **Repositories are untrusted.** Invoke analyzers with agent-owned
   configuration, `--no-eslintrc` / `--no-plugins`, and a scrubbed
   environment. Costs fidelity — a repository's own lint rules stop
   being what gets reported — and is a real product change.

Child sandboxing stays refused and neither option reopens it.

**Not started.** Picking either would be inventing intent.

## Order of work

Severity first, then blast radius. Everything here is decidable from
documents that already exist — a stated promise the code contradicts —
so none of it needs a ruling.

| # | Entry | What | State |
|---|---|---|---|
| 1 | D34 | Config, history and baseline writes open by name; hardlink and symlink escape | **closed** |
| 2 | D36 | `class_dirs`, `expand_files` and the scan itself follow paths out of the root | **closed** |
| 3 | D35 | Repository config can enable tool acquisition against P1 | **closed** |
| 4 | D40 | Repository-configured regex is a trivial ReDoS | queued |
| 5 | D42 | `requires-python` claims 3.10; `StrEnum` needs 3.11 | queued |
| 6 | D43 | Composite action interpolates inputs into Bash | queued |
| 7 | D41 | Release authority rides mutable third-party Action tags | queued |
| 8 | D45 | `SECURITY.md` supports `0.1.x`; the package is `0.9.1` | queued |
| 9 | D37 | CLI passes git options the MCP door rejects; no timeouts; swallowed errors | queued |
| 10 | D38 | A standing grant follows a renamed directory after restart | queued |
| 11 | D46 | XML parsers unbounded against analyzer output | queued |
| 12 | D44 | MCP annotations contradict behaviour | blocked on the trust decision |
| 13 | D39 | Analyzer configuration executes | blocked on the trust decision |

## Why green CI missed almost all of it

Codex's sharpest observation, and it deserves recording separately from
any one defect: the security tests prove *the package imports no HTTP
client*, while the package deliberately launches repository-programmable
children holding the host environment. The abstraction under test was
"does our code reach the network", when the risk was "what do we hand
the tree's own code".

Every fix below ships a falsifier. Several ship a lint, because the
defect classes here — open-by-name writes, unbounded configured paths —
were each closed once already at one seam and left open at the others.
