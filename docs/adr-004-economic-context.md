# ADR 004: Keep economic context separate from score and grade

- Status: Accepted. Implementation progress is recorded in the
  [decision register](decisions.md).
- Date: 2026-08-11
- Scope: Repository configuration, impact scenarios, work-order priority and
  outcome validation

## Context

The same maintainability finding can be economically negligible in a stable
internal utility and material in a frequently changed, regulated or
reliability-critical service. Source structure alone does not contain labor
rates, planning horizon, verification burden, incident cost or product
criticality. Asking maintainers for that context can make assumptions explicit
and produce a more useful ordering of the bounded work order.

It does not make the maintainability score a cost predictor. User-supplied
inputs can improve relevance while still being wrong, optimistic or stale. No
outcome study has connected this project's score or findings to future labor
cost, and product intent forbids that claim.

The architecture therefore needs a hard boundary between:

- the uniform standard score, which remains comparable across repositories;
- evidence about how often affected code changes and how work flows through the
  repository; and
- a repository-specific economic scenario used only to prioritize work.

Established cost-estimation work supports the need for context, not this
project's coefficients. COCOMO II, as summarized in NASA's software cost
estimation handbook, separates product, platform, personnel and project
attributes. That is evidence against treating source structure as the whole
cost model. It is not permission to transplant a development-effort model into
finding-level maintenance estimates.

## Options

### A. Do not estimate economic impact

Keep the work order ordered only by finding severity and structural pressure.

This avoids speculative numbers, but treats a cold utility and a critical
hotspot as economically equivalent when the available context says otherwise.

### B. Convert maintainability scores directly into money

Fit or choose one global multiplier and publish expected cost or savings.

This is easy to communicate and unsupported. It hides the variables that
actually drive effort and would turn a standard into a prediction without an
outcome study.

### C. Add transparent, configured scenario ranges beside the score

Derive exposure data from the repository where possible, ask for irreducible
business context, and calculate low/base/high scenarios whose assumptions and
provenance are visible.

This improves prioritization without claiming validated prediction.

### D. Train a cross-organization predictive model immediately

Collect repository and labor data and fit one model across organizations.

This may become a later study. It is premature before organization-specific
measurements, task definitions and held-out validation exist.

## Proposed decision

Choose option C. Treat option D as a research path that requires a separate
empirical decision and pre-registered validation.

Economic context produces an optional `economic_impact` section and a priority
ordering for work items. It never changes aspects, categories, overall, grade,
`evidence_status` or `verified_grade`. Reports without economic configuration
remain fully valid maintainability reports.

The output vocabulary is **scenario**, **estimate**, **exposure** and
**assumption**. The words **prediction**, **saving**, **avoided cost** and
**return on investment** require observed or held-out outcome evidence and must
not describe the initial feature.

## v1 slice (shipped 2026-08-15)

The first increment is option C, narrowed so it can ship without a survey
and without changing the uniform score.

**Presentation is split.** The 0–5 score and `verified_grade` never mention
money. A separate `economic_impact` block prints a low/base/high **scenario**
range and the assumptions that produced it. The work order **reorders** by
exposure; standard risk×effort severity remains on the report so both sorts
are visible. Per-finding dollar lines are not in v1 — the $ range is a
rollup over the current work-order set.

**Ask once, then persist.** The labor gate is part of the **same**
first-run question set on chat, MCP, and a CLI TTY
([first run](help/first-run.md)). Non-TTY / CI never asks. Answers are
written into `maintainability-agent.json` under `economic_context`.
Later runs read the file. For one run, flags and environment variables
override the file. `prompt_when_interactive: false` keeps even an
interactive run silent (the same switch as the rest of first-run
setup).

**Required for any $ block:** loaded engineering cost per hour as
low / base / high, plus a currency **label** (default `USD`; no exchange
fetch). Planning horizon defaults to **12 months** if omitted.

**Optional asks (Enter skips; missing widens or drops that term):**
reliability tier (`internal` / `customer` / `regulated`); typical review
minutes per change; representative incident or downtime cost.

**Do not ask in v1.** Derive exposure from what the scan already has:
recurrence (a finding that cleared and returned) and hotspot churn.
Do not ask for PR lead time, deploy duration, incident linkage, or team
tenure. Those stay later adapters.

**Environment overrides** (one run; do not persist unless the TTY ask
writes the file): `MAINTAINABILITY_LABOR_LOW`, `MAINTAINABILITY_LABOR_BASE`,
`MAINTAINABILITY_LABOR_HIGH`, and optionally `MAINTAINABILITY_CURRENCY`,
`MAINTAINABILITY_HORIZON_MONTHS`.

**Arithmetic** stays the inspectable product of
`expected affected changes per year × incremental hours per change ×
loaded rate`, over the horizon. Incremental hours are a visible
configured or defaulted range, not a COCOMO coefficient. Operational
incident $ is a separate optional term, never folded into the rate.

