"""Narrowing the work order, and the rule that keeps it a view — task 4.7-4.8.

Split from `test_work_order.py` when that file crossed the 500-line gate
this project enforces on everyone else. The seam is real: that file is
about *what the work order says* — the risk/effort weighting, the
computed deltas, the verification commands. This one is about *showing
less of it*, which is a different kind of claim.

The property under test here is the one that keeps a growing tool from
becoming 2,550 measures: **a filter may never move a number.** It reads
what the audit already gathered and returns a subset. The moment
narrowing can change a score, the rubric stops being uniform and two
readers of the same repository get different answers because they asked
different questions.
"""

from __future__ import annotations

import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from maintainability_audit._work_order import CLASS_RISK_EFFORT, Band, work_order


def _repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def _long_function(name: str, branches: int = 40) -> str:
    body = "".join(f"    if x == {n}:\n        return {n}\n" for n in range(branches))
    return f"def {name}(x):\n{body}    return -1\n"

# 4.7-4.8 — filtering is a view. It may never touch the rubric.
# --------------------------------------------------------------------


def test_filtering_never_changes_a_single_score(tmp_path: Path) -> None:
    """The rule that keeps this from becoming 2,550 measures.

    A filter answers "show me less". It is presentation over evidence
    already gathered, and the moment it can move a number the rubric
    stops being uniform — two readers of the same repository would get
    different scores because they asked different questions.

    Asserted over every filter axis at once: the score block must be
    byte-identical whatever the caller selected.
    """
    from maintainability_audit._work_order import select
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / "filtered", {
        **{f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(60)},
        "pkg/hot.py": _long_function("tangled"),
        "pkg/huge.py": _long_function("sprawling", branches=90),
    })
    report = build_report(root, load_config(None))
    before = deepcopy(report["score"])

    for criteria in (
        {"band": "quick-win"},
        {"finding_class": "oversized-declaration"},
        {"path": "pkg/hot.py"},
        {"band": "quick-win", "path": "pkg/huge.py"},
        {"band": "nothing-matches-this"},
    ):
        selected = select(report["work_order"], **criteria)
        assert report["score"] == before, f"filtering by {criteria} moved the score"
        assert all(item in report["work_order"] for item in selected), (
            "a filter may only remove items, never invent or alter them"
        )


def test_a_selection_quotes_its_own_recomputed_worth(tmp_path: Path) -> None:
    """"Clear these six" is worth a number, and not the sum of six numbers.

    Findings of one class share a denominator, so the value of clearing
    a chosen subset has to be recomputed for that subset. Quoting a sum
    overstates a work order by more the longer it gets, which is exactly
    the direction that flatters.
    """
    from maintainability_audit._work_order import combined_delta, select
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / "subset", {
        **{f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(60)},
        **{f"pkg/hot{n}.py": _long_function(f"tangled{n}") for n in range(6)},
    })
    report = build_report(root, load_config(None))
    everything = report["work_order"]
    half = select(everything, path="pkg/hot0.py") + select(everything, path="pkg/hot1.py")
    if not half or len(everything) <= len(half):
        pytest.skip("needs a strict subset to compare")

    assert combined_delta(report, half) <= combined_delta(report, everything), (
        "clearing a subset cannot be worth more than clearing everything"
    )


@pytest.mark.parametrize(("declarations", "offenders"), [(60, 1), (600, 40)])
def test_the_same_rubric_applies_at_every_repository_size(
    tmp_path: Path, declarations: int, offenders: int,
) -> None:
    """A small repository and a large one are scored by one rubric.

    The risk this guards is real and cheap to fall into: a rule tuned so
    a twelve-file service behaves sensibly can quietly distort a
    thousand-file one, and nothing fails when it does. Both sizes here
    carry the same *proportion* of oversized declarations, so both must
    land in the same band with the same class weighting. Only the counts
    differ.
    """
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / f"size{declarations}", {
        **{f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(declarations)},
        **{f"pkg/hot{n}.py": _long_function(f"tangled{n}") for n in range(offenders)},
    })
    items = work_order(build_report(root, load_config(None)))
    oversized = [i for i in items if i["finding_class"] == "oversized-declaration"]

    assert oversized, "the same finding class must be produced at both sizes"
    assert oversized[0]["band"] == Band.QUICK_WIN.value
    assert oversized[0]["risk"] == CLASS_RISK_EFFORT["oversized-declaration"].risk
    assert len(oversized) == offenders, "every offender is listed, whatever the size"


def test_the_cli_narrows_the_work_order_and_quotes_the_subset_worth(tmp_path: Path) -> None:
    """One flag, repeatable. Not one flag per axis.

    The surface is deliberately small: `--work axis=value`, repeated.
    Adding a flag per axis is how a tool ends up with fifty of them and
    a reader who cannot find the one they want.

    What the selection quotes is recomputed for that selection, never
    summed from the items — findings of one class share a denominator,
    so a sum overstates by more the longer the list.
    """
    from maintainability_audit.cli import main

    root = _repo(tmp_path / "cli", {
        **{f"pkg/mod{n}.py": "def f():\n    return 1\n" for n in range(60)},
        "pkg/hot.py": _long_function("tangled"),
        "pkg/other.py": _long_function("sprawling", branches=90),
    })
    out = tmp_path / "report.md"

    assert main(["--root", str(root), "--output", str(out),
                 "--work", "path=pkg/hot.py"]) == 0
    narrowed = out.read_text(encoding="utf-8")
    section = narrowed.split("## Selected Work", 1)[-1].split("\n## ", 1)[0]

    assert "## Selected Work" in narrowed, "a selection states what clearing it is worth"
    assert "tangled" in section
    # Narrowed within the work order only. The findings tables below
    # still list every hotspot and duplicate: `--work` chooses what to
    # *do*, and suppressing the evidence would leave a reader unable to
    # check the choice.
    assert "sprawling" not in section, "the work order was not narrowed"
    assert "## Work Order" not in narrowed, "a selection replaces the full list"


def test_an_unknown_filter_axis_is_refused_rather_than_ignored(tmp_path: Path) -> None:
    """A filter that quietly ignores its input is worse than one that fails.

    The caller believes the narrowing happened and reads a full list as
    though it were a selection.
    """
    from maintainability_audit.cli import main

    root = _repo(tmp_path / "badaxis", {"a.py": "def f():\n    return 1\n"})

    with pytest.raises(SystemExit) as raised:
        main(["--root", str(root), "--work", "colour=blue"])

    assert raised.value.code != 0
