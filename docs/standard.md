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

An aspect that cannot be measured — no git history, a pre-0.4.0 baseline without the newer counts — reports **null**, prints "not measurable", blocks the A-grades, prices at the corpus anchor (4.0) in the point estimate, and **widens `score.overall_range`**, the interval obtained by pricing every unknown at 0 and at 5. Renormalizing unknowns away was audited into retirement (hiding evidence deleted its weight entirely); anchor pricing was then audited too, correctly: **no single imputed value stops concealment from flattering a repo whose true evidence is worse than the imputed one** — with the anchor, hiding worst-band history still improves the point estimate by up to the anchor-to-worst gap. That residual is inherent, so it is pinned by test at its bound and made visible: a report with unknowns carries an interval, and a reader comparing two scores must compare intervals, not points.

**Layer 2 — categories.** Each ISO category is a weighted mean of its aspects (weights in `_formula.CATEGORY_ASPECTS`; unmeasured aspects contribute the anchor value):

|category|aspects (weight)|
|---|---|
|modularity|file_size .35, duplication .25, change_coupling .25, churn_hotspots .15|
|reusability|duplication .30, near_duplication .30, idiom_consistency .25, file_size .15|
|analyzability|declaration_size .30, documentation .20, dead_code .20, risk_patterns .15, churn_hotspots .15|
|modifiability|change_coupling .25, duplication .20, churn_hotspots .20, risk_patterns .15, file_size .10, policy_gates .10|
|testability|test_presence .50, declaration_size .30, policy_gates .20|

**Layer 3 — overall.** Equal-weighted mean of the five categories — ISO orders its sub-characteristics no other way, and an unequal weighting would be a claim nothing here supports. The testability cap (below) is applied before this mean, and the mean is taken over the categories **exactly as displayed** (rounded), so `overall == weighted mean of the printed categories` is arithmetic a reader can check on any report — an audit produced a counterexample when it was computed from hidden unrounded values. The calibration constant is fitted so the **corpus median rolls up to exactly 4.0 through this same pipeline — including the one-decimal category rounding score_report ships**; the rounded pipeline is a step function, so c is the midpoint of the plateau where the median hits 4.0 exactly (an audit caught an earlier version deriving through unrounded values while claiming "same pipeline"), priced by the same aspect functions live reports go through — including the evidence aspects (test presence, dead code, near-duplication, idioms, documentation), which are captured per corpus repo in `measurements.json`. History aspects price at the anchor in the derivation exactly as they do for any shallow clone, because the corpus is pinned via shallow fetches. `tests/test_calibration_corpus.py` re-derives the constant offline through this full path.

**Grades on top of the number:** A+/A are gated on per-dimension ceilings (below), and two evidence rules bind them:

- **A repository with production code and no test evidence cannot receive an A-grade.** Zero test files, or test files containing zero declarations — an empty test-shaped artifact bought an A once, and that hole is closed — cap testability at 2.0 and demote with a named blocker. The published meaning of a 5 includes "tested", and that sentence is enforced, not aspirational.
- **Unknown evidence blocks the top grades.** A+ is published as "nothing is wrong anywhere"; a shallow clone that hides coupling, hotspots and ownership is not that — it is "nothing was wrong in what could be seen". Unmeasured aspects demote to B with a blocker naming them. "Couldn't look" blocks; "looked and there was nothing to measure" (a young repo where no file has three commits yet) does not. CI note: `actions/checkout` defaults to `fetch-depth: 1`; use `fetch-depth: 0` for the full grade.

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

### Does the bounded prompt work? (controlled experiment, pre-registered)

