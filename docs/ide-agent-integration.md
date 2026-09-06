# IDE and Agent Integration

This guide shows how to use maintainability-agent with editors and AI coding
agents. **Chat is the primary surface; the CLI is the automation and CI
surface.** **Chat, MCP, and an interactive CLI TTY are one setup: the same questions**
([first run](help/first-run.md)). MCP allowed-root grants are a server
boundary, not a second questionnaire.

## Primary chat workflow

Call `audit_repository`. The tool checks repository and user configuration;
the host does not inspect the tree first. Unset `action` never audits. When
both configuration tiers are absent, the result is `setup_needed` and
`audit_ran: false` — no report. Ask those questions through MCP elicitation
or the host's structured question UI (setup, root grants, history consent,
economic context, and presentation). Answering writes the answers and does
not start an audit. A configured repository returns `choice_needed` (`run` or
`reconfigure`), also without a report. `action="run"` returns the report and
bounded work order to the conversation.

If the user chooses a file presentation, the host asks for the location at save
time. It must not write or save a report file without that chosen location.
See [chat workflow help](help/README.md) for the first-run questions, analyzer
pool, and report loop.

The primary loop is:

```text
1. Call audit_repository. The tool checks configuration.
2. If the result carries setup_needed, ask those structured choices
   with disclosed defaults, then call again. Answering is not an audit.
3. If the result carries choice_needed, ask run or reconfigure.
4. action=run produces the report; show it in chat.
5. Give the bounded work order to the coding agent.
6. Re-audit after the bounded patch (action=run again).
```

## Automation / CI: CLI commands

### Run Audit

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --output maintainability-report.md
```

### Generate AI Remediation Prompt

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md
```

### Generate PR Comment Body

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --output maintainability-report.md \
  --comment-output maintainability-pr-comment.md
```

### Audit Only Changed Files

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --changed-only main...HEAD \
  --output maintainability-report.md
```

### Create / Use Baseline

```bash
# Snapshot today's findings.
maintainability-agent --config maintainability-agent.json \
  --write-baseline maintainability-baseline.json

# Fail only on findings not in the baseline.
maintainability-agent --config maintainability-agent.json \
  --baseline maintainability-baseline.json --fail-on-new
```

### Generate Agent Standards

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --init-agent-standards \
  --target generic --target codex --target claude-code \
  --target cursor --target copilot --target windsurf \
  --instructions-output-dir .
```

Generated files:

| Target | File |
|---|---|
| generic | `AI-MAINTAINABILITY.md` |
| codex | `AGENTS.md` |
| claude-code | `CLAUDE.md` |
| cursor | `.cursor/rules/maintainability.mdc` |
| copilot | `.github/copilot-instructions.md` |
| windsurf | `.windsurf/rules/maintainability.md` |

## VS Code

VS Code itself does not enforce agent behavior, but it can run the audit as a task and expose the generated prompt/report to Copilot Chat, Codex, Claude Code, or any terminal-based agent.

Add `.vscode/tasks.json` to the target repo:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Maintainability: Audit",
      "type": "shell",
      "command": "maintainability-audit --config maintainability-agent.json --output maintainability-report.md --prompt-output maintainability-remediation-prompt.md --comment-output maintainability-pr-comment.md",
      "group": "test",
      "problemMatcher": []
    },
    {
      "label": "Maintainability: Changed Only",
      "type": "shell",
      "command": "maintainability-audit --config maintainability-agent.json --changed-only main...HEAD --output maintainability-report.md --prompt-output maintainability-remediation-prompt.md",
      "group": "test",
      "problemMatcher": []
    },
    {
      "label": "Maintainability: Init Agent Standards",
      "type": "shell",
      "command": "maintainability-audit --config maintainability-agent.json --init-agent-standards --target generic --target codex --target claude-code --target cursor --target copilot --target windsurf --instructions-output-dir .",
      "group": "build",
      "problemMatcher": []
    }
  ]
}
```

Suggested VS Code workflow:

1. Run `Maintainability: Init Agent Standards`.
2. Ask the agent to follow the generated repo instruction file.
3. Make changes.
4. Run `Maintainability: Changed Only`.
5. If it fails, give the agent `maintainability-remediation-prompt.md`.

## Local MCP server: Visual Studio, VS Code and Codex

The optional MCP server removes the file handoff for Codex and the Codex VS
Code extension. It exposes all three MCP primitives over stdio:

