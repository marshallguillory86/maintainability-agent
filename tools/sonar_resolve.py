"""Resolve a SonarCloud issue, with the reason recorded before the verdict.

Two findings had to be dismissed by hand in the dashboard, and both times
the decision left no trace anywhere a reader of this repository would
find it. That is the shape this project treats as a defect when other
people do it — `_conformance.SUPPRESSION_MARKERS` counts `NOSONAR` as
silencing a finding — so the same act needs the same visibility.

Running it here buys three things a dashboard click does not:

* the justification is **required**, not optional, and is posted *before*
  the transition, so an issue is never resolved with no reason attached;
* the whole act lands in a CI run, with who dispatched it and what they
  wrote, rather than in a SaaS audit log nobody reads;
* the token stays a repository secret and is never pasted anywhere.

It refuses more than it does. A transition it does not recognise, a
comment shorter than a sentence, or an issue that is already resolved all
stop before anything is sent — a resolution recorded twice reads as two
decisions when it was one.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HOST = "https://sonarcloud.io"

#: `falsepositive` denies the finding; `wontfix`/`accept` keeps it true and
#: declines to act. They are different claims and the comment has to match,
#: which is why this does not offer a default.
TRANSITIONS = ("falsepositive", "wontfix", "accept")

#: Long enough to be a reason rather than a shrug. "n/a" and "false
#: positive" are the comments that make a register entry worthless later.
MIN_COMMENT = 40


def _call(path: str, token: str, payload: dict[str, str]) -> dict:
    request = urllib.request.Request(
        f"{HOST}{path}",
        data=urllib.parse.urlencode(payload).encode(),
        method="POST",
    )
    # SonarCloud takes the token as the basic-auth *username*, empty password.
    import base64

    basic = base64.b64encode(f"{token}:".encode()).decode()
    request.add_header("Authorization", f"Basic {basic}")
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed host
        body = response.read().decode()
    return json.loads(body) if body.strip() else {}


def _current(issue: str, token: str) -> dict:
    query = urllib.parse.urlencode({"issues": issue, "ps": "1"})
    request = urllib.request.Request(f"{HOST}/api/issues/search?{query}")
    import base64

    basic = base64.b64encode(f"{token}:".encode()).decode()
    request.add_header("Authorization", f"Basic {basic}")
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed host
        found = json.loads(response.read().decode()).get("issues") or []
    if not found:
        raise SystemExit(f"no issue {issue}; check the key and the project")
    return found[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", required=True, help="SonarCloud issue key.")
    parser.add_argument("--transition", required=True, choices=TRANSITIONS)
    parser.add_argument(
        "--comment", required=True,
        help="Why. Posted before the transition, and never optional.",
    )
    args = parser.parse_args(argv)

    token = os.environ.get("SONAR_TOKEN", "")
    if not token:
        raise SystemExit("SONAR_TOKEN is not set; this runs in CI where it is a secret")
    if len(args.comment.strip()) < MIN_COMMENT:
        raise SystemExit(
            f"the comment is {len(args.comment.strip())} characters. A "
            "resolution nobody can reconstruct later is the thing this "
            "script exists to prevent."
        )

    issue = _current(args.issue, token)
    if issue.get("resolution"):
        print(f"{args.issue} is already {issue['resolution']}; nothing sent.")
        return 0
    print(f"{args.issue}: {issue.get('rule')} at "
          f"{issue.get('component', '').split(':')[-1]}:{issue.get('line')}")

    try:
        _call("/api/issues/add_comment", token,
              {"issue": args.issue, "text": args.comment})
        result = _call("/api/issues/do_transition", token,
                       {"issue": args.issue, "transition": args.transition})
    except urllib.error.HTTPError as failure:
        detail = failure.read().decode()[:300]
        raise SystemExit(
            f"SonarCloud refused ({failure.code}): {detail}\n"
            "A 403 here means the token can run analysis but not administer "
            "issues, which is a different permission."
        ) from failure

    resolved = (result.get("issue") or {}).get("resolution")
    print(f"resolution: {resolved or '(none reported)'}")
    return 0 if resolved else 1


if __name__ == "__main__":
    sys.exit(main())
