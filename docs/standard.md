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
2. **Per-dimension normalization.** Raw pressures live on wildly different scales — measured across the corpus, duplication runs ~65x file-size pressure and ~62x declaration pressure. Summing them raw would score duplication and nothing else. Each dimension is divided by its own corpus median, so a reported `3.1x` means "three times the duplication that real, well-maintained code lives with."
3. **No saturation.** The curve is hyperbolic, so two bad repos remain distinguishable instead of both reading 0.0.

The corpus median lands at **4.0 (B)**: a well-run real codebase earns a B, and every grade above it must be paid for.

### The reference corpus

Calibration is reproducible, not a snapshot someone took once. The corpus is defined in [`tools/calibration/corpus.json`](../tools/calibration/corpus.json) — 40 mature open-source repositories **pinned to exact commits**, spanning 32 to 18,789 source files and 463,581 declarations across Python, TypeScript and JavaScript:

> angular · ansible · ant-design · anime · axios · Chart.js · code-server · django · echarts · excalidraw · express · fastapi · flask · freeCodeCamp · github-readme-stats · hackingtool · hoppscotch · jquery · keras · localstack · lodash · manim · material-ui · mermaid · models · n8n · nest · playwright · reveal.js · scrapy · strapi · svelte · tabby · tailwindcss · transformers · uBlock · vite · webpack · youtube-dl · yt-dlp

**The list is produced by a query, not by preference.** The first corpus was fourteen repositories chosen because the author knew them — selection bias sitting directly underneath a scale used to grade other people's code. [`tools/calibration/select_corpus.py`](../tools/calibration/select_corpus.py) now issues a GitHub search anyone can re-run:

```text
language:{python,typescript,javascript} stars:>3000 created:<2021-01-01 pushed:>2026-01-01
```

Each clause does real work. **`stars:>3000`** means "well maintained" is a claim others have tested rather than one this project asserts. **`pushed:>2026-01-01`** keeps the corpus describing code that is still maintained. **`created:<2021-01-01`** is the load-bearing one: this corpus is the *human-written* baseline against which AI-assisted code is compared, and today's most-starred repositories include projects begun well into the LLM era. Letting those in would answer the question before measuring it.

Star-sorted search returns a lot of things that are not programs. Two filters remove them: a conservative name filter for curated lists and courses, and — the real one — [`verify_corpus.py`](../tools/calibration/verify_corpus.py), which clones each candidate and keeps it only if it holds at least 20 source files and 100 declarations. Seven candidates were rejected on contents, including `PayloadsAllTheThings` (33 declarations), `airbnb/javascript` (14) and `30-Days-Of-Python` (22); the rejections are recorded in `corpus.json` rather than silently dropped.

One exclusion is worth naming because it is the kind of thing that quietly corrupts a reference. `33-js-concepts` cleared verification — an `index.js` plus thirty concept-demo test files is enough declarations to look like a codebase — and landed as the corpus outlier on duplication (38.8x the median) and file size (3x the next repo), because parallel teaching examples are *supposed* to repeat. It is excluded as a teaching repo, on what it contains rather than on how it scored. The distinction matters: filtering a corpus by its own measurements manufactures whatever reference the filter was aimed at. For the record, removing it barely moved anything — `c` went 3.5724 → 3.5466 — which is what a median is for.

To re-measure and check for drift:

```bash
python3 tools/calibration/measure.py            # clone at pinned commits, measure, report drift
python3 tools/calibration/measure.py --check    # exit 1 if stored constants are stale
```

The measurements themselves are checked in at `tools/calibration/measurements.json`, and `tests/test_calibration_corpus.py` re-derives every constant from them **offline** — no clone, no network. A hand-edited constant, or a re-measurement that wasn't written back, fails the suite. The constants are therefore auditable without taking anyone's word for them, which is the same standard the scores themselves are held to.

Size matters to the selection: a reference drawn only from small libraries would bake in exactly the size bias that made the previous model grade Django an F. The corpus spans a 587x range in file count for that reason.

