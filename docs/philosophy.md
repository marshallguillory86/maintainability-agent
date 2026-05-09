# Philosophy

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

AI-written code often fails in recognizable ways:

- plausible but misplaced abstractions
- broad rewrites for narrow bugs
- duplicated helpers with tiny differences
- stale comments that sound confident
- tests that assert implementation details instead of behavior
- architecture drift across modules

Maintainability Agent catches signals of those failures and creates prompts that steer agents toward disciplined, small, reviewable fixes.
