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

The same revert proof also covers the second falsifier convention: the
population-derived ``tests/*_class.py`` files. ``test_falsifier_standard``
already enforces that each asserts a non-empty population, but nothing
enforced that one fails without its change — so a plan's worth of class
falsifiers once merged while this gate, reading only the register, proved
nothing. Every ``*_class.py`` file the change *adds* is now revert-proven
too. Only added files: a modified one may defend a fix older than this
base, which would revert to a tree where it legitimately passes.

An import error counts as a failure, which is a weaker signal than a
real assertion failure: it proves the test does not pass at the base
without proving it measures the right thing. Entries relying on that are
reported so a reader knows which kind of proof they have.
"""

from __future__ import annotations

import argparse
import os
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

#: The first entry this tool holds to its standard. Entries below it
#: were closed before the tool existed and were never written against
#: it, so proving them retroactively would produce a wall of failures
#: that says more about when the control arrived than about the work.
#: The same cutoff shape as the `*Roles:*` (D90) and `*Mutation:*` (D97)
#: conventions, and for the same reason: a rule announced today does not
#: get to be evidence about yesterday.
PROVE_FROM = 97


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
    # The reverted tree must be the tree the tests *import*, and it was
    # not. `pip install -e .` puts the checkout's own `src` on the path,
    # so a test run inside this worktree imported the package from the
    # original checkout — the code at HEAD, never the base. Reverting the
    # files on disk changed what the tests could *read* and nothing about
    # what they could *call*, which is why document falsifiers proved
    # correctly here for months while every behaviour falsifier passed
    # vacuously.
    #
    # The worktree's own source goes first and the parent's path follows,
    # rather than replacing it: naming only the worktree left the child
    # unable to import pytest itself on any interpreter whose pytest
    # lives outside the default path, and a child that cannot start is
    # the case immediately below.
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            [str(tree / "src"), *(entry for entry in sys.path if entry)]
        ),
    }
    failed, passed = [], []
    for node in node_ids:
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pytest", node, "-q", "--no-header",
             "-p", "no:randomly", "--no-cov"],
            cwd=tree, text=True, capture_output=True, check=False, timeout=600,
            env=environment,
        )
        _refuse_a_run_that_never_happened(node, result)
        (failed if result.returncode != 0 else passed).append(node)
    return failed, passed


def _pytest_reached_a_verdict(result: subprocess.CompletedProcess) -> bool:
    """Whether pytest ran at all, as opposed to never starting.

    `_prove` read every non-zero exit as "the test failed at the base",
    which it treats as proof. A child that could not start therefore
    counted as a successful proof, and an environment broken in any way
    reported that every falsifier falsified. Found while proving the
    shadowing fix above: the mutation that should have failed its guard
    passed instead, because the child was exiting 1 with `No module named
    pytest` and the tool was reading that as evidence.

    The line is drawn at output, not at the exit code. A collection error
    — the base lacking the module a new test imports — is pytest
    reporting on the tree, and this file's own docstring already counts
    that as the weaker signal it is. An interpreter that never reached
    pytest writes nothing to stdout at all, and that is not evidence
    about anything.
    """
    return bool(result.stdout.strip())


def _refuse_a_run_that_never_happened(node: str, result: subprocess.CompletedProcess) -> None:
    """Raise when the child never got as far as running pytest.

    A proof that cannot tell a failing test from a missing interpreter is
    worth less than no proof, because it is believed.
    """
    if result.returncode == 0 or _pytest_reached_a_verdict(result):
        return
    detail = (result.stderr or "").strip().splitlines()
    raise RuntimeError(
        f"{node}: pytest exited {result.returncode} without producing any "
        "output — a broken proof environment, not a falsified test. "
        f"{detail[-1][:200] if detail else 'no output'}"
    )


def _prove_one(ident: str, names: list[str], base: str) -> list[str]:
    """Prove one entry's falsifiers. Returns the ones that did not."""
    tree = Path(tempfile.mkdtemp(prefix="falsifier-"))
    try:
        _git("worktree", "add", "--detach", "--quiet", str(tree), "HEAD")
        node_ids = _node_ids(names, tree)
        if not node_ids:
            return [f"{ident} cites {names}, none of which resolve"]
        failed, passed = _prove(base, node_ids, tree)
        for node in failed:
            print(f"{ident}: {node} fails without the change — proven")
        return [
            f"{ident}: {node} PASSES without the change, so it does not defend it"
            for node in passed
        ]
    finally:
        _git("worktree", "remove", "--force", str(tree))
        shutil.rmtree(tree, ignore_errors=True)


def _added_class_falsifiers(base: str) -> list[str]:
    """`tests/*_class.py` files this change *adds*, in sorted order.

    The population-derived class falsifiers are a second convention beside
    the register (``test_falsifier_standard`` enforces their non-empty
    population; nothing enforced that they fail without their change). This
    brings them under the same revert proof — but only the ones the change
    *adds*. A file the change merely *modifies* may defend a fix that
    predates this base, so reverting to the base leaves a tree where the
    test legitimately passes; proving it would be a false accusation. An
    added file arrives with the change it defends, so the base cannot
    already contain it.
    """
    added = _git("diff", "--name-only", "--diff-filter=A", base, "HEAD").splitlines()
    return sorted(path for path in added if _is_class_falsifier(path))


def _is_class_falsifier(path: str) -> bool:
    """A ``tests/*_class.py`` population-derived falsifier file."""
    return path.startswith("tests/") and path.endswith("_class.py")


# A test file may legitimately cover behaviour that already worked — a
# characterisation test, or coverage nobody had written yet. Such a file
# passes at the base and is not a broken falsifier. It says so in its
# module docstring rather than being assumed, because "this one is fine"
# is precisely the judgement an agent grading its own homework would make
# silently.
COVERS_EXISTING = "Covers existing behaviour:"


def _added_test_files(base: str) -> list[str]:
    """Every ``tests/test_*.py`` this change adds, class falsifiers aside.

    The register and the class-falsifier convention were the only two
    routes into this proof, and the languages shipped through neither:
    C, C++, C#, Fortran and fixed-form Fortran arrived as feature
    increments with roughly 300 tests, none of which CI ever watched
    fail. The hole was not in the proof but in what reached it, so the
    selector now follows how work actually arrives.

    Added files only, for the reason the class version gives: a modified
    file may defend a fix older than this base, and proving it would be a
    false accusation.
    """
    added = _git("diff", "--name-only", "--diff-filter=A", base, "HEAD").splitlines()
    return sorted(
        path for path in added
        if path.startswith("tests/")
        and Path(path).name.startswith("test_")
        and path.endswith(".py")
        and not _is_class_falsifier(path)
    )


def _tests_in(source: str, filename: str) -> list[str]:
    """Every ``test_`` function a file defines, as pytest node ids."""
    return [
        f"tests/{filename}::{match.group(1)}"
        for match in re.finditer(r"^\s*(?:async\s+)?def (test_\w+)\b", source, re.M)
    ]


def _prove_class_files(paths: list[str], base: str) -> list[str]:
    """Revert-prove every added class falsifier in one scratch worktree.

    Returns the node ids that PASSED at the base, i.e. did not defend the
    change they shipped with. Reuses ``_prove``: the class files stay as
    this commit wrote them while everything else reverts, so each test runs
    against the world before the fix and must fail.
    """
    tree = Path(tempfile.mkdtemp(prefix="falsifier-class-"))
    try:
        _git("worktree", "add", "--detach", "--quiet", str(tree), "HEAD")
        node_ids: list[str] = []
        for path in paths:
            node_ids += _tests_in((tree / path).read_text(encoding="utf-8"), Path(path).name)
        if not node_ids:
            return []
        failed, passed = _prove(base, node_ids, tree)
        for node in failed:
            print(f"class falsifier: {node} fails without the change — proven")
        return [
            f"class falsifier {node} PASSES without the change, so it does not defend it"
            for node in passed
        ]
    finally:
        _git("worktree", "remove", "--force", str(tree))
        shutil.rmtree(tree, ignore_errors=True)


def _prove_added_tests(paths: list[str], base: str) -> list[str]:
    """Revert-prove the tests an added file brings, one worktree for all.

    A file whose every test passes at the base defended nothing that
    shipped with it. That is reported unless the file declares itself as
    covering pre-existing behaviour, which is a real and common case and
    so is allowed — stated, not assumed.
    """
    tree = Path(tempfile.mkdtemp(prefix="falsifier-added-"))
    try:
        _git("worktree", "add", "--detach", "--quiet", str(tree), "HEAD")
        node_ids: list[str] = []
        exempt: set[str] = set()
        for path in paths:
            source = (tree / path).read_text(encoding="utf-8")
            if COVERS_EXISTING in source:
                reason = source.split(COVERS_EXISTING, 1)[1].splitlines()[0].strip()
                print(f"{path}: exempt — covers existing behaviour: {reason}")
                exempt.add(path)
                continue
            node_ids += _tests_in(source, Path(path).name)
        if not node_ids:
            return []
        failed, passed = _prove(base, node_ids, tree)
        print(f"  {len(failed)} of {len(node_ids)} fail without the change")
        by_file: dict[str, list[str]] = {}
        for node in passed:
            by_file.setdefault(node.split("::", 1)[0], []).append(node)
        return [
            f"{path}: every test passes without the change "
            f"({len(nodes)} of {len(nodes)}), so the file defends nothing it "
            f"shipped with; add `{COVERS_EXISTING} <reason>` to its docstring "
            "if that is deliberate"
            for path, nodes in sorted(by_file.items())
            if path not in exempt
            and len(nodes) == len(_tests_in((tree / path).read_text(encoding="utf-8"),
                                            Path(path).name))
        ]
    finally:
        _git("worktree", "remove", "--force", str(tree))
        shutil.rmtree(tree, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="commit the fixes land on top of")
    args = parser.parse_args()
    base = _git("rev-parse", args.base).strip()

    new = _new_entries(base)
    class_files = _added_class_falsifiers(base)
    added_tests = _added_test_files(base)
    if not new and not class_files and not added_tests:
        print("no new register entries, class falsifiers or added tests; nothing to prove")
        return 0

    unproven: list[str] = []
    for ident, body in sorted(new.items(), key=lambda item: int(item[0][1:])):
        if int(ident[1:]) < PROVE_FROM:
            continue
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
        unproven += _prove_one(ident, names, base)

    if class_files:
        print(f"\nproving {len(class_files)} added class falsifier(s): "
              f"{', '.join(class_files)}")
        unproven += _prove_class_files(class_files, base)

    if added_tests:
        print(f"\nproving {len(added_tests)} added test file(s): "
              f"{', '.join(added_tests)}")
        unproven += _prove_added_tests(added_tests, base)

    if unproven:
        print("\nfalsifiers that do not falsify:")
        for line in unproven:
            print(f"  {line}")
        return 1
    print("\nevery newly cited falsifier fails without its change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
