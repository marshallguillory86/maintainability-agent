# Why this exists

Moved out of the README, which is a front door and had become an essay.
The argument is unchanged; only its address is.

The ratio of code-written to code-reviewed has collapsed. Unmaintainable code
that used to accumulate over years can now accumulate in an afternoon:
duplicated helpers, oversized files, speculative abstractions — the same slop
hand-written codebases always accrued, now at machine speed.

The same speed is the way out. An agent pointed at specific, deterministic
findings can fix them at the rate they appear. The loop this tool closes:

1. **Measure** pressure points deterministically, with no LLM involved.
2. **Score** with one uniform standard, so the verdict is not a debate.
3. **Emit** a prompt scoped to *those findings only*, with explicit
   instructions not to refactor beyond them.
4. **Hand it to the agent.** Review a scoped diff instead of a speculative
   rewrite.

Step 3 is the product; steps 1 and 2 are in service of it. Every other tool in
this space stops at "here's a list of findings."

**Who does the checking matters as much as what it checks.** An author is never
the independent check on their own work, so a platform that generates code and
grades it is producing a self-assessment — a property of the arrangement, not a
criticism of any one of them. This writes nothing and runs no model, which is
what lets its verdict be evidence ([the principle](philosophy.md#principles)).
Since 2.1.0 the work order is also **checked**: `--conformance` compares the
returned diff against the paths the report named, `--fail-on-regression`
ratchets the dimension scores, and `--attestation-output` composes them into one
record ([how that hole was closed](roadmap.md#the-remediation-hole-closed-in-210-through-230)).
The limit, stated in the same breath: those checks read the diff's **shape**,
never its correctness — whether the change works is not a claim this tool makes.

One pre-registered experiment has tested the bounded prompt.
Generic prompting made 2 of 6 repositories worse; bounded prompting made 1 of 6 worse and improved 5 of 6, under this tool's own finding count.
The *registered* hypothesis was narrower diffs, which did not hold, so the
registered verdict stands at **INCONCLUSIVE**. Method, limits and raw data:
[docs/studies.md](studies.md#does-the-bounded-prompt-work-controlled-experiment-pre-registered).

### Who it's for

- Teams running AI agents in the dev loop, tired of unbounded cleanup PRs, who
  want a CI gate that actively constrains follow-up scope.
- Repos that want a maintainability gate without a SaaS analyzer or shipping
  code to a third party.
- Solo devs who want a single deterministic audit to pin in a Makefile,
  pre-commit, or local CI script.
