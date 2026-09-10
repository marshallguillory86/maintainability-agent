# Work-order run, 2026-09-10 — the tool's own backlog, worked to a disposition

**Genre: work log.** Written to be cited. Every row here is a decision with
the measurement that drove it, so a reader can disagree with the decision
without having to re-derive the facts.

The subject is `maintainability-agent` auditing itself at `v3.1.0`
(`87cf1ef`), through its own MCP server, with the analyzer pool running.
That run produced **64 work-order items**. This document takes every one of
them to a disposition: fixed, or refused with the reason.

## Why a refusal is a disposition

This project's own remediation rules say: *"Explain false positives or
justified complexity instead of contorting clear code to satisfy a
metric."* A backlog worked to zero by satisfying the metric is worth less
than a backlog worked to zero by judgment, and the difference is only
visible if the refusals are written down with their evidence.

Two of the six non-trivial items here are refusals. Both are cases where
the detector was **correct by its own rule** and the right engineering
answer was still "no". That is the interesting half of the run.

## The starting state

| | |
|---|---|
| Version | 3.1.0 (`87cf1ef`) |
| Grade | C · estimate 4.1 / 5 · range 3.8 – 4.6 |
| Evidence | complete, profile `default-v1` |
| Analyzers | 10 of 13 contributing |
| Files scanned | 497 |
| Hard gate failures | 0 |
| Work-order items | 64 |

Item classes: 58 `unpaired-hotspot`, 4 `near-duplicate`, 2 `dead-code`.

## Dead code — 2 items, both fixed

Both were genuinely unreferenced. The check before deleting was a
repository-wide grep for the name, in `src/`, `tests/` and `tools/`, with
the definition line excluded: zero call sites for each.

| Item | Evidence | Action |
|---|---|---|
| `_pressures._breach_counts` (26 lines) | no reference anywhere | deleted |
| `_grant_ledger._grant_still_names_what_was_granted` (8 lines) | no reference anywhere | deleted |

Neither is a judgment call. Unreferenced code costs reading time and
misleads a search, and deleting it is the cheapest change there is.

## Near-duplicates — 4 items, 2 fixed and 2 refused

The condition this project sets for merging duplication is **the same
business meaning**, not the same shape. All four are similar in shape.
Two mean the same thing and two do not.

### Fixed: two identical JSON diagnostic readers (similarity 1.00)

`RuffAdapter._read` and `FortitudeAdapter._read` were byte-identical apart
from two tokens: the concept mapper, and the key holding the line number.

ruff and fortitude are both Rust linters in the same lineage and ship the
same envelope with one key renamed — ruff writes `row`, fortitude writes
`line`. Reading ruff's spelling against fortitude's payload does not fail;
it silently drops every line number. One of the two copies carried a
comment warning about exactly that.

Consolidated into `_json_diagnostics(result, *, slug, concept_of,
line_key)`. **The warning that used to be a comment beside one copy is now
a required argument on every caller**, which is the part worth noting: the
duplication was the smaller problem, and the knowledge trapped in a comment
was the larger one.

*Verified:* 185 adapter tests pass.

### Fixed: PHP and Rust member qualification (similarity 0.949, cross-file)

`_ranges_php._qualify_methods` and `_ranges_rust._qualify_impl_members`
were twenty-four lines answering one question — *which container does this
declaration belong to?* — and answering it identically: innermost span
wins, so a method inside a class nested in another class, or an `impl`
nested in a `mod`, is named for the thing it is actually a member of.

What genuinely differed was **which spans to qualify against**, which is
now the argument. Extracted to `_ranges_core.qualify_members`, beside the
shared `scan_bounded` walk both languages already used.

Rust's version additionally skipped an unnamed span (an anonymous `impl`).
That guard is kept for both: PHP class spans always carry a name, so it
costs PHP nothing, and it states the rule for whichever language arrives
next.

*Verified:* 460 language tests pass.

### Refused: `_semantic_policy._domain_type` / `_operation` (similarity 0.900)

Both validate a config entry and return a normalized dict. There the
resemblance ends:

| | `_domain_type` | `_operation` |
|---|---|---|
| required fields | `name`, `required_type` | `name` |
| error message | names both fields | names one |
| output keys | `boundary`, `symbol`, `required_type` | `capability_type`, `operation_contract` |

Merging them needs a schema parameter and a shared error path. The result
is one function whose behaviour depends on a mode argument, and two entry
contracts that a reader can no longer see by reading the function that
enforces them. **The shape is shared; the meaning is not.** Refused.

### Refused: `_pressures.dimension_pressures` / `production_pressures` (similarity 0.813)

These deliberately compute over **two different populations**, and the
separation is load-bearing rather than incidental.

`analyzability` and `testability` ask how understandable and testable the
*production* code is. Charging them for a long test body inverts the
incentive: extracting duplicated test setup into a fixture would lower the
score for improving the code.

