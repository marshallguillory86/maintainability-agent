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

### Cognitive complexity (0.6.0)

The cyclomatic figure is a keyword tally, and it is blind to the thing that actually costs a reader. These score identically under it:

```python
def flat(a,b,c,d,e):          def nested(a,b,c,d,e):
    if a: return 1                if a:
    if b: return 2                    if b:
    if c: return 3                        if c:
    if d: return 4                            if d:
    if e: return 5                                if e:
    return 0                                          return 5
```

Both are cyclomatic 6. Guard clauses are read one at a time; five levels of nesting must be held in the head at once. Nesting is the strongest driver of how hard code is to read, and it was invisible.

Each flow break is now charged **plus the depth it sits at**, so nesting compounds — the pair above scores 5 and 15. `else` costs one flat point rather than a nested one, because it resolves a branch already being tracked; `elif` chains likewise do not compound; and a run of boolean operators counts once, since `a and b and c` is a single idea to read.

Python is measured exactly from the AST. C-family sources have no parser here, so nesting is inferred from brace depth over the masked copy — approximate, and it under-reports on brace-free single-statement bodies, which is the safe direction.

Thresholds (`max_cognitive_complexity` 25, `warn_cognitive_complexity` 15) were fitted against **21,300 declarations** in the reference corpus, whose distribution is p50 = 1, p90 = 9, p95 = 17, p99 = 49. Warning at 15 flags 5.5% of declarations and failing at 25 flags 2.7% — comparable hit rates to the existing file thresholds. Both figures are reported side by side rather than merged: a function can be low in one and high in the other, and that difference is the point.

### Signals reported but not yet scored

**Near-duplicate declarations** (0.6.0) detect a helper written twice under two names — the failure mode most often attributed to AI-written code, where an agent that cannot see your existing helper writes a second one. Exact text matching cannot catch it, so declaration bodies are reduced to a token sequence with identifiers anonymized by order of first appearance; renamed copies produce identical fingerprints.

Measured across the reference corpus (production code only, cross-file pairs, as a share of eligible declarations):

| Cohort | n | Median | Max |
|---|---|---|---|
| Mature human-written OSS | 12 | **0.20%** | 2.15% |
| AI-written applications | 6 | **1.49%** | 12.05% |

Three of the AI-written repos exceed every repository in the OSS corpus. This is the first signal measured here that separates the two populations — on file size, declaration size and complexity they are statistically indistinguishable.

**Read it with the confounds in view.** The OSS corpus is libraries; the AI cohort is applications. Libraries are designed for reuse and have had years of review pressure to remove duplication, while applications accrete. Both samples are small. The direction is consistent with the mechanism and with published findings on AI-assisted commit histories, but this is evidence, not proof.

Two false-positive classes were removed by fitting the near-duplicate eligibility thresholds against the corpus rather than guessing them: bodies too short for similarity to mean anything, and thin delegations whose shape is dictated by the API surface (requests' `put`/`patch`, flask's `template_filter`/`template_test`). Test files are excluded — in mature projects nearly all near-duplicates are deliberately parallel test variants, which are not the defect being measured.

**Unreferenced private declarations** (0.6.0) find debris — a helper written for an approach abandoned two prompts later. Only declarations the language marks internal are candidates (a leading underscore in Python, no `export` in JS/TS), because privacy is the author's own claim that no external caller exists, which is what makes "no references here" sufficient evidence. Public functions, decorated declarations, dunder methods and test files are left alone.

Two false-positive classes surfaced on first contact with the corpus and are now pinned by tests. Counting identifiers over the *masked* copy blanked f-string interpolations, which are live code — flask's `_get_werkzeug_version` is called from inside one and was reported dead. And an object-literal method (`beforeBreadcrumb(crumb) { … }` in a Sentry config) binds no name and is invoked by whoever receives the object. Fixing both dropped one repo's findings from 15 to 0.

Measured rates barely separate the cohorts — mature OSS median 0.0% (max 0.55%), AI-written median 0.14% (max 1.53%). It earns a place in the report as hygiene, **not** as evidence for anything about AI-written code. Note also that a private *method* on a public class can be reached by a downstream subclass, so those findings deserve a look rather than a reflex deletion.

Neither is a score dimension yet. Most repositories sit at zero, so a median-based reference would be unstable — dividing by ~0.002 turns a rounding difference into a large multiple. Signals earn a place in the score by holding up across more repositories, not by being new.


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
