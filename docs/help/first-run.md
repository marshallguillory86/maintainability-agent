# First run and questions

The chat host checks configuration before it audits. If either the user tier or
the repository's `maintainability-agent.json` exists, the run is deterministic
from that configuration and no first-run setup is reopened. If both are absent,
the host presents one structured setup form with visible defaults:

- run the validated analyzer pool: yes;
- analyzer depth: moderate;
- license policy: permissive;
- record scan history in this repository: yes;
- economic context: skip, or low/base/high loaded labor rates;
- presentation: chat.

Accepted setup answers are written to both configuration tiers and apply to the
same audit. A decline or a host without elicitation support receives
`setup_needed` with the same choices, and a later call asks again until answers
are written.

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
