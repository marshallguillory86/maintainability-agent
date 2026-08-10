# Studies and measured results

**Genre: empirical.** Everything here is a claim about the world, and carries pinned inputs, a control where one exists, and its own limits. Nothing here is part of the standard — the rubric, its weights and its thresholds are judgments applied uniformly and live in [the standard](standard.md), which needs no study to be legitimate.

The split exists because mixing the two genres in one document is how this project's one retracted claim reached the README as settled fact. See [the evidence standard](product-intent.md#the-evidence-standard) for the bar each tier of claim must clear.

**Nothing on this page licenses a product claim beyond the sentence stated with it.**

## Summary

| Study | Question | Status |
|---|---|---|
| [Bounded prompt](#does-the-bounded-prompt-work-controlled-experiment-pre-registered) | Does a findings-bounded prompt beat a generic instruction? | Pre-registered; verdict **INCONCLUSIVE** as registered. Generic prompting made 2 of 6 repositories worse; bounded prompting made 1 of 6 worse and improved 5 of 6, closing a median of 7.5 findings against 0 |
| [AI authorship](#does-this-detect-ai-written-code) | Does any metric distinguish AI-written code? | **Retracted.** Matched control, p = 0.546. This design could not measure a difference |
| [Fix breadth](#does-this-detect-ai-written-code) | Are AI-assisted fixes broader? | Exploratory only. Three specifications straddle p = 0.05; none survives Holm |

## Approved summaries

The **only** sentences other documents may use to describe these results. Governing and public documents quote one of these verbatim or say nothing; `test_docs_links.py` compares them character for character, because matching individual numbers cannot detect a swapped attribution or a different sentence built from the same figures.

Changing a sentence here is changing a public claim. Do it when the evidence changes, and correct every document that quotes it in the same commit.

<!-- approved-summaries:start -->
- Generic prompting made 2 of 6 repositories worse; bounded prompting made 1 of 6 worse and improved 5 of 6, under this tool's own finding count.
- No metric measured here distinguishes AI-written code from human-written code; the one claim that did was retracted.
- Re-run against a control matched on age, popularity and language, the near-duplication gap is not significant (p = 0.546), and no other metric earns the claim either.
<!-- approved-summaries:end -->


## Does the bounded prompt work? (controlled experiment, pre-registered)

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

## Does this detect AI-written code?

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

**Fix breadth showed a direction, then failed to hold significance under pinned inputs — reported here as the exploratory trend it is.** "Broad rewrites for narrow bugs" is a diff property, so [`measure_fix_breadth.py`](../tools/calibration/measure_fix_breadth.py) measures it from commit history: over non-merge commits whose subjects mark them as fixes, the files and lines each fix touches. Three specifications have now been run, and their disagreement is the finding. Unpinned caches: nominally significant. Pinned commits over whatever history the cache held: not significant (best banded p = 0.071). Pinned commits over a **deterministic window** (`git log -n 300` from each pinned HEAD — what `fix_breadth.json` now records, with per-repo commit and clone depth): nominally significant again (banded p = 0.029 / 0.046 / 0.037; AI-assisted median 3 vs 2 files per fix, 21% vs 13% broad). The window's determinism took two further corrections, and the second one moved numbers. First: the deepening step was gated on the cached HEAD differing from the pinned commit, so a *shallow cache already at the pin* was accepted as-is, and an audit showed a depth-one clone of one subject yielding 0 fix commits against the deep cache's 96 — dropping the repository from the population entirely rather than measuring it. Depth is now verified and repaired independently of HEAD. Re-measuring under that repair alone reproduced every published figure identically, and an earlier revision of this paragraph stopped there and called the window deterministic.

It was not. A sixth audit found the remaining hole: **the oldest commit a shallow clone holds has no parent**, so git diffs it against the empty tree and its `--numstat` reports the entire tree as added instead of what the commit changed. A synthetic fix commit measured 1 file / 75 lines in a full clone and 2 files / 39 lines at the shallow boundary. This was not hypothetical here — **two AI-cohort repositories had a fix commit sitting on that boundary, and its fabricated whole-tree diff counted as a "broad" fix**, so the bug inflated the AI cohort's broad-fix share in exactly the direction that flattered the hypothesis. Clones now fetch one commit deeper than the window so every commit *in* the window is parented, and grafted boundary commits are excluded outright. Corrected figures: `broad_fix_share` **p = 0.025 → 0.028** unbanded, with two per-repo shares falling (0.114 → 0.102, 0.434 → 0.427). The banded tests and the medians quoted above are unchanged. `tests/test_fix_breadth_window.py` now pins the property across cache depths with synthetic repositories, rather than pinning the one repository whose failure had been demonstrated. A result that crosses the 0.05 line depending on window choice is fragile by demonstration, none of the three specifications survives a Holm correction for the three correlated outcomes (threshold 0.0167), no primary outcome was registered, authorship is classified per *repository* rather than per fix commit, and fix detection trusts subject lines, which agent tooling writes far more consistently than humans (19/20 vs 11/18 repos cleared the labeled-fix filter). The honest status is unchanged by the friendlier third run: **a consistent direction worth a better-designed study — a diff-content fix detector, a registered primary outcome, commit-level authorship — and no claim beyond that.**

**The design has a hole no statistics repair: the control cannot be verified as human.** "No AI trailer on any sampled commit" excludes only tooling that writes trailers — Copilot and pasted LLM output leave none. The control contains zero-star 2024-25 projects whose subject matter (RAG apps, AI platforms) makes LLM assistance likely. If enough of the control is quietly AI-assisted, this study compares AI-with-trailers to AI-without-trailers, and its null is guaranteed and uninformative. That is why the honest conclusion is **"this design could not measure a difference"**, not "there is no difference". Add the usual limits — n = 20 vs 18 misses anything subtler than roughly two-fold, and the trailer-writing cohort self-selects for deliberate workflows — and the study licenses exactly one claim: the 0.6.0 evidence was wrong, and nothing measured so far replaces it. A study that wanted the stronger claim would need a control whose humanity is verifiable, such as code committed before LLM assistants existed, measured at a pinned historical commit.
