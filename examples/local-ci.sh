#!/usr/bin/env bash
set -euo pipefail

python3 -m pytest

maintainability-agent \
  --config maintainability-agent.json \
  --fail-on-gate \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md \
  --comment-output maintainability-pr-comment.md

echo "Maintainability report written to maintainability-report.md"
echo "AI remediation prompt written to maintainability-remediation-prompt.md"
echo "PR comment body written to maintainability-pr-comment.md"
