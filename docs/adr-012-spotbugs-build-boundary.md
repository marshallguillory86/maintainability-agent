# ADR 012 — SpotBugs and the build boundary

**Status: Proposed.** Drafted 2026-08-19 for decision 9's third JVM
slice (item 8 on the improvement list). Nothing here ships until the
operator accepts a resolution.

## The problem

SpotBugs — the third of the Java "big three" beside PMD and
Checkstyle — analyzes compiled bytecode, not source. Every value it
adds (null-dereference paths, resource leaks, bad equals/hashCode
contracts) requires `.class` files that only a build produces.

This agent's boundary is settled and load-bearing: it never runs a
repository's build, never accepts command strings, and never spawns
anything but a catalogued analyzer over the tree as it stands (P1;
the MCP security contract). A build is arbitrary code execution by
definition — `pom.xml` and `build.gradle` run plugins. Crossing that
line for one analyzer would trade the product's strongest safety
claim for one tool's evidence.

## Options considered

1. **Run the build when asked.** Rejected outright: it converts a
   read-only-over-source auditor into an arbitrary-code runner, and
   no elicited consent makes that class of risk proportionate to a
   bug-pattern report.
2. **Skip SpotBugs entirely.** Honest but wasteful: many Java trees
   under audit — CI workspaces, developer checkouts after a build —
   already contain `target/classes` or `build/classes`. Refusing to
   read evidence that already exists is absence-as-a-choice.
3. **Analyze bytecode that already exists; never create it.**
   SpotBugs joins the pool with a `has_targets` gate on compiled
   output (`target/classes`, `build/classes`, or configured class
   dirs). Present bytecode → SpotBugs runs over it. Absent bytecode →
   a `not-applicable` coverage row whose detail says a build would
   widen coverage, and an environment work-order entry giving the
   user the build-then-rerun instruction — the same "the user acts,
   the agent reports" contract as a missing binary (agents never
   install; agents never build).

## Proposed resolution

Option 3. The boundary sentence stays absolute — *the agent never
builds* — and the work order carries the remedy, exactly as it does
for missing tools. One honesty condition attaches: a SpotBugs run
must record **staleness evidence** (bytecode may not match current
source). The coverage row carries the newest source mtime vs the
newest class-file mtime; when source is newer than bytecode, the row
says so and the findings are labeled as measured against stale
compilation. Two reports with different staleness are not comparable
silently (P8).

## Consequences

- The JVM track completes with three adapters of two shapes:
  source-read (PMD, Checkstyle) and artifact-read (SpotBugs). D15's
  composition test covers both shapes.
- The environment work order gains its first non-install remedy
  (build instruction), which generalizes to future artifact-read
  tools (JaCoCo report reading was already declined — decision 10 —
  but the same gate pattern would apply if that ever reopens).
- A CI image that builds before auditing gets full SpotBugs evidence
  with zero configuration.
