# IDE and Agent Integration

This guide shows how to use Maintainability Audit CI with editors and AI coding agents.

The core loop is:

```text
1. Generate standards for the agent before code is written.
2. Let the human/agent make a small patch.
3. Run the audit locally or in CI.
4. Use the generated remediation prompt if the patch drifts.
```

## First-Class Commands

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
Code extension. It exposes two read-only tools over stdio:

- `audit_repository` runs the same production scan as the CLI and returns the
  structured report, rendered Markdown and bounded remediation prompt together.
- `get_agent_info` reports the installed version and authorized roots.

It is deliberately not another scanner. The MCP module calls the existing
configuration, report, renderer and prompt functions directly, so CLI and MCP
cannot acquire different scoring or finding semantics.

Install the extra:

```bash
python3 -m pip install "maintainability-agent[mcp]"
```

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
`;` on Windows).

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
- the server accepts no command strings or output paths and writes no report,
  baseline or source artifact;
- both tools advertise MCP read-only, non-destructive and closed-world hints.

This is a local integration. It needs no VPS and opens no listening socket.

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