- `audit_repository` takes an `action` argument. Unset never audits. An
  unconfigured repository returns `setup_needed` and `audit_ran: false`; a
  configured one returns `choice_needed` (`run` or `reconfigure`).
  `action="run"` runs the same production scan as the CLI and returns only
  the requested report presentation plus the bounded remediation prompt when
  requested. An explicit `config_path` bypasses both gates. Its tri-state
  `record_history` decision follows the persisted first-run consent, appends
  an existing series, or follows an explicit true or false; it can also write
  or consult a repository-scoped version-3 baseline. A top-level
  `environment_work_order` tells the host which selected tools could not run,
  how to install them and what concepts they restore.
- `get_agent_info` reports the installed version and authorized roots.
- Resources expose the applied standard, analyzer catalog and byte-identical
  Markdown report without introducing a second rendering path.
- The `maintainability-agent` prompt tells the model to call the audit tool and
  stay inside its returned remediation work order.

It is deliberately not another scanner. The MCP module calls the existing
configuration, report, renderer and prompt functions directly, so CLI and MCP
cannot acquire different scoring or finding semantics.

Install the extra:

```bash
python3 -m pip install "maintainability-agent[mcp]"
```

The package subcommand is `maintainability-agent mcp --allow-root <path>`.
IDE examples retain `maintainability-agent-mcp` because it is a direct stdio
console script and remains part of the public interface.

This is a local stdio process, not a hosted service. On the first call to a
repository with no repository or user configuration, it sends one structured
setup form through MCP elicitation. The choices have visible defaults: run the
validated analyzer pool (yes), moderate depth, permissive licensing, optional
scan-history recording (yes), low/base/high loaded labor cost or skip, and chat
presentation. The pool question explains that external analyzers are the
primary evidence and the built-in detectors always run as the fallback;
choosing no means built-ins only and a fallback-tier evidence label. Answering
does not start an audit; the call returns `choice_needed`. A decline or a
client without elicitation support receives `setup_needed` with the same
choices for the host's own question UI, and `audit_ran: false` — no report,
no score, no grade.

The local process may write exactly five artifacts: repository
`maintainability-agent.json`, the XDG user `config.json`, the XDG user
`state.json` that records the completed audit, and repository scan history at
`.maintainability/history.jsonl`, plus the repository baseline at
`.maintainability/baseline.json`. Setup writes the first three; the audit's
history rule may append the fourth, and `write_baseline` controls the fifth. It
never writes source or a report. The stored presentation is the default for
later calls; an explicit per-call `format` still wins.

For Visual Studio, put this in `%USERPROFILE%\\.mcp.json` or
`<SOLUTIONDIR>\\.mcp.json` (replace both absolute paths):

```json
{
  "servers": {
    "maintainabilityAgent": {
      "type": "stdio",
      "command": "C:\\path\\to\\venv\\Scripts\\maintainability-agent-mcp.exe",
      "args": ["--allow-root", "C:\\absolute\\path\\to\\solution"]
    }
  }
}
```

For VS Code, put this in `.vscode/mcp.json` or the user-profile MCP
configuration:

```json
{
  "servers": {
    "maintainabilityAgent": {
      "type": "stdio",
      "command": "maintainability-agent-mcp",
      "args": ["--allow-root", "${workspaceFolder}"]
    }
  }
}
```

The `command` must be on the IDE process's `PATH`; an absolute path to the
virtual-environment executable is also valid. Visual Studio enables discovered
tools from the Copilot Agent tool picker. In VS Code, use **MCP: List Servers**
to start the server and inspect its output.

Codex and its VS Code extension can instead use `~/.codex/config.toml`:

```toml
[mcp_servers.maintainability_agent]
command = "maintainability-agent-mcp"
args = ["--allow-root", "/absolute/path/to/your/repos"]
startup_timeout_sec = 20
tool_timeout_sec = 300
enabled_tools = ["audit_repository", "get_agent_info"]
default_tools_approval_mode = "auto"
```

Repeat `--allow-root` to authorize unrelated repository directories. If no
argument is supplied, the server permits only its launch directory. The
`MAINTAINABILITY_MCP_ALLOWED_ROOTS` environment variable is an alternative;
separate multiple roots with the platform path separator (`:` on macOS/Linux,
`;` on Windows, which the code honours and nobody has tested — this is
POSIX-only software). For audit-tool calls, an elicitation-capable host can instead
offer a structured **this session** (default), **always**, or **no** grant.
Session grants live only in the process; always grants persist only in the XDG
user configuration. Report resources never ask for or persist a grant.

Restart Codex, then inspect the connection with `/mcp` or `codex mcp list`.
A typical call in any client is:

```text
Use maintainability_agent.audit_repository on this workspace with
config_path maintainability-agent.json. Treat the returned remediation_prompt
as the bounded work order; do not fix unreported issues.
```

Security properties are part of the contract:

