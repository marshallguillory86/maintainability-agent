# First run and questions

**Chat, MCP, and an interactive CLI TTY are one setup: the same questions.**
MCP is the chat transport, not a third questionnaire.
There is not a CLI process, a chat process, and an MCP process. The
list below is the set. A surface that asks a subset is a bug.

CI, a non-TTY, and an explicit `--config` never ask. That is not a
different questionnaire; there is no operator. MCP allowed-root grants
(this session / always / no) are a server boundary, not these questions.

Call `audit_repository` on the chat path, or run the CLI at a TTY with
no config. The tool checks configuration; the host does not inspect the
repository first. Unset MCP `action` never audits.

If both the repository's `maintainability-agent.json` and the XDG user
configuration are absent, the interactive surface asks the setup
questions and does not audit — no report, no score, no grade. On MCP
that is `setup_needed` with `audit_ran: false`. A host that can elicit
asks those fields as one structured form with visible defaults:

- run the validated analyzer pool: yes;
- analyzer depth: moderate;
- license policy: permissive;
- economic context: skip;
- run this repository's test suite for coverage — **this executes the tree**: no;
- presentation: chat, markdown or html — default chat;
- record scan history in this repository: yes.

**The labor rates are a second question set, asked only if you include the
economic scenario.** Answer `include` and the next call asks three more:

- loaded labor rate, lower bound — default 90 per hour;
- loaded labor rate, central estimate — default 140 per hour;
- loaded labor rate, upper bound — default 210 per hour.

Answer `skip` — the default — and you are never asked. Until this was staged, all three were on the first form
regardless, so the common path answered three money questions for something
it had just declined.

They are refused if they do not satisfy `0 < low <= base <= high`. That check
used to live in scoring, so an impossible set was accepted here, written to
both tiers, and surfaced two calls later as an error about a file the person
had already left behind.

**The test command is a second question set, asked only if you opt the suite
in.** Answer `yes` to running the suite and the next call asks one more:

- the exact test command to run, e.g. `pytest -q` or `npm test`.

**The question arrives pre-filled where the repository answers it.** Since
2.5.0 the tool reads the tree's build manifests — `Package.swift`,
`fpm.toml`, `Cargo.toml`, `go.mod`, `CMakeLists.txt`, `pom.xml`,
`build.gradle`, a `.sln`, `package.json`, or a declared `[tool.pytest]`
section — and offers the command they imply, naming the file it read.
Accept it, edit it, or replace it; whatever you submit is what gets stored.
It is only ever a default. The `require_test_command` hard gate asks
whether *you* documented a command, so a suggestion the tool made and you
never answered does not satisfy it.

An Xcode project with no `Package.swift` is left blank on purpose: bare
`xcodebuild test` needs a `-scheme` and usually a `-destination`, and
neither can be read off the tree, so there is no command to offer that
would run.

Clearing the line still cancels the opt-in, exactly as a blank answer
always did.

This is the one exception to the tool never running the audited tree
(Decision 9, amended 2026-08-31): it executes only the command you name, only
because you opted in, and only for this repository. A blank answer cancels the
opt-in. The command is stored in `expected_commands.test`; its line coverage,
if the run produces a `coverage.xml`, scores `test_effectiveness` as
`coverage / 20`, and the aspect is NotApplicable on every run that does not opt
in. Answer `no` — the default — and neither this question nor any execution
happens.

Accepted answers are written to both configuration tiers. Answering does not
start an audit, including when the host elicited the questions on that call.
The next unset call on the now-configured repository returns `choice_needed`
with options `run` and `reconfigure`, also `audit_ran: false`.
`action="run"` audits. `action="reconfigure"` reopens the setup questions on a
repository that already has answers.

A decline or a host without elicitation support receives `setup_needed` with
the same choices and does not receive a report; a later call asks again until
answers are written. An explicit `config_path` bypasses both gates so
automation is not blocked. The MCP tool passes unset `action` because a person
is on the other end. The plain `audit_repository` Python function defaults
`action="run"` for the CLI, the report resource, and scripted callers that
have already decided.

## Repository grants

An audit-tool call outside the server's allowed roots uses one structured grant
question when the host supports it: **this session** (the default), **always**,
or **no**. A session grant lasts only for the running process. Always writes the
root to the user configuration, never the repository configuration. No—or a
host without elicitation—returns the boundary error with the `--allow-root` and
`MAINTAINABILITY_MCP_ALLOWED_ROOTS` remedies. Report-resource reads never ask
for or persist a grant.
How that boundary text survives MCP is the entry-layer transport rule in
[../architecture.md](../architecture.md#the-rules-and-why-each-exists): only
the transport declares the named anticipated refusals that may carry their text
to the caller.

## History consent and files

Written `history.record` consent wins over terminal interactivity. With no
written answer, a CLI TTY may start a series; an existing history file remains
a standing answer and appends. Explicit per-call true or false still wins.

Chat returns report text. If the user chooses a file presentation, the host
asks for a save location at save time. Neither the MCP process nor an agent may
write or save a report file without that chosen location.
