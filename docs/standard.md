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

> **Architecture decision:** repeated audits showed that the current raw-dictionary scorer conflates maintainability with evidence sufficiency. [ADR 001](adr-001-evidence-and-verification.md) defines the accepted replacement: typed evidence states, versioned normalization, separate estimates and verified grades, and manifest-based history measurements. Its implementation status is tracked in one place, the [decision register](decisions.md). `score.evidence_status` and `score.verified_grade` ship and every consumer surfaces them; this page describes the compatibility scoring behaviour, which stages 8 and 9 will finish changing.

### The rubric: aspects → categories → overall

The score is a three-layer rollup, and every layer is visible in the report (`score.aspects`, `score.rubric`) and in [`_formula.py`](../src/maintainability_audit/_formula.py), which is the single source both the scorer and the calibration derive from.

**Layer 1 — aspects.** Thirteen measured aspects, each scored 0–5. Two kinds:

|aspect|kind|measured as|
|---|---|---|
|file_size|calibrated|file-size pressure vs. corpus median, through the score curve|
|declaration_size|calibrated|declaration size/complexity pressure (production code only)|
|duplication|calibrated|exact duplicate-block pressure vs. corpus median|
|risk_patterns|calibrated|configured risk-pattern density vs. corpus median|
|policy_gates|calibrated|hard-gate failures vs. the one-failure unit|
|test_presence|rubric|share of declarations living in test files (0 test files → 0.0)|
|dead_code|rubric|unreferenced private declarations per production declaration|
|near_duplication|rubric|near-duplicate declarations per production declaration|
|idiom_consistency|rubric|count of concerns served by competing libraries|
|churn_hotspots|rubric|share of changed files that are hotspots (5+ commits and cognitive ≥ 50)|
|change_coupling|rubric|share of changed files in code-to-code co-change pairs|
|knowledge_concentration|rubric|share of settled files (3+ commits) with a single author|
|documentation|rubric|artifact presence: README, changelog, docs directory|

**Calibrated** aspects inherit the corpus anchor — 1.0x the mature-OSS median maps to the same score everywhere. **Rubric** aspects score evidence a corpus median cannot price, against banded thresholds stated in [`scoring.py`](../src/maintainability_audit/scoring.py), informed by the corpus and cohort measurements where those exist.

An aspect that cannot be measured — no git history, a pre-0.4.0 baseline without the newer counts — reports **null**, prints "not measurable", blocks the A-grades, prices at the corpus anchor (4.0) in the point estimate, and **widens `score.maintainability_range`**, the interval obtained by pricing every unknown at 0 and at 5. Renormalizing unknowns away was audited into retirement (hiding evidence deleted its weight entirely); anchor pricing was then audited too, correctly: **no single imputed value stops concealment from flattering a repo whose true evidence is worse than the imputed one** — with the anchor, hiding worst-band history still improves the point estimate by up to the anchor-to-worst gap. That residual is inherent to imputation, so `score.maintainability_estimate` is not the field the grade is banded from.

**The verified grade bands the floor, not the point estimate.** `score.verified_grade` comes from `maintainability_range[0]` — every unmeasured aspect priced at 0. Hiding an aspect can only widen the interval downward, so concealment is monotonically unprofitable at every grade boundary rather than only at A, and supplying the evidence raises the floor to meet the point estimate.

That property is only as good as the definition of "unmeasured", and the first version of it was wrong. An audit showed that deleting `test_file_count` outright scored *better* than reporting zero tests, because the untested testability cap was a penalty that fired only on reports carrying the evidence — so the floor rose when the field vanished. Sweeping every summary key found three more with the same shape (`file_failures`, `files_scanned`, `risk_findings`), where an absent count read as "zero findings" rather than "not counted". Absent inputs now make their aspect `None` — priced at the anchor for the point estimate, at zero for the floor — and unknown test evidence applies the cap on the floor side. `test_withholding_any_single_input_cannot_raise_the_floor_or_the_grade` sweeps the summary dict itself, so a field added next year is covered the day it is added. The interval alone was not enough: an audit demonstrated a repository grading C with its worst-band history visible and B with the same history withheld, and observed that printing the width warned a careful human while every machine consumer — CI gate, badge, ranking, API — kept reading the flattered field. That was a fair hit; disclosure is not closure. When the two differ, a blocker names both numbers, so a report never shows a demotion it does not explain. Practical consequence: `actions/checkout` at its default `fetch-depth: 1` costs roughly a grade. Use `fetch-depth: 0`.