**Moving from the hand-picked 14 to the queried 40 changed the scale, and it is worth being explicit about which way.** The references moved as follows:

|dimension|14 hand-picked|40 queried|effect on scores|
|---|---|---|---|
|file_size|0.0779|0.0576|stricter|
|declarations|0.0243|0.0599|more lenient|
|duplication|1.4659|3.7350|**much more lenient**|
|risk|0.0546|0.0726|more lenient|

Duplication is the one to look at: the reference is now 2.5x higher, so a repository that used to score `5.0x` on duplication now scores `2.0x` for identical code. That is not a bug, but it is a judgment. The hand-picked corpus was almost entirely libraries — `requests`, `flask`, `click`, `attrs`, `httpx` — and libraries are designed for reuse and have had years of review pressure to remove repetition. Sorting by stars returns applications and tools as well (n8n, excalidraw, playwright, transformers), and those carry substantially more duplication. The queried corpus therefore describes *widely-used code* rather than *well-factored libraries*, which is the more honest reference for a tool that grades arbitrary repositories, but it does mean the duplication bar is set by a population that includes application code.

The gates dimension is deliberately **not** corpus-derived. Hard gates are discrete policy breaches a repository opts into, not a rate drawn from a population, and once gating became opt-in the corpus median went to zero — which would have made the dimension silently ignore real failures. It is fixed at 0.05, so one gate failure reads as `1.0x`.

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

Thresholds (`max_cognitive_complexity` 25, `warn_cognitive_complexity` 15) were fitted against **21,300 declarations** in the 14-repo corpus these were calibrated on at 0.6.0, whose distribution is p50 = 1, p90 = 9, p95 = 17, p99 = 49. They have not yet been re-fitted against the 40-repo corpus and its 463,581 declarations; the scoring references have. Warning at 15 flags 5.5% of declarations and failing at 25 flags 2.7% — comparable hit rates to the existing file thresholds. Both figures are reported side by side rather than merged: a function can be low in one and high in the other, and that difference is the point.

### Signals reported but not yet scored

**Near-duplicate declarations** (0.6.0) detect a helper written twice under two names — the failure mode most often attributed to AI-written code, where an agent that cannot see your existing helper writes a second one. Exact text matching cannot catch it, so declaration bodies are reduced to a token sequence with identifiers anonymized by order of first appearance; renamed copies produce identical fingerprints.

It is a useful finding on its own terms. It is **not** evidence about who wrote the code — see below.

Two false-positive classes were removed by fitting the near-duplicate eligibility thresholds against the corpus rather than guessing them: bodies too short for similarity to mean anything, and thin delegations whose shape is dictated by the API surface (requests' `put`/`patch`, flask's `template_filter`/`template_test`). Test files are excluded — in mature projects nearly all near-duplicates are deliberately parallel test variants, which are not the defect being measured.

**Unreferenced private declarations** (0.6.0) find debris — a helper written for an approach abandoned two prompts later. Only declarations the language marks internal are candidates (a leading underscore in Python, no `export` in JS/TS), because privacy is the author's own claim that no external caller exists, which is what makes "no references here" sufficient evidence. Public functions, decorated declarations, dunder methods and test files are left alone.

Two false-positive classes surfaced on first contact with the corpus and are now pinned by tests. Counting identifiers over the *masked* copy blanked f-string interpolations, which are live code — flask's `_get_werkzeug_version` is called from inside one and was reported dead. And an object-literal method (`beforeBreadcrumb(crumb) { … }` in a Sentry config) binds no name and is invoked by whoever receives the object. Fixing both dropped one repo's findings from 15 to 0.

It earns a place in the report as hygiene, **not** as evidence for anything about AI-written code. Note also that a private *method* on a public class can be reached by a downstream subclass, so those findings deserve a look rather than a reflex deletion.

