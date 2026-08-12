# FOSS code-quality tool inventory

Every free tool this agent could run to gather maintainability evidence, what each one actually produces, and whether it has been **proven to run** rather than merely listed.

This exists because the agent currently reimplements a fraction of these in `src/` — its own complexity approximation, its own clone detector, its own dead-code pass — while the README says *"pair this tool with mature analyzers … don't replace them."* The implementation contradicts the principle. The inventory below is the first step to inverting that: the FOSS tools produce the evidence, and the rubric becomes a metric computed over their output.

**Scope: maintainability and code quality only.** Security scanning belongs to `secure-code-agent` and is deliberately absent here. Duplicating it would be the same replace-don't-pair mistake in a different direction.

## Proven, on this machine, in this session

Every row below was installed and run against real code, and produced machine-readable output. The "found" column is an actual result, not a capability claim.

| Tool | Languages | Produces | Output | Found when run |
|---|---|---|---|---|
| **lizard** | C, C++, C#, Java, JavaScript, TypeScript, Objective-C, Swift, Python, Ruby, PHP, Scala, Go, Lua, Rust, **Fortran**, Kotlin, Solidity, Erlang, Zig, Perl, GDScript, TTCN-3 | Cyclomatic complexity, NLOC, parameter count, token count, per function | CSV, XML | 205 functions in `src/`; worst CCN 14. Across seven languages simultaneously: C 11, C# 11, Java 11, Go 10, Rust 10, C++ 7, Fortran 6 |
| **jscpd** | ~150 formats incl. all of the above | Copy-paste clones, duplication % | JSON, SARIF | Detected a 30-line Java clone across two files (27.9% duplication); correctly identified c, csharp, fortran, go, java, rust in one pass |
| **radon** | Python | **Maintainability Index** (the academic MI formula), cyclomatic complexity, Halstead, raw LOC | JSON | 34 files ranked; lowest MI 42.23 (`cli.py`); 220 functions measured |
| **ruff** | Python | ~800 lint rules incl. complexity (C901), comprehensions, unused code, naming | JSON, SARIF | Already the repo's linter |
| **pylint** | Python | Design smells — too many arguments, locals, instance attributes, branches; duplicate-code checker | JSON | 107 messages: too-many-arguments ×5, too-many-instance-attributes ×2, too-many-locals ×2 |
| **vulture** | Python | Dead code with a confidence score | text | 0 at ≥80% confidence on `src/` |
| **eslint** | JavaScript, TypeScript (via typescript-eslint) | `complexity`, `max-depth`, `max-params`, `max-lines-per-function`, plus the rule ecosystem | JSON, SARIF | complexity 11, max-depth 4 and 5, max-params 5 on a synthetic file |
| **xenon** | Python | Pass/fail thresholds over radon — a gate, not a metric | exit code | installed, threshold-only |

**The headline is `lizard`.** One binary covers C, C++, C#, Java, Fortran, Go, Rust, Kotlin, Swift, PHP, Ruby, Scala and more with no per-language configuration, producing the same four metrics everywhere. Combined with `jscpd` for duplication, two tools give comparable maintainability evidence across essentially every language someone might point an AI at.

## Worth adding, not yet proven here

Listed with what they add beyond the proven set. Nothing here should be described as working until it has been run.

| Tool | Languages | Adds |
|---|---|---|
| **PMD / CPD** | Java, C#, C++, Go, Kotlin, Swift, JS, PHP, Ruby, Fortran… | Design rules (god class, cyclomatic, coupling) and a mature copy-paste detector; the standard Java answer |
| **Checkstyle** | Java | Style and structural conventions; complements PMD rather than repeating it |
| **SpotBugs** | Java bytecode | Bug patterns the source-level tools miss |
| **detekt** | Kotlin | The best-in-class Kotlin maintainability linter, complexity and smell rules |
| **golangci-lint** | Go | Meta-runner: gocyclo, gocognit, dupl, funlen, deadcode in one pass |
| **clippy** | Rust | The canonical Rust lint set, many maintainability rules |
| **cppcheck** / **clang-tidy** | C, C++ | Static analysis and modernisation/readability checks |
| **Roslyn analyzers** / **SonarAnalyzer.CSharp** (free tier) | C# | Complexity and smell rules native to the toolchain |
| **rubocop**, **reek**, **flog** | Ruby | Style, smells, complexity |
| **phpstan**, **phpmd** | PHP | Level-based static analysis and mess detection |
| **swiftlint** | Swift | Style and complexity |
| **fortran-linter**, **fprettify** | Fortran | Thin; lizard carries most of the Fortran signal |
| **knip**, **ts-prune** | TS/JS | Dead exports — needs project config, failed a no-config run here |
| **madge**, **dependency-cruiser** | JS/TS | Circular dependencies and architecture rules |
| **mypy**, **pyright** | Python | Type coverage as a maintainability signal |
| **scc**, **cloc**, **tokei** | Everything | LOC and a rough complexity estimate; useful as denominators |

## What this changes about the agent

Three things follow from the table, and they are the actual work:

**Availability must be reported, never assumed.** A tool that is not installed is not a clean result. `secure-code-agent` already does this — it prints `scanners run:` and `unavailable:` — and this agent does not, which is precisely why a repository with one function scored 5.0/A+: six shallow built-in checks found nothing, and the rubric read that as excellence. Coverage is the missing concept.

**Installation has to be explicit and layered.** Python tools install with the package; Node tools need `npx`; Java, Go, Rust and C tools are per-ecosystem binaries. The honest design ships a small proven core (lizard, jscpd, ruff, radon), detects what else is present, and reports the rest as unavailable rather than pretending to have looked.

**The rubric becomes a metric over their findings**, not over homegrown detectors. That is a scoring-model change and needs its own decision record before any code moves.

## Method

Everything in the proven table was installed into this repository's virtualenv or run through `npx`, executed against either `src/` or a synthetic multi-language fixture, and its machine-readable output parsed. The multi-language fixture deliberately contained the same tangled function written in seven languages so the complexity numbers could be compared directly.
