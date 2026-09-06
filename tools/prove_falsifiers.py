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
import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from _falsifier_scope import (  # noqa: E402 - sibling module, script dir on sys.path
    COVERS_EXISTING,
    ROOT,
    added_class_falsifiers,
    added_test_files,
    added_tests_in_modified_files,
    function_source,
    git,
    tests_in,
)

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
    before = _entries(git("show", f"{base}:{REGISTER.as_posix()}"))
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
    git("checkout", base, "--", ".", *(f":(exclude){path}" for path in keep), cwd=tree)
    added = [
        line for line in git(
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
        git("worktree", "add", "--detach", "--quiet", str(tree), "HEAD")
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
        git("worktree", "remove", "--force", str(tree))
        shutil.rmtree(tree, ignore_errors=True)






# A test file may legitimately cover behaviour that already worked — a
# characterisation test, or coverage nobody had written yet. Such a file
# passes at the base and is not a broken falsifier. It says so in its
# module docstring rather than being assumed, because "this one is fine"
# is precisely the judgement an agent grading its own homework would make
# silently.






def _module_docstring(source: str) -> str:
    """The file's own docstring, or "" — never a function's.

    The escape has to be attributable. Scanning the whole source made any
    test's docstring a claim about every test in the file.
    """
    try:
        module = ast.parse(source)
    except SyntaxError:
        return ""
    return ast.get_docstring(module) or ""


def declares_exemption(text: str) -> str | None:
    """The stated reason a file or test covers existing behaviour, or None.

    An occurrence that is quoted — wrapped in backticks or quote
    characters — is a *mention*, not a declaration. Prose explaining the
    escape exempted the very test explaining it: this project's own
    falsifier for the added-file rule was reported exempt, with a reason
    sliced out of a sentence about the mechanism.

    That is the defect D108 closed one layer over, where a suppression
    marker quoted in a docstring was read as a directive. The rule is the
    same and so is the reason: a gate that cannot tell a mention from a
    declaration lets anything hide behind a sentence about it.
    """
    for line in text.splitlines():
        index = line.find(COVERS_EXISTING)
        if index < 0:
            continue
        before = line[:index].lstrip()
        # A docstring's own opening delimiter is not quoting anything —
        # the overwhelmingly common declaration is the phrase opening the
        # docstring. Only a triple quote counts as that opener; a single
        # one before the phrase is somebody quoting it mid-sentence.
        if before in {'"""', "'''", ""}:
            return line[index + len(COVERS_EXISTING):].strip()
        if before[-1:] in {"`", "'", '"'} or before.count("`") % 2:
            continue
        return line[index + len(COVERS_EXISTING):].strip()
    return None


def _prove_added_tests_in_place(node_ids: list[str], base: str) -> list[str]:
    """Revert-prove tests added to files that already existed.

    Per test rather than per file: the file's other tests defend older work
    and are not this change's to prove. A test that passes at the base
    defended nothing it shipped with, unless it says it covers pre-existing
    behaviour — the same stated-not-assumed escape the added-file path uses,
    read from the function's own source so one regression test does not
    exempt its neighbours.
    """
    tree = Path(tempfile.mkdtemp(prefix="falsifier-inplace-"))
    try:
        git("worktree", "add", "--detach", "--quiet", str(tree), "HEAD")
        wanted: list[str] = []
        for node in node_ids:
            path, name = node.split("::", 1)
            body = function_source((tree / path).read_text(encoding="utf-8"), name)
            reason = declares_exemption(body)
            if reason is not None:
                print(f"{node}: exempt — covers existing behaviour: {reason}")
                continue
            wanted.append(node)
        if not wanted:
            return []
        failed, passed = _prove(base, wanted, tree)
        for node in failed:
            print(f"added test: {node} fails without the change — proven")
        return [
            f"{node} was added by this change but PASSES without it, so it "
            f"defends nothing that shipped with it; add "
            f"`{COVERS_EXISTING} <reason>` to its docstring if that is deliberate"
            for node in passed
        ]
    finally:
        git("worktree", "remove", "--force", str(tree))
        shutil.rmtree(tree, ignore_errors=True)




def _prove_class_files(paths: list[str], base: str) -> list[str]:
    """Revert-prove every added class falsifier in one scratch worktree.

    Returns the node ids that PASSED at the base, i.e. did not defend the
    change they shipped with. Reuses ``_prove``: the class files stay as
    this commit wrote them while everything else reverts, so each test runs
    against the world before the fix and must fail.
    """
    tree = Path(tempfile.mkdtemp(prefix="falsifier-class-"))
    try:
        git("worktree", "add", "--detach", "--quiet", str(tree), "HEAD")
        node_ids: list[str] = []
        for path in paths:
            node_ids += tests_in((tree / path).read_text(encoding="utf-8"), Path(path).name)
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
        git("worktree", "remove", "--force", str(tree))
        shutil.rmtree(tree, ignore_errors=True)


def _prove_added_tests(paths: list[str], base: str) -> list[str]:
    """Revert-prove the tests an added file brings, one worktree for all.

    Every test that passes at the base is reported, not only a file where
    all of them do. The looser file-level rule let one hollow test ride
    in beside fourteen real ones — it printed "14 of 15 fail without the
    change" and exited 0 — while the added-in-place check, on the same
    run, held each new test individually. A test's obligation to falsify
    something cannot depend on how new its neighbours are.

    The escape stays file-level and stays explicit: a file that declares
    itself as covering pre-existing behaviour is exempt entirely, which
    is a real and common case, stated rather than assumed.
    """
    tree = Path(tempfile.mkdtemp(prefix="falsifier-added-"))
    try:
        git("worktree", "add", "--detach", "--quiet", str(tree), "HEAD")
        node_ids: list[str] = []
        exempt: set[str] = set()
        for path in paths:
            source = (tree / path).read_text(encoding="utf-8")
            # A file-level claim is one the *module* docstring makes.
            # Reading the whole file exempted every test in it because a
            # single test declared the escape for itself — D109 made the
            # reporting per-test and left this half file-level, so one
            # legitimate exemption silenced nineteen falsifiers beside it.
            reason = declares_exemption(_module_docstring(source))
            if reason is not None:
                print(f"{path}: exempt — covers existing behaviour: {reason}")
                exempt.add(path)
                continue
            for node in tests_in(source, Path(path).name):
                own = declares_exemption(function_source(source, node.split("::", 1)[1]))
                if own is not None:
                    print(f"{node}: exempt — covers existing behaviour: {own}")
                    continue
                node_ids.append(node)
        if not node_ids:
            return []
        failed, passed = _prove(base, node_ids, tree)
        print(f"  {len(failed)} of {len(node_ids)} fail without the change")
        return [
            f"{node} PASSES without the change, so it defends nothing it "
            f"shipped with; make it fail at the base, or add "
            f"`{COVERS_EXISTING} <reason>` to the file's docstring if the "
            "whole file is deliberately about behaviour that already existed"
            for node in sorted(passed)
            if node.split("::", 1)[0] not in exempt
        ]
    finally:
        git("worktree", "remove", "--force", str(tree))
        shutil.rmtree(tree, ignore_errors=True)


def _prove_register_entries(new: dict[str, str], base: str) -> list[str]:
    """The original route: register entries added by this change."""
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
    return unproven


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="commit the fixes land on top of")
    args = parser.parse_args()
    base = git("rev-parse", args.base).strip()

    new = _new_entries(base)
    class_files = added_class_falsifiers(base)
    added_tests = added_test_files(base)
    added_in_place = added_tests_in_modified_files(base)
    if not new and not class_files and not added_tests and not added_in_place:
        print("no new register entries, class falsifiers or added tests; nothing to prove")
        return 0

    unproven = _prove_register_entries(new, base)

    if class_files:
        print(f"\nproving {len(class_files)} added class falsifier(s): "
              f"{', '.join(class_files)}")
        unproven += _prove_class_files(class_files, base)

    if added_tests:
        print(f"\nproving {len(added_tests)} added test file(s): "
              f"{', '.join(added_tests)}")
        unproven += _prove_added_tests(added_tests, base)

    if added_in_place:
        print(f"\nproving {len(added_in_place)} test(s) added to existing file(s): "
              f"{', '.join(added_in_place)}")
        unproven += _prove_added_tests_in_place(added_in_place, base)

    if unproven:
        print("\nfalsifiers that do not falsify:")
        for line in unproven:
            print(f"  {line}")
        return 1
    print("\nevery newly cited falsifier fails without its change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
