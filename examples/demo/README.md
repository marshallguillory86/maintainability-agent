# Demo tree

A two-module order system with real problems in it. It exists so you can see
what this tool produces before pointing it at your own code.

```bash
cd examples/demo
maintainability-agent --root . --config maintainability-agent.json \
  --output report.md --prompt-output prompt.md
```

`prompt.md` is the product. It should take under a minute to read.

## What it finds, and why each one is real

| Finding | Where | Why it is not a nitpick |
|---|---|---|
| `apply_pricing` is 72 lines, complexity 27 | `billing.py:14` | Tier discounts, coupon rules, shipping, VAT and currency all decide in one function. Changing one rule means reading all of them. |
| Nothing tests `apply_pricing` | `billing.py:14` | It is the most branching code here and the only money path. An untested hotspot is where a regression goes unnoticed. |
| A pricing block is duplicated | `billing.py:16` and `invoices.py:15` | `invoices.py` re-derives the line totals rather than asking `billing.py`. The invoice and the charge can disagree, which is the worst kind of bug to find in production. |

Three finding classes, four items. Each gets its own copy-paste prompt naming
what to change, where, why, and the command that verifies it.

## The score is deliberately absent

The report says **Not scored**, and that is the tool working, not failing:

> No score issued — 2 is below the calibration floor of 24 for files_scanned,
> so no rate drawn from this tree is supported.

The rubric was calibrated against 180 real repositories. Two files cannot
support a rate, so no rate is reported — a demo tree is not a grade. Every
finding and every work item is still real; only the rates are withheld.

That is the whole posture of this tool in one output: **the work order is first
class and the score is second.** A tool willing to print a confident letter for
two files would be willing to print one for your repository on evidence just as
thin.

## Do not fix this tree

The findings are the fixture. A test regenerates the work order and compares it
to `expected-prompt.md`, so repairing `billing.py` fails the suite. If you want
to try the prompts, copy the directory somewhere else first.
