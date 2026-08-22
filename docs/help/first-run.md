# First run and questions

Call `audit_repository`. The tool checks configuration; the host does not
inspect the repository first. Unset `action` never audits.

If both the repository's `maintainability-agent.json` and the XDG user
configuration are absent, the call returns `setup_needed` with the setup
questions and `audit_ran: false` — no report, no score, no grade. A host that
can elicit asks those questions as one structured form with visible defaults:

- run the validated analyzer pool: yes;
- analyzer depth: moderate;
- license policy: permissive;
- record scan history in this repository: yes;
- economic context: skip, or low/base/high loaded labor rates;
- presentation: chat.

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

## History consent and files

Written `history.record` consent wins over terminal interactivity. With no
written answer, a CLI TTY may start a series; an existing history file remains
a standing answer and appends. Explicit per-call true or false still wins.

Chat returns report text. If the user chooses a file presentation, the host
asks for a save location at save time. Neither the MCP process nor an agent may
write or save a report file without that chosen location.