The product's central promise — a findings-bounded prompt produces narrower, more targeted agent fixes than a generic instruction — was tested under a protocol committed before any run ([`PROTOCOL.md`](../tools/experiments/fix_scope/PROTOCOL.md)): six repositories at pinned commits, two `codex exec` runs each (`gpt-5.6-sol`, 10-minute budget), generic instruction versus this tool's generated prompt. **Provenance, stated precisely:** the protocol — including the decision rule — was committed before the first run began; the analyzer was **not**: its first version landed about a minute into the runs, and it was rewritten mid-run after an audit found it diverged from the protocol's wording. What predates the data is the rule; the code applying it does not, and an earlier revision of this page claimed otherwise. Every arm was re-derived against its pinned base after a runner defect was audited (no recorded number changed). Raw data: [`results.json`](../tools/experiments/fix_scope/results.json), plus [`artifacts/`](../tools/experiments/fix_scope/artifacts/) holding every arm's full diff against its pinned base and every bounded prompt (regenerated deterministically from the pinned inputs; regenerated lengths match the recorded ones byte-for-byte). The agents' full transcripts were not captured — only 2,000-character tails — and cannot be recovered; that loss is permanent and noted here rather than papered over.

**The registered verdict is INCONCLUSIVE**, and it stands as registered:

|median (n = 6 pairs)|generic|bounded|
|---|---|---|
|files touched|2.5|3.0|
|lines changed|113.5|170|
|out-of-scope share|0.500|0.484|
|findings closed|**0.0**|**7.5**|

The bounded arm was **not narrower** on files touched — one of the three registered conditions — so the claim is not SUPPORTED. It was better-targeted (out-of-scope share lower, paired median −0.10) and closed far more findings (positive in 5 of 6 pairs, paired median +14, best single run +78), so the claim does not FAIL either.

