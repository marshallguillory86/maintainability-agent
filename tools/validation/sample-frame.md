# Report validation sample: the frame, written before selection

Why this exists, what it is chosen for, and what it cannot show. Written and committed **before any repository is cloned**, so the set cannot be quietly reselected until the tool looks good on it.

## What this is not

Not the [reference corpus](../calibration/corpus.json). That set has one frame — *mature open-source software* — because it calibrates the **scale**, and a scale needs a defensible stand-in for "what good looks like".

This set answers a different question: **is the output any use on real code?** Findings located where they claim, a work order somebody could act on, coverage stated honestly, a score that a reader with the repository in front of them would recognise. Reusing the calibration corpus would tell us how the tool behaves on well-maintained JavaScript libraries and nothing else.

## Selection axes

Chosen for **variety**, deliberately including cases the tool is expected to handle badly, because a sample that only contains cases it handles well proves nothing.

| Axis | Why it matters | Range wanted |
|---|---|---|
| **Language** | Tool coverage is wildly uneven — `complexipy`, `radon`, `ruff`, `vulture`, `mypy`, `pydocstyle` and `interrogate` are Python-only; only `lizard` and `jscpd` are multi-language | Python (full), JS/TS (partial), Java / Go / Rust / C (lizard and jscpd only) |
| **Size** | The population floors gate the score, and the report must behave at both ends | Below the floor (< 32 files or < 139 declarations), mid-size, large |
| **Structure** | A monorepo exercises paths, exclusions and per-package reality | At least one monorepo, mostly single-package |
| **Condition** | A report that only works on tidy code is a report for nobody | Actively maintained and visibly neglected |

## What a pass looks like

Stated in advance so the results cannot be graded generously afterwards:

1. **The tool completes** on every repository, or reports why it could not — never a crash, never a hang.
2. **Findings are locatable.** A sampled finding's `path:line` points at code that matches its message.
3. **Coverage is honest.** Concerns nothing examined are named, and no language gets a score implying tools that never ran.
4. **The floor behaves.** A repository under the population floor gets findings and no score, with the reason naming the shortfall.
5. **Nothing is fabricated.** Every number in the write-up comes from a recorded run, and repositories that fail are reported as failures rather than dropped.

## What it cannot show

It is a **convenience sample**, not a random one, so nothing here supports a claim about repositories in general. It cannot say the score is *correct* — no ground truth for maintainability exists to check against. It shows whether the output is coherent, located, honest about its gaps, and useful to read.

Under the [evidence standard](../../docs/product-intent.md#the-evidence-standard) this is Tier 3: pinned inputs, a stated frame, stated limits, and results that stand or fall on the recorded run.
