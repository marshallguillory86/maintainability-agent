#!/usr/bin/env python3
"""Keep one GitHub issue per weekly check: open on failure, close on recovery.

A scheduled job that fails leaves a red run in a list, and a list nobody
reads is no signal at all. The analyzer drift job had gone red for any
upstream release for weeks at a time; its own comment named the failure —
*"a pipeline that fails on something advisory teaches people to ignore it."*
This turns each failing weekly check into one standing issue, updated rather
than duplicated on every repeat, and closed when the check passes again.

It talks to the GitHub REST API over one HTTPS connection to a fixed host,
with the workflow's own token. Nothing is executed, so there is no shell and
no subprocess to review.

Usage (in a workflow step, with GITHUB_TOKEN and GITHUB_REPOSITORY set):
    python3 tools/scheduled_issue.py --title "Weekly check: ..." \\
        --failed true|false [--body-file path]
"""

from __future__ import annotations

import http.client
import json
import os
import sys
from pathlib import Path

HOST = "api.github.com"


def plan(existing: int | None, failed: bool) -> str:
    """What to do: `create`, `update`, `close` or `none`."""
    if failed:
        return "update" if existing else "create"
    return "close" if existing else "none"


def _request(method: str, path: str, token: str, body: dict | None = None):
    connection = http.client.HTTPSConnection(HOST, timeout=30)
    try:
        connection.request(method, path, body=json.dumps(body) if body is not None else None, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "User-Agent": "maintainability-agent-scheduled-issue", "Content-Type": "application/json"})
        response = connection.getresponse()
        data = response.read()
        if response.status >= 300:
            raise RuntimeError(f"{method} {path} -> {response.status}: {data[:200]!r}")
        return json.loads(data) if data else None
    finally:
        connection.close()


def _open_issue(repo: str, token: str, title: str) -> int | None:
    for issue in _request("GET", f"/repos/{repo}/issues?state=open&per_page=100", token) or []:
        if issue.get("title") == title and "pull_request" not in issue:
            return issue["number"]
    return None


def main(argv: list[str]) -> int:
    args = dict(zip(argv[1::2], argv[2::2], strict=False))
    title, failed = args["--title"], args.get("--failed", "false").lower() == "true"
    body = Path(args["--body-file"]).read_text(encoding="utf-8") if "--body-file" in args else ""
    token, repo = os.environ["GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"]
    run = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"

    existing = _open_issue(repo, token, title)
    action = plan(existing, failed)
    if action == "create":
        issue = _request("POST", f"/repos/{repo}/issues", token, {"title": title, "body": f"{body}\n\nRun: {run}"})
        print(f"opened #{issue['number']}")
    elif action == "update":
        _request("POST", f"/repos/{repo}/issues/{existing}/comments", token, {"body": f"Still failing.\n\n{body}\n\nRun: {run}"})
        print(f"updated #{existing}")
    elif action == "close":
        _request("POST", f"/repos/{repo}/issues/{existing}/comments", token, {"body": f"Passing again. Run: {run}"})
        _request("PATCH", f"/repos/{repo}/issues/{existing}", token, {"state": "closed"})
        print(f"closed #{existing}")
    else:
        print("passing, nothing open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
