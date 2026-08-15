#!/usr/bin/env bash
set -euo pipefail

python3 -m pytest \
  --cov=maintainability_audit \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-fail-under=92

maintainability-agent \
  --config maintainability-agent.json \
  --fail-on-gate \
  --record-history \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md \
  --comment-output maintainability-pr-comment.md \
  --sarif-output maintainability.sarif

echo "Maintainability report written to maintainability-report.md"
echo "AI remediation prompt written to maintainability-remediation-prompt.md"
echo "PR comment body written to maintainability-pr-comment.md"
echo "Coverage XML written to coverage.xml"
echo "SARIF report written to maintainability.sarif"
echo "Scan appended to .maintainability/history.jsonl (trends and recurrence read it next run)"
