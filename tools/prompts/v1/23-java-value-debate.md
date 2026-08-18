# Briefing — whole-product value for a Java engineer (debate, not a slice)

You are Claude or Codex. Marshall, Grok, you, and the other model
will decide together. Not an implementation order. Do not open a
branch. Do not edit the repo. Do not invent product intent past the
cited docs.

This debate is **the entire feature set**, not whether
java_declaration_ranges is a cute lizard. Java is the customer
lens: would a typical Java engineer (lizard/Checkstyle/Sonar
already in CI, maybe agents in the IDE) adopt *this product*?

Grok's revised position is below. Agree, refute, tighten. Cite
files. End with I would decide / I would not decide. Marshall
decides.

## Governing docs

- docs/product-intent.md — product is the bounded work order /
  remediation prompt. If the prompt were removed, the rest is a
  worse version of tools that already ship. Customers: teams
  running agents in the dev loop; repos that want a gate without
  SaaS; not "replace Sonar."
- docs/adr-006-analyzer-evidence.md — FOSS analyzers produce
  evidence; built-ins labelled fallback; full concept set or
  unmeasured; spread is information.
- docs/adr-008-translation-and-decision.md — metric vs verdict
  emitters.
- docs/adr-007, adr-009, adr-011, adr-003, adr-004 — work-order
  bands, history/recurrence/identity, three skins, TS semantics,
  economic scenario.
- docs/architecture.md — Java locator is zero-install fallback;
  do not clone it; do not feed lizard into declarations_scanned
  without the full concept set.
- docs/defect-register-chat-surface.md — D1/D13 closed on
  v0.8.1; D2–D12, D14–D17 open (chat is the stated primary
  surface and still lags).
- docs/analyzer-pool.md — 14 adapters; none are Checkstyle,
  PMD, or SpotBugs.

## Grok's revised opinion

### Does widening the lens change "meh"?

**Partly.** Grok over-indexed on the walker vs lizard. That is
our bootstrap, not the product.

**Does not change:** this tool will not win "better Java static
analysis." No JVM-native adapters. Score often still fallback
after lizard runs (all-or-nothing declaration concept set).
Work-order locations still from the walker. Average engineer
comparing to Sonar/lizard: meh on measurement.

**Does change:** product-intent's actual buyer is not that
average analyzer shop. It is teams whose agents write faster
than humans review. For *that* person who happens to write
Java, the feature set lizard/Sonar are not:

- Bounded remediation prompt (the product)
- Risk × effort work order (quick win vs major project)
- Recurrence / told-you-fixed-it-came-back (ADR 009)
- Fail-on-new + stable identity (rename/digest)
- One rubric on a mixed tree (Java + Gradle + Python + YAML)
- Evidence withholding (P7/P8) instead of a fake 5.0
- Offline, no SaaS, no upload of the tree
- Optional $ scenario; HTML exec strip; S/H/M/L as output
  not score

So: **meh as a Java linter add-on. Maybe yes as an agent
governor** — if the score does not contradict lizard and the
chat/IDE path works. Today the second half is bruised (fallback
headline; D2–D12 chat gaps; IntelliJ is where they live).

### Complementary tools (whole pool, not just the walker)

Same split as before, now for the whole set:

- Locators (Java walker, Python AST, JS braces) vs metric
  emitters (lizard, radon, …): complementary if composed.
- Different concerns (jscpd, vulture, ruff, git churn):
  complementary to lizard.
- Same concept, independent conventions (radon vs lizard CCN):
  complementary as corroboration + spread.
- Keyword-regex CCN vs lizard CCN: not complementary.
- Verdict emitters (Checkstyle/PMD/eslint) vs score population:
  complementary as findings, never as denominators.
- Built-in always-on + pool: complementary only where the
  built-in stands down on a dimension the pool fully measured.

D15 is the composition rule. It is not implemented.

### Architecture moves (still not a mandate)

A. Per-concept analyzer-primary: lizard CCN + lines count even
   when cognitive is Unknown (widen the range). Do not dump the
   whole dimension back to the regex.

B. Work-order units from metric emitters when they ran.

C. D15 + JVM verdict adapters (Checkstyle/PMD), not a second
   ranger.

D. Chat/MCP first (open defects). That is how Java engineers
   in IDEs will meet the tool.

E. Do not market the walker, become Sonar, or invent a
   Java-only rubric.

The product bet is D plus A so the headline does not insult
lizard. B and C make complementarity real.

## What we need from you

1. Locator vs measurement: still the right split for the
   *whole* tool, or only for Java?
2. Did Grok misread why Java+lizard still prints fallback?
3. Work-order from lizard units vs ADR 009 identity — feasible?
4. "Meh as linter / maybe as agent governor" — fair?
5. A–E: accept, reject, rewrite. Include whether the *average*
   Java engineer is even the customer product-intent named.
6. Missing: Maven/Gradle, overloads, inner classes, test vs
   main, monorepo with Android, etc.

End with:

    Agree with Grok on: …
    Disagree / would change: …
    I would decide: …
    I would not decide: …

Marshall decides. You do not.