- repository roots are canonicalized before authorization, so a symlink cannot
  escape an allowed directory;
- a config file must resolve inside the repository being audited;
- `changed_only` accepts one inert git revision expression, never command-line
  options or whitespace;
- the server accepts no command strings or report output paths. It writes only
  the five disclosed artifacts: repository config, XDG user config, XDG user
  state, repository scan history and repository baseline — never a report or
  source artifact;
- `get_agent_info` advertises MCP read-only, non-destructive and closed-world,
  and is all three. `audit_repository` advertises its bounded setup/state
  writes, and is **destructive** and **open-world**: it replaces an existing
  configuration or baseline when asked to, and with `analyzers.acquire_tools`
  enabled it may fetch a missing Node tool, while analyzers run as local
  children this package does not sandbox. It said non-destructive and
  closed-world until D44; two tests locked those values, which is why the
  claim outlived three audit rounds.

This is a local integration. It needs no VPS and opens no listening socket.

## Invokable skill / slash command

This repo ships a portable skill under
[`skills/maintainability-agent/`](../skills/maintainability-agent/) so
`/maintainability-agent` is one keystroke away. Keep the installed copy in sync
— a drifted skill teaches agents a dead workflow:

```bash
maintainability-agent --install-skill        # writes ~/.claude/skills
```

Re-run after every upgrade; a differing installed copy is refused with the
list of differences (`--force-skill` to overwrite).

| Host | Install destination | Invocation |
|---|---|---|
| Codex / OpenAI | via `skills/maintainability-agent/agents/openai.yaml` | per Codex's skills convention |
| Claude Code | `skills/maintainability-agent/` → `~/.claude/skills/maintainability-agent/` (or repo `.claude/skills/`) | `/maintainability-agent` |
| GitHub Copilot (VS Code) | `skills/maintainability-agent/copilot/maintainability-agent.prompt.md` → `<repo>/.github/prompts/` | `/maintainability-agent` in Copilot Chat |

For always-on guidance instead of an invokable skill, use
`--init-agent-standards` (see [--init-agent-standards](#generate-agent-standards)).

## Per-Agent Quick Start

Every agent uses the same shape: pick a `--target`, run `--init-agent-standards`, then prompt the agent to follow the generated instruction file and use `maintainability-remediation-prompt.md` as the bounded task.

```bash
# Replace <TARGET> with one of: copilot, cursor, codex, claude-code, windsurf, generic
maintainability-agent --config maintainability-agent.json \
  --init-agent-standards --target <TARGET> --instructions-output-dir .
```

| Agent | Instruction file | Suggested in-agent prompt |
|---|---|---|
| GitHub Copilot | `.github/copilot-instructions.md` | "Follow .github/copilot-instructions.md. Fix only the findings in maintainability-remediation-prompt.md. Keep the patch small and preserve current behavior unless the report says behavior is wrong." |
| Cursor | `.cursor/rules/maintainability.mdc` | "Use the active Cursor rules. Apply only what maintainability-remediation-prompt.md asks for." |
| Codex | `AGENTS.md` | "Follow AGENTS.md. Use maintainability-report.md + maintainability-remediation-prompt.md as the source of truth. Fix the highest-severity findings only, with tests where behavior changes." |
| Claude Code | `CLAUDE.md` | "Read CLAUDE.md, maintainability-report.md, and maintainability-remediation-prompt.md. Make a small patch that resolves the hard gates. Do not refactor outside the reported scope." |
| Windsurf | `.windsurf/rules/maintainability.md` | "Use the Windsurf rules. Resolve only the items in maintainability-remediation-prompt.md." |
| Generic | `AI-MAINTAINABILITY.md` | "Follow AI-MAINTAINABILITY.md. Use maintainability-remediation-prompt.md as the bounded task. Keep the patch small, testable, and aligned with existing architecture." |

## Local CI

For repos that do not use GitHub Actions:

```bash
examples/local-ci.sh
```

Or copy the command:

```bash
maintainability-audit \
  --config maintainability-agent.json \
  --fail-on-gate \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md \
  --comment-output maintainability-pr-comment.md
```

## GitHub Actions

Use `.github/workflows/maintainability.yml` from this repo as a starting point.

Artifacts:

- `maintainability-report.md`
- `maintainability-remediation-prompt.md`
- `maintainability-pr-comment.md`

## Recommended Human Workflow

Do not let an AI agent blindly auto-fix everything.

Use this sequence:

1. Review `maintainability-report.md`.
2. Decide which hard gates or high-value findings matter.
3. Give the agent `maintainability-remediation-prompt.md`.
4. Review the patch.
5. Run native tests/lints.
6. Run the audit again.
7. Commit only bounded, explainable changes.
