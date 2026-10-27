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
agent and does not authorize a repository-wide rewrite. In chat and in the
remediation prompt the work order comes first and these figures follow it as the
evidence that aimed it; the complete Markdown or HTML report opens with them.

## The security pillar

Every audit runs `secure-code-agent`, installed beside this package, and reports
its reading as the security pillar alongside the four pillars this tool measures
itself. Its practice level and its condition are shown separately and never
averaged, and its own findings and work order are carried into the report and
the prompt.

When it is not installed, is an unsupported release, or does not produce a
trustworthy result, the pillar says it was not measured, says why, and the
environment work order gives the install command. An unmeasured pillar is never
reported as a clean one.

A pipeline that has already run it can hand the result over with
`--security-pillar PATH` instead. A `security-pillar.json` sitting in the audited
repository is not trusted on its own.

## When declaration rates are withheld

Declaration-level findings — function size, complexity, dead code — need a
parser for the language. Sixteen are parsed: Python, Java, Kotlin, C, C++,
C#, Go, Rust, PHP, Ruby, Swift, Shell, COBOL, Fortran (free-form and
fixed-form), the JS/TS family and HTML. Each has a scanner
written for it and a documented list of what it misses; see
[language support](../language-support.md).

For any other language the report **withholds** declaration rates and names the
missing parser as the reason. It does not estimate a population from patterns
that were written for other languages, because a rate divided by a wrong
population is a number a reader with the repository open would call absurd.
Those files are still measured for length, duplication and risk, and still
count toward repository size.

Adding an extension to `include_extensions` does not create a population. It
widens what is scanned, not what can be parsed.

Two consequences worth expecting rather than reporting as bugs: a repository
written mostly in an unparsed language can show few declaration findings while
being large, and its verified grade may be withheld for want of evidence. Both
are the disclosure working, not the scan failing.

## Test honesty

After Ken Pugh's [AlignThree Spectables](https://alignthree.com), the report
names three things about a test suite. None of them moves the score or a gate,
and none becomes a work-order item by itself:

- **Skipped tests.** A skip, pending or expected-failure marker in a test file
  (`@pytest.mark.skip`, `xfail`, `unittest.skip`, `it.skip`, `xit`,
  `test.todo` and the like). A suite reports these as something other than a
  failure, so a skip reads as a pass to anyone who only sees the result.
- **Tests that compute their expected value.** In Python test files, a
  comparison whose one side calls the code under test and whose other side
  does arithmetic on variables, such as `assert add(a, b) == a + b`. The test
  re-does the work and passes whatever the code returns. Arithmetic on
  literals (`2 * 60`), path joins, relations between two results and an input
  size compared with an output are not reported.
- **Spectables specifications.** Where the repository keeps `.spectable`
  files, the report reads them and names three authoring mistakes from the
  Spectables grammar: a table row with the wrong number of cells, a repeated
  scenario name in one file, and an `=Name` cell that names no `Define`.
  Unknown types are not checked, because Spectables publishes no list of its
  built-in types. Spectables itself writes and runs these specifications.

The Markdown and HTML reports show each finding by file and line, with the
credit beneath them; the remediation prompt lists them as report-only.

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
