# External Quality Tool Readiness

Maintainability Agent should be easy to test against mature third-party quality platforms. The repo is prepared for the common public-repo path on SonarQube Cloud, Qlty, and Codacy.

## Local Signal First

Run this before connecting external services:

```bash
PYTHONPATH=src python3 -m pytest \
  --cov=maintainability_audit \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-fail-under=92

PYTHONPATH=src python3 -m maintainability_audit \
  --config maintainability-agent.json \
  --fail-on-gate \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md \
  --comment-output maintainability-pr-comment.md \
  --sarif-output maintainability.sarif
```

Expected local bar:

- tests pass
- coverage is at least 92%
- `coverage.xml` exists
- no hard-gate failures
- no file, function, duplicate, or risk findings

## SonarQube Cloud

Public projects can use SonarQube Cloud's free public-project analysis path. This repo includes `sonar-project.properties` with:

- `src` as source code
- `tests` as tests
- `coverage.xml` as Python coverage input
- generated/build directories excluded

After publishing the repo, connect it through SonarQube Cloud and make sure the project key and organization match the GitHub owner/repo.

Likely gate concerns:

- maintainability rating
- new-code issues
- duplicated lines
- coverage imported from `coverage.xml`
- security hotspots, if any are detected

## Qlty

Qlty provides a free open-source path through its GitHub App for qualifying public repositories. Use it after publishing by installing the app on the repo.

Likely gate concerns:

- duplication
- structure issues
- complexity
- technical debt ratio
- coverage, if configured

## Codacy

Codacy advertises free open-source/public repository scanning and coverage tracking. Use it after publishing by adding the GitHub repository in Codacy.

Likely gate concerns:

- issues
- complexity
- duplication
- coverage import
- security and dependency findings

## Current Readiness

The built-in local audit is not meant to replace these tools. Its job is to keep AI-assisted changes bounded and produce a remediation prompt before the external platforms see the code.

External tools should be treated as independent checks. If one reports a finding that Maintainability Agent does not, either:

- fix the underlying code,
- document the false positive,
- or add a deterministic adapter/rule so the local audit catches similar issues earlier.