What the data descriptively shows is not the contest the protocol anticipated. The registered rule braced for generic-prompt *thrashing* — broad rewrites the bounded prompt would rein in. Under this model and budget the generic instruction instead produced **timid motion**: median zero findings closed, and **two generic-arm runs made their codebase measurably worse** (net −6 and −7 findings; one *bounded* run also went net −1, and an earlier revision of this page miscounted the two arms' failures as three generic). The bounded prompt's measured value here is *effectiveness by this tool's aggregate count* — total findings fell sharply in its arms, at comparable breadth — not narrowness, and not verified finding-by-finding: `findings_closed` is a net aggregate, so closing named findings and, say, deleting code that carried findings are indistinguishable in it. The scope set also contains every finding path in the full report, which is broader than the subset the prompt actually names, and a supporting test or doc edit counts as out-of-scope unless that file had findings of its own — both symmetric across arms, neither what the phrase "named findings" implies. The out-of-scope difference itself is small (0.484 vs 0.500 marginal; paired median −0.10 at n = 6).

**Limits, stated with the result:** n = 6 pairs and one agent/model; a 10-minute budget that may cap generic exploration; subject test suites were not executed, so a fix that breaks behavior counts the same as one that does not; and findings-closed is measured by this tool's own ruler while the bounded prompt names exactly what that ruler measures — some closure is teaching-to-the-test by construction. A SUPPORTED claim about narrowness would need an agent and budget under which the generic arm actually rewrites broadly, and an outcome measure not owned by the vendor of the prompt.

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

### Does this detect AI-written code?

**This tool does not claim to. Its 0.6.0 claim that it could is retracted, and a follow-up study designed to test the claim properly could not measure a difference — which is weaker than "there is no difference", and the distinction matters.**

0.6.0 reported near-duplication at 1.49% for AI-written applications against 0.20% for human-written OSS, and called it "the first signal that separates the two populations". The AI cohort was six young applications; the control was twelve libraries with a decade of maintenance behind them. Authorship, age, domain and size all differed at once, and the conclusion was attributed to the only one of those the project found interesting.

The re-run builds a control **selected to match on age, popularity and language** — same creation window, same star band (both cohorts have a median of **zero** stars), same language mix, with no AI co-author trailer on any of up to 300 sampled commits. **Size was not matched at selection**: the AI cohort came out carrying 1.8x the control's median declarations, and size is handled after the fact by re-testing inside a common size band, which is a weaker control than matching would have been. Cohorts are built by [`select_authored.py`](../tools/calibration/select_authored.py) and measured by [`measure_cohorts.py`](../tools/calibration/measure_cohorts.py); the cohort definitions are pinned in [`ai.json`](../tools/calibration/ai.json) and [`human.json`](../tools/calibration/human.json), and the analysis reproduces offline from the checked-in [`cohorts.json`](../tools/calibration/cohorts.json) via [`analyze_cohorts.py`](../tools/calibration/analyze_cohorts.py). The rank-sum test carries tie and continuity corrections and is pinned numerically against scipy — an earlier version lacked the tie correction, which inflated p-values by up to 2.4x on tie-heavy metrics, in the direction that flattered the null.

|metric|AI-assisted (n=20)|no-trailer control (n=18)|mature OSS (n=40)|p|size correlation|
|---|---|---|---|---|---|
|near-duplicate rate|1.73%|0.83%|0.64%|0.546|0.10|
|dead code rate|0.00%|0.00%|0.02%|0.266|0.52|
|file failure rate|2.89%|0.80%|3.26%|0.043|0.58|
|function failure rate|9.14%|8.83%|6.70%|0.629|0.12|
|duplicate block rate|6.70|1.73|6.23|0.042|0.49|

**Read the whole table, not the best row.** Two metrics fall under p = 0.05 — more than chance alone would typically yield across five tests, but they are also the two metrics most correlated with codebase size (r = 0.58 and 0.49), and the AI cohort is the larger one. Inside the shared size band (109–3,655 declarations), file failures go to **p = 0.123 with the medians nearly equal** (1.82% vs 1.77%) — that gap really does look like size. Duplicate blocks are less tidy: **p = 0.117, but the banded medians still differ 3.3x** (5.67 vs 1.73), so that comparison is underpowered rather than resolved, and a larger study could plausibly find a real difference there. Near-duplication — the retracted headline — is p = 0.546 unbanded and 0.871 banded: not close.

What actually changed from 0.6.0 is instructive: the AI near-duplication figure barely moved (1.49% → 1.73%). **The control moved**, from 0.20% to 0.83%, because it stopped being decade-old libraries. The signal was maturity wearing authorship's clothes.

**Fix breadth showed a direction, then failed to hold significance under pinned inputs — reported here as the exploratory trend it is.** "Broad rewrites for narrow bugs" is a diff property, so [`measure_fix_breadth.py`](../tools/calibration/measure_fix_breadth.py) measures it from commit history: over non-merge commits whose subjects mark them as fixes, the files and lines each fix touches. Three specifications have now been run, and their disagreement is the finding. Unpinned caches: nominally significant. Pinned commits over whatever history the cache held: not significant (best banded p = 0.071). Pinned commits over a **deterministic window** (`git log -n 300` from each pinned HEAD — what `fix_breadth.json` now records, with per-repo commit and clone depth): nominally significant again (banded p = 0.029 / 0.046 / 0.037; AI-assisted median 3 vs 2 files per fix, 21% vs 13% broad). A result that crosses the 0.05 line depending on window choice is fragile by demonstration, none of the three specifications survives a Holm correction for the three correlated outcomes (threshold 0.0167), no primary outcome was registered, authorship is classified per *repository* rather than per fix commit, and fix detection trusts subject lines, which agent tooling writes far more consistently than humans (19/20 vs 11/18 repos cleared the labeled-fix filter). The honest status is unchanged by the friendlier third run: **a consistent direction worth a better-designed study — a diff-content fix detector, a registered primary outcome, commit-level authorship — and no claim beyond that.**

**The design has a hole no statistics repair: the control cannot be verified as human.** "No AI trailer on any sampled commit" excludes only tooling that writes trailers — Copilot and pasted LLM output leave none. The control contains zero-star 2024-25 projects whose subject matter (RAG apps, AI platforms) makes LLM assistance likely. If enough of the control is quietly AI-assisted, this study compares AI-with-trailers to AI-without-trailers, and its null is guaranteed and uninformative. That is why the honest conclusion is **"this design could not measure a difference"**, not "there is no difference". Add the usual limits — n = 20 vs 18 misses anything subtler than roughly two-fold, and the trailer-writing cohort self-selects for deliberate workflows — and the study licenses exactly one claim: the 0.6.0 evidence was wrong, and nothing measured so far replaces it. A study that wanted the stronger claim would need a control whose humanity is verifiable, such as code committed before LLM assistants existed, measured at a pinned historical commit.

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
