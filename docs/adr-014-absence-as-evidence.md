# ADR 014 — Adversarial-properties detection: the absence-as-evidence half

- Status: **Accepted** (2026-09-10) — the *scope* decision. Nothing is
  built. Implementation is gated on a pre-registered precision bar, the
  way [ADR 003](adr-003-deterministic-semantic-policy.md) gated its own.
  Progress belongs in the [decision register](decisions.md), not here.
- Scope: what a detection dimension may claim, where it stops against
  [`secure-code-agent`](adr-007-pillars-and-practice.md), and whether any
  of it can gate or score.
- Related: [ADR 013](adr-013-hostile-audit-prompt.md) (the emitter half of
  the same play), [ADR 003](adr-003-deterministic-semantic-policy.md) (a
  non-gating finding class and a frozen acceptance bar),
  [ADR 007](adr-007-pillars-and-practice.md) (security is delegated),
  [ADR 008](adr-008-translation-and-decision.md) (the LLM boundary),
  [product intent](product-intent.md) (P3 and P7).

## Context

[ADR 013](adr-013-hostile-audit-prompt.md) shipped the *emitter*: this
tool can seed a hostile audit of itself from one run. That ADR's own
closing line defers the other half — a deterministic dimension that
audits a **target** repository for the hardening classes this project
enforces on itself — to "a future release and its own ADR." The
[roadmap](roadmap.md) carries the same deferral and names the reason it
could not simply be built: *it brushes the `secure-code-agent`
boundary, so it needs an explicit scope decision.*

That boundary is real and already decided in the other direction.
[ADR 007](adr-007-pillars-and-practice.md) delegates the security pillar
outright: MA does not measure exploitability, it reads what
`secure-code-agent` measured. A dimension that shipped symlink-escape
and shell-injection detection would be MA re-deciding that question by
building the thing it just delegated.

But the four classes the roadmap names are not one kind of finding.
They are two, and the seam runs straight between them:

| Class named on the roadmap | What it actually asks |
|---|---|
| a write that follows a symlinked route | is this exploitable? |
| a caller argument reaching a filesystem or shell sink unvalidated | is this exploitable? |
| an empty tool run read as clean | does this code's evidence handling lie? |
| absence read as a pass | does this code's evidence handling lie? |

The first two are exploitability. The second two are **evidence
integrity**, and they are not security findings at all. Code that
converts "we did not measure" into "it is fine" is wrong on a machine
with no attacker anywhere near it. It is wrong the way a report that
scores an unexamined repository 5.0 is wrong.

That is this project's own stated failure mode, in someone else's code.
[Product intent](product-intent.md) P3 is *"withholding evidence cannot
improve the reported grade"* and P7 is *"a score is issued only where
enough was examined to support it, and never as a consequence of not
looking."* Both promises exist because this tool violated them and an
audit caught it. The register carries the instances: a withheld band
that improved a dimension, an empty analyzer run priced as clean, a
production count whose absence resurrected as a measured value and moved
the reported overall from 4.3 to 4.6.

So the question this ADR settles is not "should MA detect adversarial
properties." It is **which half**, and the answer is available from
first principles rather than from preference: MA takes the half that is
its own subject matter and leaves the half it already delegated.

## Options

**A. Build all four classes.** One dimension covering symlink escape,
unvalidated sinks, empty-run-as-clean and absence-as-pass.

*Consequence:* MA ships exploitability detection four months after
deciding it would not, and two tools disagree about the same file with
no rule for which wins. `secure-code-agent` is the delegate for a
pillar MA reports; a delegate whose findings MA also computes is not a
delegate. Rejected.

**B. Build nothing; keep the deferral.** The status quo.

*Consequence:* honest, and it leaves on the table the one detection MA
is better placed to make than any security scanner, because it is the
detection MA's own promises are written in terms of. The hostile-audit
loop keeps producing this finding class by hand, one session at a time,
with no artifact — which is exactly the gap ADR 013 was written to
close on the other side.

**C. Build the evidence-integrity half only, non-gating, behind a frozen
precision bar.** Detect code that reads absence as a pass. Leave every
exploitability class to `secure-code-agent`. Emit as design-review
candidates that never touch a score, on ADR 003's terms.

