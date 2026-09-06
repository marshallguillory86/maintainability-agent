"""D99: the check that a falsifier falsifies.

Miles Parker's objection, in his words: an agent is in control of both
what is being tested and the test, so one that introduced a bug and
mutated the test to cover it would look no different externally from one
that functioned perfectly.

Every control before this was self-report. The falsifier standard is
enforced by tests the same agent can edit; the `*Mutation:*` line is the
author's account of what they broke. `tools/prove_falsifiers.py` is the
first control that does not take the author's word: it restores the
repository to the base commit, keeps only the files defining the cited
tests, and requires each of them to fail.

These check the tool's own decisions, because a prover that cannot tell
a real falsifier from a weakened one is worse than none -- it would
launder exactly the substitution it exists to catch.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import _falsifier_scope as scope  # noqa: E402
import prove_falsifiers as prover  # noqa: E402


def test_the_citation_region_stops_at_the_next_field() -> None:
    """A `*Mutation:*` line names tests and is not a citation.

    The mutation statement is *required* to say which member it broke,
    so reading to the end of an entry made every such statement look
    like a miscited falsifier.
    """
    entry = (
        "Body.\n\n"
        "*Closing tests:* `test_the_real_one` in `tests/test_x.py`.\n\n"
        "*Roles:* found=grok fix=claude test=codex run=mutation\n\n"
        "*Mutation:* broke `test_a_different_one`, outside the sample.\n"
    )
    assert prover._cited(entry) == ["test_the_real_one"], (
        "the citation region swallowed a later field, so a mutation "
        "statement would be read as a claim about a falsifier"
    )


def test_a_path_is_not_a_citation() -> None:
    """`tests/test_x.py` names a file; the module stem is not a test."""
    entry = "*Closing tests:* see `tests/test_falsifier_standard.py`.\n"
    assert prover._cited(entry) == [], (
        "a bare path counted as naming a test, so an entry could cite an "
        "address instead of a falsifier"
    )


def test_only_entries_the_base_lacks_are_proven() -> None:
    """Re-proving the whole register every run would be unusable.

    And wrong: an entry closed six commits ago is not defended by the
    diff under review.
    """
    before = prover._entries("\n### D1 — Closed: a (Low)\n\nbody\n")
    after = prover._entries(
        "\n### D1 — Closed: a (Low)\n\nbody\n\n### D2 — Closed: b (Low)\n\nbody\n")
    assert set(after) - set(before) == {"D2"}


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("*Closing tests:* `test_one` and `test_two` in `tests/test_a.py`.",
         ["test_one", "test_two"]),
        ("*Closing test:* `test_one` in `tests/test_a.py`.", ["test_one"]),
        ("*Closing suite:* `test_one` in `tests/test_a.py`.", ["test_one"]),
        ("No citation at all.", []),
    ],
    ids=["plural", "singular", "suite", "none"],
)
def test_every_citation_spelling_the_register_uses_is_read(
    body: str, expected: list[str],
) -> None:
    """A spelling the parser cannot read is an entry it silently skips.

    Silently skipping is the failure mode that matters here: the tool
    would report success over an entry it never examined, which is the
    class D97 names arriving inside the control for it.
    """
    assert prover._cited(body) == expected


def test_class_falsifier_files_are_recognised_but_other_tests_are_not() -> None:
    """Only `tests/*_class.py` is a class falsifier the prover reverts.

    A plain test file, or a `_class.py` outside `tests/`, is not the
    population-derived convention and must not be dragged into the proof.
    """
    assert scope.is_class_falsifier("tests/test_clone_group_class.py")
    assert not scope.is_class_falsifier("tests/test_scanning.py")
    assert not scope.is_class_falsifier("src/maintainability_audit/_class.py")


def test_every_test_function_in_a_class_file_becomes_a_node_id() -> None:
    """The proof runs the whole file: a class falsifier that added a
    passing decoy beside its real assertion cannot hide it from the sweep."""
    source = (
        "import pytest\n\n"
        "def helper():\n    return 1\n\n"
        "def test_alpha():\n    assert helper() == 1\n\n"
        "async def test_beta():\n    assert True\n"
    )
    assert scope.tests_in(source, "test_x_class.py") == [
        "tests/test_x_class.py::test_alpha",
        "tests/test_x_class.py::test_beta",
    ]


def _synthetic_change(tmp_path: Path) -> tuple[str, Path, Path]:
    """A repository where one value moves, with a test that expects the move.

    Returns `(base, worktree, decoy)`. The decoy holds HEAD's value and
    stands in for the editable install: a copy of the package importable
    from outside the worktree.
    """
    import os
    import subprocess

    # This machine carries a global hook refusing any commit whose author
    # is not the personal identity, and it fires inside scratch
    # repositories too. The hook documents this override; without it the
    # commits are refused and the fixture silently proves nothing.
    environment = {**os.environ, "GIT_IDENTITY_OVERRIDE": "1"}
    repo = tmp_path / "repo"
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()

    def git(*args: str, cwd: Path = repo) -> str:
        done = subprocess.run(  # noqa: S603
            ["git", *args], cwd=cwd, check=True, capture_output=True,
            text=True, env=environment,
        )
        return done.stdout.strip()

    git("init", "-q", ".")
    git("config", "user.email", "audit@example.invalid")
    git("config", "user.name", "audit")
    (repo / "src" / "pkg" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    assert len(base) == 40, "the fixture never committed; it would prove nothing"

    (repo / "src" / "pkg" / "__init__.py").write_text("VALUE = 2\n", encoding="utf-8")
    (repo / "tests" / "test_value.py").write_text(
        "from pkg import VALUE\n\n\ndef test_value():\n    assert VALUE == 2\n",
        encoding="utf-8",
    )
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-qm", "change")

    tree = tmp_path / "wt"
    git("worktree", "add", "--detach", "--quiet", str(tree), "HEAD")
    decoy = tmp_path / "decoy"
    (decoy / "pkg").mkdir(parents=True)
    (decoy / "pkg" / "__init__.py").write_text("VALUE = 2\n", encoding="utf-8")
    return base, tree, decoy


def test_the_reverted_tree_is_the_tree_the_tests_import(tmp_path: Path) -> None:
    """The proof must run the base's code, not merely restore its files.

    `_prove` restores the worktree to the base and runs the new tests
    inside it — and `pip install -e .` puts the *checkout's* own `src` on
    the path, so `import maintainability_audit` resolved to HEAD no
    matter what the worktree held. Reverting the files changed what a
    test could **read** and nothing about what it could **call**, which
    is why document falsifiers proved correctly for months while every
    behaviour falsifier passed vacuously. Measured on the Fortran work:
    0 of 19 failed at the base before the fix, 18 of 19 after.

    The decoy below is that editable install, in miniature.
    """
    import os

    base, tree, decoy = _synthetic_change(tmp_path)
    # The decoy has to sit where the editable install sits: on this
    # process's own import path, which is what `_prove` hands the child.
    # Putting it only in `os.environ` proved nothing — the child's path is
    # rebuilt from `sys.path`, so the decoy never reached it and the test
    # failed at the base for the wrong reason, passing this guard under
    # the very mutation it exists to catch.
    previous = os.environ.get("PYTHONPATH")
    os.environ["PYTHONPATH"] = str(decoy)
    sys.path.insert(0, str(decoy))
    try:
        failed, passed = prover._prove(
            base, ["tests/test_value.py::test_value"], tree
        )
    finally:
        sys.path.remove(str(decoy))
        if previous is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = previous

    assert (tree / "src" / "pkg" / "__init__.py").read_text(
        encoding="utf-8").strip() == "VALUE = 1", "the worktree was never reverted"
    assert failed == ["tests/test_value.py::test_value"], (
        "the test passed against the base, so the prover imported the decoy "
        "rather than the reverted worktree — every behaviour falsifier it "
        "reports as proven would be vacuous"
    )
    assert passed == []


def test_a_child_that_never_ran_is_not_a_proof() -> None:
    """A broken environment must refuse, not report every test as proven.

    `_prove` read every non-zero exit as "failed at the base", which it
    treats as proof. A child that could not start therefore counted as a
    successful proof, and an environment broken in any way reported that
    every falsifier falsified.

    This is not hypothetical: it is what hid the shadowing defect above.
    The mutation that should have failed that guard passed instead,
    because the child was exiting 1 with `No module named pytest` and the
    tool was reading that as evidence.

    The line is output, not exit code — which matters, because a
    collection error *is* a real signal here. A new test file naming a
    module the base does not have cannot be collected, and this file's
    own docstring already counts that as the weaker proof it is. Only a
    child that printed nothing at all never ran.
    """
    import subprocess

    import pytest as _pytest

    def outcome(returncode: int, stdout: str, stderr: str = ""):
        return subprocess.CompletedProcess(
            args=["pytest"], returncode=returncode, stdout=stdout, stderr=stderr
        )

    # The interpreter never reached pytest: nothing on stdout.
    never_ran = outcome(1, "", "No module named pytest")
    assert not prover._pytest_reached_a_verdict(never_ran)
    with _pytest.raises(RuntimeError, match="without producing any output"):
        prover._refuse_a_run_that_never_happened("tests/t.py::x", never_ran)

    # pytest ran and could not collect: the base lacks the module the new
    # test imports. Weak, and still evidence about the tree.
    could_not_collect = outcome(4, "ERROR: found no collectors for tests/t.py::x")
    assert prover._pytest_reached_a_verdict(could_not_collect)
    prover._refuse_a_run_that_never_happened("tests/t.py::x", could_not_collect)

    # An ordinary failure, which is what a proof looks like.
    failed = outcome(1, "1 failed in 0.01s")
    assert prover._pytest_reached_a_verdict(failed)
    prover._refuse_a_run_that_never_happened("tests/t.py::x", failed)


def test_the_tool_is_wired_into_the_pipeline() -> None:
    """A prover nobody runs proves nothing.

    It is a pull-request job deliberately: the base to revert to is the
    branch the change is proposed against, which only a PR defines.
    """
    workflow = (ROOT / ".github" / "workflows" / "quality-gates.yml").read_text(
        encoding="utf-8")
    assert "prove-falsifiers:" in workflow, "the proving job is gone"
    block = workflow.split("prove-falsifiers:", 1)[1].split("\n  analyzer-drift:")[0]
    assert "tools/prove_falsifiers.py" in block, "the job no longer runs the tool"
    assert "--base" in block, "the job runs the tool with no base to revert to"
    for neutered in ("|| true", "continue-on-error", "|| exit 0"):
        assert neutered not in block, (
            f"the proving job is neutered with {neutered!r}, so a falsifier "
            "that does not falsify reports green"
        )


def test_one_hollow_test_in_an_added_file_is_still_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A test's obligation cannot depend on how new its neighbours are.

    The added-file check asked whether *every* test in the file passed at
    the base, so a single test that defends nothing rode in beside
    fourteen that do. The added-in-place check, on the same run, held
    each new test individually and named both of them.

    That inconsistency shipped a real hollow test: a `--staged` refusal
    case asserted `"--changed-only" in stderr`, which argparse's usage
    banner satisfies whether or not the feature exists, so it passed on a
    tree where `--staged` was not a flag at all. The gate saw it — it
    printed "14 of 15 fail without the change" — and exited 0.

    One passing member is enough to report. The file-level
    ``Covers existing behaviour:`` escape still exempts a whole file that
    is deliberately about pre-existing behaviour.
    """
    added = "tests/test_precommit_staged.py"
    real = (ROOT / added).read_text(encoding="utf-8")
    nodes = prover.tests_in(real, Path(added).name)
    assert len(nodes) > 2, "fixture file must carry several tests"

    hollow, defended = nodes[0], nodes[1:]
    monkeypatch.setattr(prover, "_prove", lambda base, ids, tree: (defended, [hollow]))

    complaints = prover._prove_added_tests([added], "HEAD")
    assert complaints, (
        "a test that passes without the change went unreported because its "
        "neighbours were new"
    )
    assert any(hollow in line for line in complaints), (
        f"the hollow test was not named: {complaints}"
    )


def test_a_quoted_escape_phrase_does_not_exempt_anything() -> None:
    """Writing *about* the escape must not trigger it — D108's shape, here.

    The escape is matched as a substring of the source, so a docstring
    that names it in backticks while explaining it exempts the very test
    doing the explaining. That happened on this file: the falsifier for
    the added-file rule was reported as
    ``exempt - covers existing behaviour: `` escape still exempts a whole
    file that`` — a reason cut out of a sentence about the mechanism.

    It is the same defect D108 closed for suppression markers: a marker
    mentioned in prose is not a directive. A gate that cannot tell the
    two apart lets any test hide behind a sentence.
    """
    phrase = prover.COVERS_EXISTING
    assert not prover.declares_exemption(f"the ``{phrase}`` escape exempts a file")
    assert not prover.declares_exemption(f'"{phrase}" is how a file opts out')
    assert prover.declares_exemption(f"{phrase} this file measures what shipped")
    # The declaration almost always opens a docstring, and the triple
    # quote in front of it is the delimiter, not somebody quoting it.
    assert prover.declares_exemption(f'    """{phrase} already reported.')