This slice does not license predictive language. Validation ladder stages
2–4 remain studies.

## Design

### Inputs

Prefer measurements over questions. Derive these when the repository or an
explicit local adapter contains them:

- change frequency and hotspot concentration;
- contributor concentration and continuity;
- pull-request lead time, review cycles and rework;
- release frequency and test or deployment duration; and
- incident-linked changes, when a configured local source establishes them.

Ask users only for context the repository cannot establish:

- loaded engineering cost as a low/base/high range;
- planning horizon and expected supported lifespan;
- reliability or product-criticality tier;
- regulatory, review and verification burden;
- representative incident or downtime cost, when relevant;
- team experience or continuity not observable from repository history; and
- material human or agent execution costs outside source control.

Every input carries one state and provenance compatible with ADR 001's evidence
model: measured, configured, defaulted or unknown. Defaults are visible and
cannot make an unknown scenario appear precise. Sensitive values remain local;
the feature adds no network requirement.

An illustrative configuration is:

```yaml
economic_context:
  version: 1
  currency: USD
  planning_horizon_months: 12
  loaded_engineering_cost_per_hour:
    low: 90
    base: 140
    high: 210
  reliability_tier: business_critical
  typical_review_minutes_per_change: 30
```

Currency is a label, not a conversion service. The deterministic offline path
does not fetch exchange rates.

### Scenario model

The first model must be inspectable rather than statistically impressive. A
finding-level labor exposure can begin with:

```text
annual labor exposure
  = expected affected changes per year
  x incremental effort per affected change
  x loaded labor cost
```

Operational risk, incident cost and cost of delay are separate terms with
separate assumptions; they are not folded invisibly into an effort multiplier.
Low/base/high input combinations produce a range, and sensitivity output names
the assumptions responsible for most of its width.

The hard problem is `incremental effort per affected change`. The first version
may use a visible configured range or an organization-specific historical
baseline. It must not import coefficients from a development-cost model and
present them as validated maintenance costs.

### Report boundary

```text
maintainability finding ----------------------------+
                                                     |
repository-derived exposure --+                     |
                               +-> scenario engine -> economic_impact
configured business context ---+                     |
                                                     v
                                          work-order priority

standard evidence -> scoring -> grade       (no dependency upward)
```

The report preserves the original finding severity and score-derived ordering
inputs so a consumer can reproduce both the standard order and the contextual
order. Presentation must label configured and experimental values where they
are shown.

### Validation ladder

1. **Scenario correctness:** property-test arithmetic, ranges, missing states,
   units and provenance over the production model.
2. **Organization-specific calibration:** use completed work items and pull
   requests to relate task type, changed area, review time, rework and incident
   handling to observed effort.
3. **Held-out validation:** freeze the model before estimating later work and
   compare estimates with actual effort using pre-registered error measures.
4. **Cross-organization validation:** only after task definitions and inputs
   are comparable may the project test whether a transferable model exists.

Stages 1 and configured scenarios license deterministic calculations. They do
not license predictive language. Stages 2 through 4 are empirical studies and
belong in `studies.md` with pinned inputs and stated limitations.

## Consequences

- Work orders can be prioritized using product and engineering context rather
  than structural severity alone.
- Organizations can calibrate to their own process before attempting a broad
  cost model.
- Configuration and telemetry integration increase setup cost. The CLI should
  therefore make the feature optional and useful with partial information.
- Monetary output creates false-precision risk. Ranges, provenance,
  sensitivity and explicit unknowns are required product behavior, not display
  polish.
- Standard scores remain comparable because labor rates and business
  criticality never enter the rubric.

## Invariants

1. Changing any economic-context input cannot change a finding, aspect,
   category, overall, grade, `evidence_status` or `verified_grade`.
2. Reports without economic context are valid and retain their existing
   deterministic output except for explicitly versioned optional fields.
3. Every displayed economic number identifies its currency, time horizon,
   range and input provenance.
4. Unknown required inputs widen or suppress a scenario; they never receive a
   hidden favorable value.
5. Low, base and high outputs are ordered for every accepted configuration.
6. Identical findings, repository measurements, configuration and model
   version produce byte-identical scenarios without network access.
7. A configured scenario is never labeled a prediction, observed saving or
   return on investment.
8. Economic priority cannot suppress a hard finding or erase the standard
   severity and ordering evidence from the report.

## References

- [NASA Software Cost Estimation Handbook](https://swehb.nasa.gov/download/attachments/16450436/Handbook_for_Software_Cost_Estimation.pdf?api=v2)
- [University of Maryland: An Industrial Case Study of Software Maintenance](https://www.cs.umd.edu/projects/SoftEng/ESEG/papers/ICSE96.html)
