# Analyzer Adapters

Maintainability Agent should not replace mature analyzers. It should collect their output and turn it into reviewable reports and bounded AI remediation prompts.

## Supported Now

### SARIF Input

```bash
maintainability-agent \
  --sarif-input semgrep.sarif \
  --output maintainability-report.md
```

External SARIF findings appear in the Markdown report under `External Findings`.

### SARIF Output

```bash
maintainability-agent \
  --sarif-output maintainability.sarif
```

The SARIF file can be uploaded to GitHub code scanning.

### Native analyzer pool

Fifteen adapters ship in the optional analyzer pool: cohesion, complexipy,
eslint, flake8, fortitude, interrogate, jscpd, lizard, multimetric, mypy,
pydocstyle, pylint, radon, ruff, and vulture. See [analyzer pool](analyzer-pool.md)
for selection and coverage.

## Which analyzer covers which language

| Language | Built-in scanner | External analyzer |
|---|---|---|
| Python | `ast`, exact | ruff, radon, mypy, vulture, complexipy, interrogate, pydocstyle, pylint, cohesion |
| Java | dedicated scanner | lizard, PMD, Checkstyle, SpotBugs |
| C / C++ / C# | dedicated scanners | lizard, multimetric |
| **Fortran** (free- and fixed-form) | dedicated scanner | **fortitude** — 100+ rules; **lizard** — complexity, NLOC, params |
| **COBOL** | dedicated scanner | **none** — no offline analyzer in the catalog reads it |
| JS / TS / JSX / TSX | brace scanner | ESLint, lizard, jscpd |

Fortran reached parity in 1.6.0: lizard had read it for years behind a
stale catalog row, so it came out `not-applicable` and never ran. A lint fails
the build if a parsed language has no analyzer measuring complexity — **COBOL is
the one disclosed exemption**, because the tooling that reads it is licensed and
host-resident, so its external tier is empty and the report says so.

**External analyzer adapters (opt-in pool)** — this is how coverage extends
beyond the built-in set. When you enable the analyzer pool, the tool shells out
to mature analyzers and folds their output in through per-tool
[adapters](adapters.md): **lizard** (cyclomatic complexity across ~a dozen
languages), **jscpd** (cross-language duplication), **ESLint** (JS/TS),
**PMD** / **SpotBugs** (JVM), and others in the catalog. These run only when
selected *and* installed (acquisition is opt-in and off by default), and where
they measured a full concept set they become the *primary* evidence, with the
built-ins as the fallback.

## Planned Native Adapters

- Semgrep JSON
- pytest / coverage summaries
- SonarQube API export

The adapter rule is simple: ingest tool output, preserve provenance, and avoid pretending every analyzer has the same semantics.
