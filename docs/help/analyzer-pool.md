# What the analyzer pool runs

The validated analyzer pool is the primary evidence source. Built-in detectors
always run as the fallback for concepts the selected analyzers cannot measure.
The report names the evidence tier used for its estimate; missing evidence is
not a clean result.

Configuration selects tools by concern, depth, license policy, language, and
explicit allow/deny rules. `analyzers.run` controls whether the pool runs;
explicit per-call choices override it. Tool acquisition remains opt-in. The
agent never installs an analyzer for the user.

Every selected tool records an outcome and version or an unavailable reason.
When a selected analyzer cannot run, the top-level `environment_work_order`
names the tool, an install command, and the concepts installation would
restore. The chat host surfaces that order rather than hiding it inside a JSON
report body.

Selection filters the catalog by the configured policy. Source-read and
artifact-read adapters compose in one report without manufacturing
agreement across unlike findings
(`tests/test_d15_composition.py`; D15 in the
[chat-surface defect register](../defect-register-chat-surface.md)).