**Competing libraries for one concern** (0.6.0) flag a codebase where two packages do one job — three HTTP clients means three error shapes and three retry stories, and no single mental model covers the code. This is the one detector that **needs a curated list**, and that cost is real: there is no structural way to know that `moment` and `date-fns` compete while `react` and `react-dom` do not. The shipped list is deliberately small, restricted to concerns whose alternatives are well known and change slowly, and **incomplete by construction** — override it entirely with `idiom_groups` in config.

Its first run against the corpus produced *only* false positives, both now pinned by tests: a package named in a fenced code block inside a Markdown document counted as an import, and `black` was reported as running two HTTP clients when one was `aiohttp` in the `blackd` daemon and the other `urllib3` in a CI helper under `scripts/` — separate programs sharing a repository. After excluding non-source files and standalone script directories it reported **nothing across all 14 repositories of the 0.6.0 corpus** and fired once, correctly, on a repo running `aiohttp` in 27 service files and `httpx` in 3.

That profile is intended: high precision, low recall. Silence means "nothing recognised", never "nothing wrong".

None of the three is a score dimension yet. Most repositories sit at zero, so a median-based reference would be unstable — dividing by ~0.002 turns a rounding difference into a large multiple. Signals earn a place in the score by holding up across more repositories, not by being new.

### Does this detect AI-written code?

**No. No metric measured here separates AI-assisted from human-written code once the comparison is controlled.**

0.6.0 claimed otherwise, and that claim is retracted. It reported near-duplication at 1.49% for AI-written applications against 0.20% for human-written OSS, and called it "the first signal that separates the two populations". The AI cohort was six young applications; the control was twelve libraries with a decade of maintenance behind them. Authorship, age, domain and size all differed at once, and the conclusion was attributed to the only one of those the project found interesting.

The re-run builds a control matched on **age, popularity, language and size**: repositories from the same creation window, inside the same star band (both cohorts have a median of **zero** stars), in the same language mix, with no AI co-author trailer on any of up to 300 sampled commits. Cohorts are built by [`select_authored.py`](../tools/calibration/select_authored.py), measured by [`measure_cohorts.py`](../tools/calibration/measure_cohorts.py), and the analysis below reproduces offline from the checked-in [`cohorts.json`](../tools/calibration/cohorts.json) via [`analyze_cohorts.py`](../tools/calibration/analyze_cohorts.py).

|metric|AI-assisted (n=20)|matched control (n=18)|mature OSS (n=40)|p|size correlation|
|---|---|---|---|---|---|
|near-duplicate rate|1.73%|0.83%|0.64%|0.539|0.10|
|dead code rate|0.00%|0.00%|0.02%|0.381|0.52|
|file failure rate|2.89%|0.80%|3.26%|0.044|0.58|
|function failure rate|9.14%|8.83%|6.70%|0.619|0.12|
|duplicate block rate|6.70|1.73|6.23|0.041|0.49|

**Read the whole table, not the best row.** Two metrics fall under p = 0.05, and both are the two that correlate most strongly with codebase size (r = 0.58 and 0.49) — while the AI cohort carries 1.8x the declarations of the control. Restricting both cohorts to the declaration range they share (109–3,655) removes it: file failures go to **p = 0.121**, duplicate blocks to **p = 0.113**, near-duplication to **p = 0.857**. Five metrics were tested at once, so one p just under 0.05 is what chance alone produces; neither survives a correction for that.

What actually changed from 0.6.0 is instructive: the AI near-duplication figure barely moved (1.49% → 1.73%). **The control moved**, from 0.20% to 0.83%, because it stopped being decade-old libraries. The signal was maturity wearing authorship's clothes.

**This is a negative result, and it has its own limits.** n = 20 against n = 18 is small, so the test would miss anything subtler than roughly a two-fold difference — absence of evidence here is not evidence of absence. The AI cohort is self-selected toward teams whose tooling writes commit trailers, which plausibly means more deliberate workflows than AI-assisted development at large. And the control is "no trailer on any sampled commit", which is weaker than "written by hand". A larger, better-instrumented study could find what this one cannot.

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
