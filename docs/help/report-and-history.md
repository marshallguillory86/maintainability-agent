# Reading the report and its history

The report and bounded work order come from one deterministic report dictionary
regardless of whether the host shows chat Markdown, returns JSON, or saves a
chosen Markdown or HTML file.

## Headline

- **Maintainability estimate:** the point selected by the published rubric from
  measured evidence.
- **Maintainability range:** the uncertainty interval. Missing evidence and
  disagreement can widen it; they are not converted to zero findings.
- **Verified grade:** a letter only when the evidence floor supports one.
- **Evidence source:** which analyzer or built-in fallback tier supplied the
  scored dimensions.

Findings remain named evidence. The work order selects a bounded subset for the
agent and does not authorize a repository-wide rewrite.

## History, recurrence, and baselines

Scan history is an input to the next report. Comparable records form a trend;
a finding that clears and later returns contributes recurrence evidence. When
repeated targeted advice fails and the finding returns, the report can escalate
it to a design-review candidate instead of asking for the same patch again.

A version-3 baseline records structured finding identities. Later audits report
the exclusive set of new findings; git-attested renames are not new findings.
Baselines do not suppress hard gates.

## Economic context

Optional low/base/high loaded labor inputs attach an economic scenario range to
the work order. It is not a prediction, saving, avoided cost, or ROI claim, and
changing it cannot change the maintainability estimate, range, or grade.
