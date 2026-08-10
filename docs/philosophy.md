# Philosophy

> Governed by [product intent](product-intent.md), which is authoritative on what this product is for and what it may claim. This page is the reasoning behind it, not a second definition of it.

Maintainability Agent is not an AI reviewer and it does not send code to an LLM.

It is a deterministic audit and prompt-generation layer for teams using AI-assisted development.

## Principles

- Deterministic first, AI optional.
- Human stays in control.
- CI produces evidence, not vibes.
- The remediation prompt is bounded by findings.
- The tool should prevent giant speculative cleanup PRs.
- Existing architecture matters.
- Passing a metric is not the same as maintainable code.

## Why AI-Specific?

**Volume, not pathology.**

An earlier version of this page claimed AI-written code fails in recognizably different ways. When this project finally tested its best candidate for such a signal against a properly matched control, the claim did not survive ([docs/standard.md](standard.md#does-this-detect-ai-written-code)). And it never needed to be true: anyone who has spent decades in software has seen thousands of lines of unmaintainable code written entirely by hand. Slop is not a new failure mode. It is the oldest one.

What AI changes is the *rate*. Agents produce code faster than humans can read it, so the ratio of code-written to code-reviewed collapses — and unmaintainable code that used to accumulate over years can now accumulate in an afternoon. That is the problem this tool exists for, and it needs no claim about AI writing *worse* code, only the observable fact that it writes *more*.

**The same volume is the way out.** If agents can produce slop at scale, agents pointed at deterministic findings can fix it at scale — that is the loop this tool closes:

1. The audit finds the specific pressure points, deterministically, with no LLM in the loop.
2. The score applies one uniform standard, so "better" and "worse" are not arguments.
3. The remediation prompt hands an agent a bounded work order — *these* findings, *this* scope — so cleanup happens at machine speed without becoming a machine-speed rewrite.

The failure modes commonly attributed to AI — misplaced abstractions, broad rewrites for narrow bugs, duplicated helpers, stale comments, implementation-detail tests — are worth detecting **regardless of who wrote them**, and detectors for them are built or planned on exactly that basis. Whether AI produces them at a different rate than humans is an empirical question; each claim about it gets tested against a matched control before it is made, because this project has retracted one such claim already and intends never to need a second retraction.