*Consequence:* the boundary is stated as a rule rather than a list, so
the next candidate class is adjudicated without reopening this ADR. The
cost is that some findings sit near the line — an unchecked exit code is
evidence integrity when the result is read as clean and a security
finding when the tool was a scanner — and those will need naming
individually.

**D. Emit it into the hostile-audit prompt instead of as findings.**
Extend ADR 013's brief rather than adding a dimension.

*Consequence:* cheap, and wrong for this class. These patterns are
AST-derivable and deterministic. Routing a decidable question through an
LLM gives up reproducibility (P1) to answer something that did not need
a model, and the prompt seam is for the reasoning the core *cannot* do.

## Decision

**Option C.** MA gains a detection dimension for one class of defect:
**code that treats an absent, empty or failed measurement as a passing
result.** It does not detect exploitability, and every class in that
category stays with `secure-code-agent`.

The boundary is a rule, not a list. A candidate belongs to MA when it
would still be a defect on a machine no attacker can reach. It belongs
to the delegate when its harm requires someone hostile. An unchecked
`subprocess` exit code is MA's when the empty output is then read as a
clean result; it is the delegate's when the argument that built the
command came from outside. Where a finding is genuinely both, MA yields
— [ADR 007](adr-007-pillars-and-practice.md) already gave that pillar
away, and two tools reporting one finding twice is worse than one tool
reporting it once.

**Nothing is gated and nothing is scored.** These emit as design-review
candidates on [ADR 003](adr-003-deterministic-semantic-policy.md)'s
terms: the score, the grade and the band matrix are untouched. The
precision achievable here is unknown until measured, and a finding class
that can fail a build before its precision is known is how a tool
teaches people to ignore it.

**Implementation is gated on a frozen acceptance bar,** pre-registered
before any result exists, in the manner of
[semantic-prototype.md](semantic-prototype.md): a labeled corpus, a
stated precision floor, and the rule that the corpus and the bar may not
be changed in the change that reports a result against them. Python
first, because its AST is the one this tool already parses to the depth
this needs.

## Consequences

**Easier.** The hostile-audit loop's most repeated finding class gets an
artifact, so it stops depending on whoever wrote the prompt that day.
A target repository gets told the thing MA is actually expert in —
P3 and P7 are the two promises this project has broken most often, and
that experience is what the dimension encodes.

**Harder.** Every new candidate class now needs the boundary rule
applied before it is written, and some will be arguable. That is the
cost of having a rule instead of a list, and it is cheaper than the
alternative, which is rediscovering the `secure-code-agent` overlap once
per class.

**Migration.** None. Nothing ships until the bar is met, and a repository
that never enables the dimension sees no change. The delegated security
pillar is unaffected: this adds no reading to it and takes none away.

**What would reverse this.** A measured precision below the frozen bar.
The dimension is then not shipped, and this ADR is superseded by one
recording that the class is not deterministically decidable at useful
precision — which is a real possible outcome and is why the bar is set
before the result exists.

## Invariants

1. No finding from this dimension can fail a gate, change
   `maintainability_estimate`, alter a category, aspect or dimension
   score, or move a grade.
2. Identical source, configuration and analyzer versions produce
   byte-identical findings from this dimension (P1).
3. No finding from this dimension asserts exploitability, reachability
   from untrusted input, or any security severity.
4. Unsupported or unparseable source is reported as unknown coverage for
   this dimension, never as zero findings — the dimension may not commit
   in its own output the defect it detects.
5. Every finding names the source construct that produced it, at a
   location a reader can open.
6. Removing the dimension's configuration cannot create a finding.
7. No result from this dimension reaches the score through any
   repository-specific path.

## References

- [ADR 013](adr-013-hostile-audit-prompt.md) — the emitter half
- [ADR 003](adr-003-deterministic-semantic-policy.md) — non-gating findings, frozen bar
- [ADR 007](adr-007-pillars-and-practice.md) — security is delegated
- [semantic-prototype.md](semantic-prototype.md) — the pre-registration pattern
- [product intent](product-intent.md) — P1, P3, P7
