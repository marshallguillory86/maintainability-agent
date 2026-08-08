# Maintainability Audit Standard

This project uses ISO/IEC 25010 maintainability as the category model.

## Definition

Maintainability is the degree to which a system can be effectively and efficiently modified to improve it, correct it, or adapt it to changes in environment and requirements.

## Categories

| Category | Audit Question |
|---|---|
| Modularity | Can changes stay local, or does one change ripple through unrelated areas? |
| Reusability | Are useful components reusable without dragging along accidental coupling? |
| Analyzability | Can a developer quickly understand impact, diagnose issues, and find what must change? |
| Modifiability | Can changes be made without introducing defects or degrading quality? |
| Testability | Can meaningful behavior be verified with local, repeatable tests? |

## Scoring

The CLI emits an ISO/IEC 25010-inspired score from 0 to 5 for each category plus an overall letter grade. This score is a deterministic triage signal, not a replacement for human review.

### How the scale was calibrated (0.5.0)

Scores are **rates measured against real code**, not counts.

The previous model counted findings absolutely: 20 oversized files cost the same in a 50-file project as in a 3,000-file one. Measured against a corpus of mature open-source repositories, it scored **Django, pytest, black, tornado, click, httpx, attrs, lodash, svelte, axios and fastapi all at 0.0 / F**, while a 53-file toy repo scored 4.6 / A. It was measuring repo size. Every real codebase saturated the floor, so the scale carried no information and could not tell a mediocre codebase from a catastrophic one.

Three properties now hold, and are pinned by `tests/test_scoring_calibration.py`:

1. **Size independence.** Every pressure is a finding count divided by the population it was drawn from. The same proportion of trouble scores the same at any repo size.
2. **Per-dimension normalization.** Raw pressures live on wildly different scales — measured across the corpus, duplication runs ~15x file-size pressure and ~93x declaration pressure. Summing them raw would score duplication and nothing else. Each dimension is divided by its own corpus median, so a reported `3.1x` means "three times the duplication that real, well-maintained code lives with."
3. **No saturation.** The curve is hyperbolic, so two bad repos remain distinguishable instead of both reading 0.0.

The corpus median lands at **4.0 (B)**: a well-run real codebase earns a B, and every grade above it must be paid for.

### The reference corpus

Calibration is reproducible, not a snapshot someone took once. The corpus is defined in [`tools/calibration/corpus.json`](../tools/calibration/corpus.json) — 14 mature open-source repositories **pinned to exact commits**, spanning 52 to 4,034 files across Python and JavaScript/TypeScript:

> requests · flask · click · attrs · httpx · pytest · black · tornado · django · fastapi · express · axios · lodash · svelte

They were selected for long maintenance history under many contributors, wide readership and dependency, mixed size and ecosystem, and a bulk authored before LLM coding assistants were in common use — making this a human-written baseline.

To re-measure and check for drift:

```bash
python3 tools/calibration/measure.py            # clone at pinned commits, measure, report drift
python3 tools/calibration/measure.py --check    # exit 1 if stored constants are stale
```

The measurements themselves are checked in at `tools/calibration/measurements.json`, and `tests/test_calibration_corpus.py` re-derives every constant from them **offline** — no clone, no network. A hand-edited constant, or a re-measurement that wasn't written back, fails the suite. The constants are therefore auditable without taking anyone's word for them, which is the same standard the scores themselves are held to.

Size matters to the selection: a reference drawn only from small libraries would bake in exactly the size bias that made the previous model grade Django an F. Including django, fastapi and svelte moved the file-size reference from 0.1233 to 0.0779 — a 37% shift that a small-repo-only corpus would have hidden.

### Why A+ is hard

An average lets a repo hide one bad dimension behind four good ones. The top two grades are therefore **gated as well as banded** — a score in the A+ band is withheld unless *every* dimension is clean, and demotion cascades (a repo denied A+ must still satisfy A's ceilings to receive an A). A single hard-gate failure disqualifies both.

When the score reports `2.5x`, that number is the unit the remediation prompt speaks in: it names the worst dimension and tells the agent to start there, because a letter grade is not actionable.

### Limits

These are structural proxies — file size, declaration size, approximate complexity, repetition. They do not measure naming quality, comment accuracy, architectural coherence, or whether a reader can build a correct mental model. Passing on structure is necessary, not sufficient. The corpus is also finite: recalibrate whenever the default thresholds change.

| Score | Meaning |
|---:|---|
| 5 | Strong. Change is localized, tested, and easy to reason about. |
| 4 | Good. Minor issues exist but do not materially slow normal changes. |
| 3 | Usable. Change is possible, but developers need caution or repo-specific knowledge. |
| 2 | Fragile. Changes are slow, risky, or require broad context. |
| 1 | Poor. Frequent regressions, unclear ownership, weak tests, or heavy coupling. |
| 0 | Unmaintainable in this area. Safe change is not realistic without remediation. |

Current scoring inputs:

- file warnings and failures
- function/class size and approximate complexity warnings or failures
- duplicate block count
- configured risk-pattern findings
- hard-gate failures

Grades:

| Grade | Overall Score |
|---|---:|
| A+ | 4.8 to 5.0 |
| A | 4.5 to 4.7 |
| B | 4.0 to 4.4 |
| C | 3.0 to 3.9 |
| D | 2.0 to 2.9 |
| F | below 2.0 |

## CI Role

CI should not pretend to fully grade maintainability by itself.

CI should:

- detect obvious hotspots
- enforce hard gates
- produce a report for review
- stop new severe maintainability regressions

Human review should:

- judge architecture fit
- judge whether complexity is accidental or inherent
- judge whether tests cover meaningful behavior
- decide remediation priority

## References

- ISO/IEC 25010 maintainability: https://iso25000.com/index.php/en/iso-25000standards/iso-25010/57-maintainability
- SonarQube metrics: https://docs.sonarsource.com/sonarqube/latest/user-guide/code-metrics/metrics-definition/
- Code Climate maintainability: https://docs.codeclimate.com/docs/maintainability
- Code Climate default thresholds: https://docs.codeclimate.com/docs/default-analysis-configuration
- ESLint complexity rule: https://eslint.org/docs/latest/rules/complexity
- Radon metrics: https://radon.readthedocs.io/en/latest/intro.html
- Semgrep docs: https://semgrep.dev/docs/
