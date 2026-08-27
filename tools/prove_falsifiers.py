"""Prove that each newly cited falsifier actually falsifies.

The register requires every closed entry to cite a test. Nothing until
now checked that the cited test *fails without the fix* — that was the
author's word, recorded in a `*Mutation:*` line and believed.

Miles Parker put the hole precisely: an agent is in control of both the
code and its test, so one that introduced a bug and adjusted the check
to cover it looks identical from outside to one that got it right. The
benign version happens constantly — a test fails, the author decides the
test was wrong, and edits it. Sometimes that is correct. Nothing
external could tell.

So this moves "revert the fix and watch the test fail" off the author's
honour and into the pipeline:

1. Find register entries added between the base commit and this one.
2. Read the tests their `*Closing tests:*` lines name.
3. In a scratch worktree, keep `tests/` from **this** commit and restore
   everything else to the **base**.
4. Run those tests. Every one must FAIL.

A test that passes there did not need the change it claims to defend,
which is what a weakened check looks like from the outside.

An import error counts as a failure, which is a weaker signal than a
real assertion failure: it proves the test does not pass at the base
without proving it measures the right thing. Entries relying on that are
reported so a reader knows which kind of proof they have.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = Path("docs/defect-register-chat-surface.md")

#: Entries may opt out with this marker and a reason on the same line.
#: A test for surface that does not exist at the base cannot fail there
#: for the right reason, and pretending otherwise is worse than saying so.
EXEMPT = "*Falsifier proof: not applicable"


def _git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(  # noqa: S603 - argv list, never a shell
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=False,
        timeout=120,
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _entries(text: str) -> dict[str, str]:
    """Register entries, keyed by identifier."""
    parts = re.split(r"\n### (D\d+) — ", text)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def _cited(body: str) -> list[str]:
    """Test names an entry offers as its falsifier."""
    blocks = re.split(r"\*Closing (?:test|tests|suite|suites):\*", body)
    if len(blocks) < 2:
        return []
    region = " ".join(re.split(r"\n\*\w+:\*", block)[0] for block in blocks[1:])
    region = re.sub(r"tests/\S+\.py", " ", region)
    return sorted(set(re.findall(r"\btest_\w+\b", region)))


def _node_ids(names: list[str], tree: Path) -> list[str]:
    """Locate each test name in the suite, as pytest node ids."""
    found: list[str] = []
    for path in sorted((tree / "tests").glob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        for name in names:
            if re.search(rf"^\s*(?:async\s+)?def {re.escape(name)}\b", source, re.M):
                found.append(f"tests/{path.name}::{name}")
    return found


def _new_entries(base: str) -> dict[str, str]:
    """Entries in this commit that the base does not have."""
    before = _entries(_git("show", f"{base}:{REGISTER.as_posix()}"))
    after = _entries((ROOT / REGISTER).read_text(encoding="utf-8"))
    return {ident: body for ident, body in after.items() if ident not in before}


def _prove(base: str, node_ids: list[str], tree: Path) -> tuple[list[str], list[str]]:
    """Run `node_ids` against the base's world. Returns (failed, passed).

    Everything goes back to the base **except the files defining the
    cited tests**, which stay as this commit wrote them. Excluding all
    of `tests/` was the first version and it could not prove any entry
    whose fix lives in test code -- D97 added population guards to four
    test files, and keeping `tests/` kept the guards, so its own closer
    passed at the base and looked unproven.

    Files the change *added* are deleted as well. `git checkout` restores
    tracked files and does not remove new ones, so a fix that adds a file
    -- `constraints/analyzers.txt`, say -- survived the revert intact.
    """
    keep = {node.split("::", 1)[0] for node in node_ids}
    _git("checkout", base, "--", ".", *(f":(exclude){path}" for path in keep), cwd=tree)
    added = [
        line for line in _git(
            "diff", "--name-only", "--diff-filter=A", base, "HEAD", cwd=tree
        ).splitlines()
        if line and line not in keep
    ]
    for path in added:
        (tree / path).unlink(missing_ok=True)
    failed, passed = [], []
    for node in node_ids:
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pytest", node, "-q", "--no-header",
             "-p", "no:randomly", "--no-cov"],
            cwd=tree, text=True, capture_output=True, check=False, timeout=600,
        )
        (failed if result.returncode != 0 else passed).append(node)
    return failed, passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="commit the fixes land on top of")
    args = parser.parse_args()
    base = _git("rev-parse", args.base).strip()

    new = _new_entries(base)
    if not new:
        print("no new register entries; nothing to prove")
        return 0

    unproven: list[str] = []
    for ident, body in sorted(new.items(), key=lambda item: int(item[0][1:])):
        if EXEMPT in body:
            print(f"{ident}: exempt — {body.split(EXEMPT, 1)[1].splitlines()[0].strip()}")
            continue
        if "Closed" not in body.split("\n", 1)[0] and "pending" in body.lower():
            print(f"{ident}: open, falsifier pending")
            continue
        names = _cited(body)
        if not names:
            unproven.append(f"{ident} cites no test")
            continue
        tree = Path(tempfile.mkdtemp(prefix="falsifier-"))
        try:
            _git("worktree", "add", "--detach", "--quiet", str(tree), "HEAD")
            node_ids = _node_ids(names, tree)
            if not node_ids:
                unproven.append(f"{ident} cites {names}, none of which resolve")
                continue
            failed, passed = _prove(base, node_ids, tree)
            for node in failed:
                print(f"{ident}: {node} fails without the change — proven")
            for node in passed:
                unproven.append(
                    f"{ident}: {node} PASSES without the change, so it does "
                    "not defend it"
                )
        finally:
            _git("worktree", "remove", "--force", str(tree))
            shutil.rmtree(tree, ignore_errors=True)

    if unproven:
        print("\nfalsifiers that do not falsify:")
        for line in unproven:
            print(f"  {line}")
        return 1
    print("\nevery newly cited falsifier fails without its change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
