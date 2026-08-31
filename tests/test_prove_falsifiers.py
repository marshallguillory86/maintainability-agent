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
    assert prover._is_class_falsifier("tests/test_clone_group_class.py")
    assert not prover._is_class_falsifier("tests/test_scanning.py")
    assert not prover._is_class_falsifier("src/maintainability_audit/_class.py")


def test_every_test_function_in_a_class_file_becomes_a_node_id() -> None:
    """The proof runs the whole file: a class falsifier that added a
    passing decoy beside its real assertion cannot hide it from the sweep."""
    source = (
        "import pytest\n\n"
        "def helper():\n    return 1\n\n"
        "def test_alpha():\n    assert helper() == 1\n\n"
        "async def test_beta():\n    assert True\n"
    )
    assert prover._tests_in(source, "test_x_class.py") == [
        "tests/test_x_class.py::test_alpha",
        "tests/test_x_class.py::test_beta",
    ]


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
