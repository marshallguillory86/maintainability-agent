# ADR 013 — The hostile-audit prompt

- Status: Proposed (2026-08-30). Implementation progress belongs in the
  [decision register](decisions.md), not here.
- Related: [ADR 003](adr-003-deterministic-semantic-policy.md) (a
  non-gating finding class that never touches the score),
  [ADR 008](adr-008-translation-and-decision.md) (the LLM boundary and
  the prompt seam), [product intent](product-intent.md) (P1 determinism;
  the falsifiable-promise table).

## The problem

This tool is built by hostile audits. An adversary — Grok, so far —
reads a change and tries to make a stated promise false: a symlinked
write that escapes the grant, an empty analyzer run priced as clean, a
type check that never ran reported as a pass. Every accepted finding
becomes a **population-derived falsifier** that fails without its fix,
and the goal is the one [product intent](product-intent.md) already
states: *"A hostile audit finds nothing that a stated invariant did not
already cover."* The promises P1–P8 are named with the thing that would
falsify each.

That loop is the highest-leverage quality process the project has, and
it is the only one with no artifact. Remediation has `render_ai_prompt`;
agent standards have `render_agent_instructions` — deterministic prompts
the tool emits so an LLM can do the non-deterministic part outside. The
hostile audit has nothing. It depends on a human hand-writing a fresh
prompt into a fresh session, re-deriving context the report already
holds, with audit quality riding on whoever wrote the prompt that day.
It is not repeatable, not seeded, and not comparable run to run.

The obvious shortcut is the wrong one. Determinism (P1) is the product's
identity — the score is reproducible byte for byte — and an LLM
red-team **inside** the audit would give a different answer every run:
it could not gate, could not be compared, and "send code to an LLM by
default" is a stated non-goal. The adversarial *reasoning* cannot live
in the deterministic core.

## Options considered

1. **Embed an LLM red-team in the audit.** Rejected. Non-deterministic
   reasoning in the deterministic core breaks P1 outright; a hostile
   result that changes between identical runs is not evidence, and
   routing the tree to an LLM by default is a non-goal. This is the same
   line ADR 012 drew for builds: the core does not take on a capability
   that trades the product's strongest claim for one activity's output.

2. **Leave it ad-hoc.** Honest but wasteful. The loop that finds the
   real holes is the only one with no repeatable, seeded artifact; each
   audit re-derives what the report already computed — what ran, what
   did not, which promises the change touches — and the result is only
   as good as the prompt a person improvised.

3. **Emit a deterministic hostile-audit prompt; delegate the reasoning
   outward.** Seed the adversary from the report and the commit under
   audit; the LLM does the adversarial thinking outside the process,
   exactly as remediation delegates the fixing. Deterministic input,
   deterministic prompt text, non-deterministic work kept out of the
   core.

## Resolution

Option 3. A `render_hostile_audit_prompt(report)` on the existing prompt
seam — surfaced as a CLI `--hostile-prompt` output and an MCP prompt —
that produces a bounded adversarial brief, deterministically, from what
the audit already knows:

- **The promises in scope.** P1–P8 and the invariants the changed code
  touches, each named with its stated falsifier, so the adversary starts
  from the claims rather than inventing a target.
- **The evidence already computed.** Coverage, what ran and what did
  not, the declaration population, the write boundary — so the audit
  begins where measurement ended and does not re-derive it.
- **The audit contract, stated.** Reproduce, do not speculate: a finding
  is a concrete input → wrong output, not a worry. Every accepted
  finding must become a population-derived falsifier that fails without
  its fix. A real hole and a population-derived claim are different
  outcomes and are labeled as such. (This is the standard these audits
  already hold themselves to; the prompt writes it down.)

The prompt is **text the tool returns** — never a report it writes,
never code it sends anywhere itself (P1, the MCP five-artifact write
boundary). The boundary sentence:

> The deterministic core **seeds** the hostile audit; it never
> **performs** it.

## Consequences

- The loop that builds this tool becomes a first-class, repeatable step:
  seeded, bounded, reproducible input, comparable across runs, and
  usable by any model or IDE agent (Grok, Claude, Codex) the same way
  the remediation prompt already is.
- It is a third emitter on a seam that already carries two
  (`render_ai_prompt`, `render_agent_instructions`) — no new
  architecture, and the same "the tool prompts, the LLM acts" contract
  ADR 008 drew.
- **It does not gate and it does not score.** A hostile-audit prompt is
  a QA aid; its findings return to the falsifier-and-fix loop, never to
  the estimate, range, or grade — the same discipline ADR 003 holds for
  design-review candidates.
- It points at this tool's own promises today, and at any codebase that
  states invariants tomorrow; the mechanism does not care whose promises
  they are.
- **Deferred, distant future (the second play).** A *deterministic*
  adversarial-properties detection dimension — one that checks a
  **target** repository for the hardening classes this agent enforces on
  itself (a write that follows a symlinked route, an empty tool run read
  as clean, a caller argument reaching a filesystem or shell sink
  unvalidated) — is a different thing: deterministic detection, not a
  prompt, and it brushes the `secure-code-agent` boundary. It is
  recorded in the [roadmap](roadmap.md) and earns its own ADR when it
  comes up, not this one.