The decisive evidence is already in the module. `_production()` exists
solely to stop the production path falling back to the combined count. Its
docstring records that an audit killed that fallback twice over, and what
it cost: deleting `production_declarations_scanned` produced a *measured*
pressure out of an `Unknown` and **raised the reported overall from 4.3 to
4.6**. ADR 001 §3 forbids exactly that.

Merging the two functions re-creates the shared path that mistake came
through. **Refused, and this is the strongest refusal in the run**: the
code already carries the record of what happens when these two are
allowed to share.

## Unpaired files — 58 items, 1 fixed and 57 refused

This is the interesting class, and the only honest way to dispose of it
was to measure. The finding asks **"does a test file exist named for this
module"**. That is a real maintainability question — can a maintainer
find the tests for this code — and it is *not* the same question as
"is this module tested". Answering the second does not automatically
answer the first, so both are reported below.

### What the suite actually covers

Branch coverage over the whole suite, 2,664 tests, gate at 92%:

| | |
|---|---|
| Total coverage | **94.46%** |
| Unpaired modules inside the coverage target | 53 |
| Unpaired paths outside it (`tools/`) | 5 |
| Unpaired modules **below 82%** | **1** |

The distribution is the answer. Of 53 measured modules, the lowest was
60.4%, the next lowest 82.9%, and the rest ran from there to 100% — six
of them at exactly 100%. One genuine gap, fifty-two well-covered modules,
and five developer scripts outside the target.

### Fixed: `_generic.py`, 60.4% → 89%

The one real gap, and it was the right one to find. `_generic` is the
module a new analyzer is added through *without writing code*: a
declaration says where the findings array is and which keys hold the
location, and one of four parsers does the rest.

That makes it the widest untrusted-input surface in the package — every
one of those parsers is handed whatever a third-party binary printed —
and a third of it was unexercised.

`tests/test_declarative_parsers.py` covers what a malformed or merely
chatty tool produces: a missing rule key, a wrong shape at the declared
path, a progress line mid-stream, an entry that is not an object. It also
pins the deliberate asymmetry between the two JSON formats — the array
parser **refuses** a wrong shape because the *declaration* is wrong,
while the line parser **skips** a non-object because the tool is merely
talking. Thirteen tests; `_generic` coverage 60.4% → 89%.

### Refused: 52 modules the suite covers, under a different convention

The rule encodes a naming convention. This repository deliberately uses
another one, and the numbers are not close:

| Test files | Named after a module | Named after a behaviour |
|---:|---:|---:|
| 219 | **4** | **215** |

`test_written_record.py`, `test_falsifier_standard.py`,
`test_anchor_disclosure.py`, `test_acquisition_trust.py` — the suite is
organised by *the behaviour under test*, not by the module that happens
to implement it. That is a deliberate choice with a stated reason, and
this project's own remediation rules give it: **"avoid tests that only
lock implementation details."** A file named for a module invites tests
about that module's shape; a file named for a behaviour survives the
refactor that moves the behaviour.

Adding 52 files named `test_scoring.py`, `test_report.py` and so on would
clear 52 work-order items and add no coverage whatsoever. That is
contorting the code to satisfy a metric, which the same rules forbid in
the same sentence.

**The detector is not wrong.** It cannot see coverage, and it is asking a
question worth asking. The answer here happens to be "we organise
differently, and here is the measurement showing the code is exercised".
Recording that answer is what stops the question being re-asked every run
— and if this repository ever *did* stop testing one of these modules,
the coverage gate at 92% is what would catch it, not the file name.

### Refused: 5 developer scripts outside the coverage target

`tools/build_catalog.py`, `tools/calibration/measure.py`,
`select_authored.py`, `measure_cohorts.py`, `measure_fix_breadth.py`.

These build the analyzer catalog and run the calibration study. They are
not shipped in the wheel, they are not on any user's path, and they are
excluded from the coverage target deliberately. A unit test named for one
of them would assert against a script whose contract is "it produced the
corpus we then pinned". The corpus *is* the artifact under version
control, and `_calibration.py` holds the provenance.

Worth stating rather than dismissing: this is the weakest of the three
refusals. A calibration script that silently changed its selection rule
would be a serious problem, and the reason it is not a coverage problem
is that its output is pinned and reviewed, not that it is unimportant.

## What this run is evidence for

Three claims, each with something in this document behind it.

1. **A deterministic gate produces a backlog a human can actually
   adjudicate.** 64 items, every one traceable to a rule, none requiring
   the reader to trust the tool's judgment over their own.
2. **The refusals are the quality signal, not the fixes.** Two items were
   correctly flagged and correctly declined. A process that cannot record
   "no, and here is why" will either contort the code or leave the item
   open forever, and both are worse than the third option.
3. **The knowledge worth preserving is usually in a comment, not in the
   duplication.** The single most valuable outcome of the ruff/fortitude
   merge was not removing sixteen duplicated lines; it was turning a
   warning that one copy happened to carry into an argument every future
   caller must supply.