`maintainability_range` always contains `maintainability_estimate`. Both endpoints run the identical pipeline with only the unknown price swapped, including the untested testability cap — an audit found the cap applied to the point estimate and not to the endpoints, producing a repository that scored 4.4 inside a stated range of `[4.5, 4.5]`, an interval excluding the number it claimed to bound. `test_the_interval_always_contains_the_score` checks the untested boundary explicitly, because the collapse test that existed at the time used a tested repository and walked straight past it.

**Layer 2 — categories.** Each ISO category is a weighted mean of its aspects (weights in `_formula.CATEGORY_ASPECTS`; unmeasured aspects contribute the anchor value):

|category|aspects (weight)|
|---|---|
|modularity|file_size .35, duplication .25, change_coupling .25, churn_hotspots .15|
|reusability|duplication .30, near_duplication .30, idiom_consistency .25, file_size .15|
|analyzability|declaration_size .30, documentation .20, dead_code .15, risk_patterns .15, churn_hotspots .10, knowledge_concentration .10|
|modifiability|change_coupling .25, duplication .20, churn_hotspots .15, risk_patterns .15, knowledge_concentration .10, policy_gates .10, file_size .05|
|testability|test_presence .50, declaration_size .30, policy_gates .20|

Every aspect in Layer 1 appears in at least one of those rows, and `test_every_scored_aspect_carries_weight_in_some_category` fails the build if one does not. It was added because one of them didn't: `knowledge_concentration` was measured, printed under "Aspect Scores" and documented here while carrying weight in no category, so a repository could move from every settled file having many authors to every settled file having one and score identically. Thirteen aspects were advertised and twelve were doing the work. Bus factor now costs a tenth of analyzability and a tenth of modifiability — code only one person has touched is code only one person can read quickly or change safely — and the constant was re-fitted around it.

**Why ownership concentration belongs in analyzability at all.** Addy Osmani names a *comprehensibility trap* in [Agentic Code Quality](https://addyo.substack.com/p/agentic-code-quality): as automated constraints absorb more of the review load, developers' mental models of the codebase quietly degrade, and he leaves the problem open. `knowledge_concentration` is a partial instrument for it. The classic reading of a single-author file is succession risk — what happens if they leave. The agentic reading is stronger and more immediate: a file that one identity has ever touched may be a file **no human has read closely**, and analyzability is precisely the question of whether someone can build a correct model of it. This is a framing borrowed from someone else's essay, not a measurement: it justifies the weight's placement, it does not evidence that the weight is correct. Only the outcome study above could do that.

**Layer 3 — overall.** Equal-weighted mean of the five categories — ISO orders its sub-characteristics no other way, and an unequal weighting would be a claim nothing here supports. The testability cap (below) is applied before this mean, and the mean is taken over the categories **exactly as displayed** (rounded), so `maintainability_estimate == weighted mean of the printed categories` is arithmetic a reader can check on any report — an audit produced a counterexample when it was computed from hidden unrounded values.

The calibration constant is fitted so the **corpus median rolls up to exactly 4.0 through the same pipeline**, and that phrase has now been earned the hard way. Three consecutive audits found the derivation differing from the live scorer by exactly one step: first the category rounding, then the untested testability cap (corpus member `tabby` derived 3.9 and scored 3.8 live), then the per-aspect rounding inside the score curve. Each time the median survived and the per-repository claim did not. The fix was to stop having two implementations: `_derive._corpus_overall` now calls `_formula.overall_from_aspects` — the function `score_report` calls — and `test_derivation_matches_live_score_report_repo_by_repo` compares the derivation against `score_report` for **all forty corpus repositories**, not at the median. A median that survives a per-repository discrepancy is luck, and the two previous versions of this paragraph were relying on it. The rounded pipeline is a step function, so c is the midpoint of the plateau where the median hits 4.0 exactly. Evidence aspects (test presence, dead code, near-duplication, idioms, documentation) are captured per corpus repo in `measurements.json`; history aspects price at the anchor in the derivation exactly as they do for any shallow clone, because the corpus is pinned via shallow fetches. `tests/test_calibration_corpus.py` re-derives the constant offline through this full path.

**Grades on top of the number:** A+/A are gated on per-dimension ceilings (below), and two evidence rules bind them:

- **A repository with production code and no test evidence cannot receive an A-grade.** Zero test files, or test files containing zero declarations — an empty test-shaped artifact bought an A once, and that hole is closed — cap testability at 2.0 and demote with a named blocker. The published meaning of a 5 includes "tested", and that sentence is enforced, not aspirational.
- **Unknown evidence blocks the top grades.** A+ is published as "nothing is wrong anywhere"; a shallow clone that hides coupling, hotspots and ownership is not that — it is "nothing was wrong in what could be seen". Unmeasured aspects demote to B with a blocker naming them, and because the grade bands the evidence floor, they usually cost more than that one step. The blocker is now stated at every grade, not only when an A is being withheld: a demotion nobody explains is the failure this list exists to prevent. "Couldn't look" blocks; "looked and there was nothing to measure" (a young repo where no file has three commits yet) does not.
- **NotApplicable evidence is resolved, not uncertain.** An aspect with no population is removed from its category denominator for the point estimate and both bounds. It receives neither a perfect score nor an unknown price, so a complete young repository's range collapses without charging it for a population that does not exist.

**What is not scored, and why.** These are aspects of maintainability by any honest definition; no measurement in this tool reaches them, so they appear in every report's rubric as unscored rather than being silently absent:

|aspect|why it is not scored|
|---|---|
|test_effectiveness|requires running the suite (mutation/coverage); this audit never executes code|
|naming_quality|no static proxy survives contact; a wrong-name detector needs semantics|
|comment_accuracy|comments are deliberately unparsed; staleness needs meaning, not structure|
|indirection_depth|call-graph construction is not implemented for the supported languages|
|architectural_coherence|no measurement distinguishes a wrong boundary from an unusual one statically|

**The rubric is a standard, not a prediction.** Like any standard — ISO/IEC 25010 itself, a building code, a style guide — it is a set of judgments made explicit, applied deterministically, and identical for every repository it grades. That is what gives a standard its authority: it is stated, stable, and uniform. Anyone who disagrees with a weight or a band can read both in source ([`_formula.py`](../src/maintainability_audit/_formula.py), [`scoring.py`](../src/maintainability_audit/scoring.py)) and argue with them; **they are not yet configurable** — overriding the rubric per-repo is roadmap, and a standard everyone edits stops being one, so any override mechanism will label its output as a house variant. No validation study is required to license a standard, and this document does not apologize for containing judgments.

What *does* require evidence is any empirical claim about the world — "this metric separates AI-written code" was one, and it was retracted when a controlled comparison failed to support it. The two kinds of claim are held to different bars on purpose.

**Tuning the standard against outcomes.** ISO defines maintainability as the *effort to modify*, and an outcome study — score repositories at a past commit, measure the following year's fix-churn, rework and change breadth, check the correlation on held-out repositories — would show whether the rubric's emphasis matches where effort is actually spent. That is worth running not to legitimize the standard but to **tune** it: if observed change effort loads on coupling twice as hard as the weights do, the weights should move. It has not been run yet.

### Studies that tested claims about this tool

Moved to [studies.md](studies.md), which is where empirical claims live. Two questions were tested and neither produced a product claim: whether [the bounded prompt works](studies.md#does-the-bounded-prompt-work-controlled-experiment-pre-registered) (registered verdict INCONCLUSIVE) and whether [any metric detects AI-written code](studies.md#does-this-detect-ai-written-code) (retracted).

This page is the **standard** — judgments made explicit and applied identically to every repository. It requires no study to be legitimate, which is exactly why the studies are kept somewhere else.

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

### Finding-level signals (scored via the rubric since the aspect rework)

**Near-duplicate declarations** (0.6.0) detect a helper written twice under two names — the failure mode most often attributed to AI-written code, where an agent that cannot see your existing helper writes a second one. Exact text matching cannot catch it, so declaration bodies are reduced to a token sequence with identifiers anonymized by order of first appearance; renamed copies produce identical fingerprints.

It is a useful finding on its own terms. It is **not** evidence about who wrote the code — see below.

Two false-positive classes were removed by fitting the near-duplicate eligibility thresholds against the corpus rather than guessing them: bodies too short for similarity to mean anything, and thin delegations whose shape is dictated by the API surface (requests' `put`/`patch`, flask's `template_filter`/`template_test`). Test files are excluded — in mature projects nearly all near-duplicates are deliberately parallel test variants, which are not the defect being measured.

**Unreferenced private declarations** (0.6.0) find debris — a helper written for an approach abandoned two prompts later. Only declarations the language marks internal are candidates (a leading underscore in Python, no `export` in JS/TS), because privacy is the author's own claim that no external caller exists, which is what makes "no references here" sufficient evidence. Public functions, decorated declarations, dunder methods and test files are left alone.

Two false-positive classes surfaced on first contact with the corpus and are now pinned by tests. Counting identifiers over the *masked* copy blanked f-string interpolations, which are live code — flask's `_get_werkzeug_version` is called from inside one and was reported dead. And an object-literal method (`beforeBreadcrumb(crumb) { … }` in a Sentry config) binds no name and is invoked by whoever receives the object. Fixing both dropped one repo's findings from 15 to 0.

It earns a place in the report as hygiene, **not** as evidence for anything about AI-written code. Note also that a private *method* on a public class can be reached by a downstream subclass, so those findings deserve a look rather than a reflex deletion.

**Competing libraries for one concern** (0.6.0) flag a codebase where two packages do one job — three HTTP clients means three error shapes and three retry stories, and no single mental model covers the code. This is the one detector that **needs a curated list**, and that cost is real: there is no structural way to know that `moment` and `date-fns` compete while `react` and `react-dom` do not. The shipped list is deliberately small, restricted to concerns whose alternatives are well known and change slowly, and **incomplete by construction** — override it entirely with `idiom_groups` in config.

Its first run against the corpus produced *only* false positives, both now pinned by tests: a package named in a fenced code block inside a Markdown document counted as an import, and `black` was reported as running two HTTP clients when one was `aiohttp` in the `blackd` daemon and the other `urllib3` in a CI helper under `scripts/` — separate programs sharing a repository. After excluding non-source files and standalone script directories it reported **nothing across all 14 repositories of the 0.6.0 corpus** and fired once, correctly, on a repo running `aiohttp` in 27 service files and `httpx` in 3.

That profile is intended: high precision, low recall. Silence means "nothing recognised", never "nothing wrong".

All three now feed the score as rubric aspects (near_duplication, dead_code, idiom_consistency) — banded against fixed thresholds rather than median-normalized, because most repositories sit at zero and dividing by ~0.002 would turn a rounding difference into a large multiple. An earlier revision of this page said they were unscored after they no longer were; an audit caught the drift.

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

Current scoring inputs (the thirteen aspects above, i.e.):

- file warnings and failures; function/class size, cyclomatic and cognitive complexity warnings and failures
- duplicate block count; near-duplicate declarations; unreferenced private declarations; competing-library concerns
- configured risk-pattern findings; hard-gate failures
- test presence (share of declarations in test files)
- documentation artifacts (README, changelog, docs directory)
- history, when available: churn hotspots, code-to-code change coupling, single-author concentration

Grades:

| Grade | Overall Score |
|---|---:|
| A+ | 4.8 to 5.0 |
| A | 4.5 to 4.7 |
| B | 4.0 to 4.4 |
| C | 3.0 to 3.9 |
| D | 2.0 to 2.9 |
| F | below 2.0 |

## Shared vocabulary, and where this tool's terms differ

**Genre: judgment.** The quality framework this standard aligns with publishes a glossary — cyclomatic complexity, duplication %, code churn, bus factor, coverage %. Where this tool measures the same quantity it uses the same word. Where it measures something *related but different*, it keeps its own name and states the relationship here, because adopting a term for a quantity you do not compute is how a report comes to claim more than it measured.

| Framework term | This tool | Relationship |
|---|---|---|
| cyclomatic complexity | `cyclomatic_complexity` | same measurement |
| duplication % | `duplication` | same measurement, expressed as a rate over files |
| code churn | `churn` | same measurement, over a stated window |
| coverage % | — | **not measured.** Supplied by the operator or absent; never inferred |
| **bus factor** | `knowledge_concentration` | **different quantity.** Bus factor counts the people whose loss would stall the project. This counts the share of settled files (3+ commits) that exactly one person has touched. A repository where one author owns 80% of files can still have a bus factor of four, so the names are not interchangeable |

`test_the_ownership_aspect_does_not_claim_to_be_bus_factor` fails the build if the ownership key is renamed to the framework's term.

## Risk and effort per finding class

**Genre: judgment.** These weightings are this project's opinion about what
each kind of finding costs to leave alone and what it costs to fix. They are
published here, rather than buried in code, so a team that disagrees has a
number to point at. `test_the_declared_weightings_are_published_in_the_standard`
fails the build if a class is weighted in code and missing from this table.

Risk and effort each run 1–5. A finding is **high risk** at 3 or
above and **high effort** at 3 or above, and the two together
place it in one of four bands:

| | low effort | high effort |
|---|---|---|
| **high risk** | **Quick Win** — lead with these | **Major Project** — name it, never inline it into a prompt |
| **low risk** | Fill-In — offer opportunistically | Reconsider — suppressed unless asked for |

| Finding class | Risk | Effort | Band | Why |
|---|---:|---:|---|---|
| `risk-pattern` | 5 | 1 | **quick-win** | a configured risk pattern is a rule this project chose to enforce on itself, and each hit is a single located line |
| `oversized-declaration` | 4 | 2 | **quick-win** | a long, branching function is where defects concentrate and where every future change has to be understood first; extracting one is bounded, local work |
| `duplicate-block` | 4 | 4 | **major-project** | duplicated logic means a fix applied in one place and missed in the others; deduplicating across a codebase is a design change, not a tidy-up |
| `oversized-file` | 3 | 3 | **major-project** | a file past the limit hides its own structure, but splitting one touches every importer and is a change worth reviewing on its own |
| `near-duplicate` | 3 | 4 | **major-project** | near-copies drift apart silently, which is worse than exact duplication; reconciling them requires deciding which behaviour was intended |
| `dead-code` | 2 | 1 | **fill-in** | unreachable code costs reading time and misleads a search, but deleting it is the cheapest change there is |
| `competing-libraries` | 2 | 4 | **reconsider** | two libraries doing one job is a decision nobody made; converging on one is a migration across every call site |

**Why Major Projects are withheld from the agent prompt.** An agent told to
deduplicate a pattern across forty files produces exactly the sprawling,
unreviewable diff a bounded prompt exists to prevent. The work is real and
appears in the report; scoping it is a human's job first.

**What a work item's delta means.** Each item carries two numbers. `delta` is
what clearing that single finding moves the published score — honestly zero
more often than not, because the overall is the mean of the *rounded*
categories and is therefore a step function. `class_delta` is what clearing
every finding of that class is worth, and it is what the ordering uses.
Neither is estimated: both come from re-running `score_report` over a summary
with those findings removed. Per-item deltas do not sum to the whole.

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
- Addy Osmani, *Agentic Code Quality* (constraints as back-pressure; the comprehensibility trap): https://addyo.substack.com/p/agentic-code-quality
- SonarQube metrics: https://docs.sonarsource.com/sonarqube/latest/user-guide/code-metrics/metrics-definition/
- Code Climate maintainability: https://docs.codeclimate.com/docs/maintainability
- Code Climate default thresholds: https://docs.codeclimate.com/docs/default-analysis-configuration
- ESLint complexity rule: https://eslint.org/docs/latest/rules/complexity
- Radon metrics: https://radon.readthedocs.io/en/latest/intro.html
- Semgrep docs: https://semgrep.dev/docs/
