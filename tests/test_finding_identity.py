"""Finding identity must survive edits that do not touch the finding.

The scheme this replaces embedded the start line, so inserting one import
above an untouched function made it read as simultaneously fixed and new.
That is a false failure for `--fail-on-new` on any refactor that shifts
lines, and it makes recurrence tracking impossible: a returning finding
cannot be distinguished from a fresh one.

These are property tests over insertion position, not a regression pinned to
the one case that was reported. ADR 009.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._identity import duplicate_fingerprint, finding_fingerprints
from maintainability_audit.baseline import (
    BASELINE_VERSION,
    StaleBaseline,
    load_baseline,
    write_baseline,
)
from maintainability_audit.config import load_config
from maintainability_audit.report import build_report

LONG_BODY = "\n".join(f"    x{i} = {i}" for i in range(120))
METHOD_BODY = "\n".join(f"        x{i} = {i}" for i in range(120))


def _repo(tmp_path: Path, name: str = "r") -> Path:
    root = tmp_path / name
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    return root


def _commit(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "x"],
        check=True,
    )


def _fingerprints(root: Path) -> set[str]:
    return finding_fingerprints(build_report(root, load_config(None)))


@pytest.mark.parametrize("inserted", [1, 5, 40, 200])
def test_inserting_lines_above_a_finding_does_not_change_its_identity(
    tmp_path: Path, inserted: int
) -> None:
    """The property, swept over how much was inserted.

    A single import was the reported case; nothing about the defect was
    specific to one line, so the test is not either.
    """
    root = _repo(tmp_path)
    (root / "big.py").write_text(f"def huge():\n{LONG_BODY}\n    return 0\n", encoding="utf-8")
    _commit(root)
    before = _fingerprints(root)
    assert before, "fixture must actually produce a finding or the test proves nothing"

    prelude = "".join(f"import os as _o{i}\n" for i in range(inserted))
    (root / "big.py").write_text(prelude + (root / "big.py").read_text(encoding="utf-8"),
                                 encoding="utf-8")

    assert _fingerprints(root) == before


def test_two_same_named_declarations_keep_distinct_identities(tmp_path: Path) -> None:
    """Dropping the line number must not merge overloads into one finding.

    Ordinals disambiguate them, and both shift together under insertion, so
    their relative order and therefore their ordinals hold.
    """
    root = _repo(tmp_path)
    (root / "two.py").write_text(
        f"class A:\n    def huge(self):\n{METHOD_BODY}\n        return 0\n"
        f"class B:\n    def huge(self):\n{METHOD_BODY}\n        return 1\n",
        encoding="utf-8",
    )
    _commit(root)
    before = _fingerprints(root)
    named = {f for f in before if ":huge#" in f}
    assert len(named) == 2, f"expected two distinct identities, got {sorted(named)}"

    (root / "two.py").write_text("import os\n" + (root / "two.py").read_text(encoding="utf-8"),
                                 encoding="utf-8")
    assert _fingerprints(root) == before


def test_editing_the_finding_itself_does_change_its_identity(tmp_path: Path) -> None:
    """Stability must not become blindness.

    Renaming the unit is a different finding about different code, and the
    fingerprint has to say so or a fixed finding would look permanently open.
    """
    root = _repo(tmp_path)
    (root / "big.py").write_text(f"def huge():\n{LONG_BODY}\n    return 0\n", encoding="utf-8")
    _commit(root)
    before = _fingerprints(root)

    (root / "big.py").write_text(f"def enormous():\n{LONG_BODY}\n    return 0\n", encoding="utf-8")
    assert _fingerprints(root) != before


def test_no_fingerprint_contains_a_bare_line_number() -> None:
    """The structural guard: identity may not encode position.

    Named for the class, not the instance. A future finding kind that folds a
    line number in fails here rather than in a user's CI six months later.
    """
    report = {
        "largest_files": [{"path": "a.py", "lines": 900, "status": "fail"}],
        "function_hotspots": [
            {"path": "a.py", "name": "f", "start_line": 42, "status": "fail"},
        ],
        "risk_findings": [{"path": "a.py", "line": 77, "name": "debt-marker", "text": "TODO"}],
        "duplicate_blocks": [{"locations": ["a.py:10", "b.py:99"], "sample": "x = 1", "count": 2}],
    }
    for fingerprint in finding_fingerprints(report):
        assert ":42" not in fingerprint
        assert ":77" not in fingerprint
        assert ":10" not in fingerprint
        assert ":99" not in fingerprint


def test_a_duplicate_block_survives_one_copy_moving(tmp_path: Path) -> None:
    same = duplicate_fingerprint(["a.py:10", "b.py:99"], "x = 1")
    moved = duplicate_fingerprint(["a.py:400", "b.py:12"], "x = 1")
    assert same == moved

    different_block = duplicate_fingerprint(["a.py:10", "b.py:99"], "y = 2")
    assert different_block != same


def test_a_version_1_baseline_is_rejected_rather_than_silently_ignored(tmp_path: Path) -> None:
    """Failing closed beats suppressing nothing.

    A v1 baseline loaded as-is would match no current fingerprint, so every
    pre-existing finding would surface as new and the build would fail with
    nothing the reader could act on.
    """
    stale = tmp_path / "old.json"
    stale.write_text(
        json.dumps({"version": 1, "root": ".", "findings": ["function:a.py:f:42"]}),
        encoding="utf-8",
    )
    with pytest.raises(StaleBaseline, match="--write-baseline"):
        load_baseline(str(stale))


def test_a_written_baseline_round_trips(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "big.py").write_text(f"def huge():\n{LONG_BODY}\n    return 0\n", encoding="utf-8")
    _commit(root)
    report = build_report(root, load_config(None))

    out = tmp_path / "bl.json"
    write_baseline(str(out), report)
    assert json.loads(out.read_text(encoding="utf-8"))["version"] == BASELINE_VERSION
    assert load_baseline(str(out)) == finding_fingerprints(report)


# ---------------------------------------------------------------------
# The ordinal has to reach the consumers, not just the baseline
# ---------------------------------------------------------------------
#
# `finding_fingerprints` numbered overloads correctly from the first
# commit of this scheme, and the test above pinned it there. Every
# consumer then rebuilt the identity itself with a literal 0, so two
# `huge` methods in one file were one finding to the work order, to
# `prompt_targets`, and to the escalation check in the prompt. The
# identity was right in the one place nobody reads and wrong in the
# three that drive behaviour.

TWO_OVERLOADS = (
    f"class A:\n    def huge(self):\n{METHOD_BODY}\n        return 0\n"
    f"class B:\n    def huge(self):\n{METHOD_BODY}\n        return 1\n"
)


def _overloads(tmp_path: Path, name: str = "overloads") -> tuple[Path, dict]:
    """A repository with two failing `huge` declarations in one file."""
    from maintainability_audit._work_order import work_order

    root = _repo(tmp_path, name)
    (root / "two.py").write_text(TWO_OVERLOADS, encoding="utf-8")
    _commit(root)
    report = build_report(root, load_config(None))
    report["work_order"] = work_order(report)
    return root, report


def _huge_items(report: dict) -> list[dict]:
    return [
        item for item in report["work_order"]
        if item["finding_class"] == "oversized-declaration"
        and item["title"].startswith("huge in ")
    ]


def test_the_work_order_gives_each_overload_its_own_identity(tmp_path: Path) -> None:
    """Two `huge` methods are two items, so they are two identities.

    They were both `function:two.py:huge#0`. A work order that names the
    same finding twice cannot be acted on twice, and the recurrence
    record it feeds learns that one declaration was advised about
    repeatedly while the other was never mentioned.
    """
    _, report = _overloads(tmp_path)
    items = _huge_items(report)
    assert len(items) == 2, f"expected two items, got {[i['title'] for i in items]}"

    fingerprints = {item["fingerprint"] for item in items}
    assert fingerprints == {"function:two.py:huge#0", "function:two.py:huge#1"}, (
        f"the work order collapsed the overloads onto {sorted(fingerprints)}"
    )
    assert fingerprints <= finding_fingerprints(report), (
        "a work-order fingerprint the report itself does not produce is an "
        "identity scheme of its own"
    )


def test_prompt_targets_records_both_overloads(tmp_path: Path) -> None:
    """What we advised is what recurrence scores later.

    `prompt_targets` kept only identities `finding_fingerprints` also
    produced — a good rule that silently discarded half the advice,
    because both rebuilt identities were `#0` and only `#0` could match.
    """
    _, report = _overloads(tmp_path)
    from maintainability_audit._work_order import prompt_targets

    targets = {t for t in prompt_targets(report) if ":huge#" in t}
    assert targets == {"function:two.py:huge#0", "function:two.py:huge#1"}, (
        f"prompt_targets recorded {sorted(targets)}"
    )


def test_escalating_one_overload_does_not_hide_the_other(tmp_path: Path) -> None:
    """The consequence a reader actually meets.

    Escalation moves a finding out of "inspect first" and into design
    review, because telling someone to look again at what they have
    already fixed twice is how a tool teaches people to ignore it. With
    both overloads answering to `#0`, escalating either one suppressed
    whichever the prompt happened to compare first.
    """
    _, report = _overloads(tmp_path)
    report["design_review_candidates"] = [{"fingerprint": "function:two.py:huge#1"}]

    from maintainability_audit.prompts import prompt_focus_sections

    lines = prompt_focus_sections(report)
    start = lines.index("Function hotspots to inspect first:")
    body: list[str] = []
    for line in lines[start + 1:]:
        if line.endswith(":"):  # the next section's heading
            break
        body.append(line)
    hotspots = "\n".join(body)

    assert "two.py:2`" in hotspots, (
        "the un-escalated overload at line 2 was suppressed by an escalation "
        f"naming the other one:\n{hotspots}"
    )
    assert "two.py:125`" not in hotspots, (
        f"the escalated overload at line 125 is still listed to inspect:\n{hotspots}"
    )


def test_inserting_above_both_overloads_leaves_the_work_order_alone(tmp_path: Path) -> None:
    """The insertion property, held where the ordinal is now consumed.

    `test_two_same_named_declarations_keep_distinct_identities` asserts
    this of `finding_fingerprints`. It passed throughout, on a report
    whose work order was wrong, which is the reason to assert it on both.
    """
    from maintainability_audit._work_order import work_order

    root, report = _overloads(tmp_path)
    before = {item["fingerprint"] for item in _huge_items(report)}

    two = root / "two.py"
    two.write_text("import os\n" + two.read_text(encoding="utf-8"), encoding="utf-8")
    after_report = build_report(root, load_config(None))
    after_report["work_order"] = work_order(after_report)

    assert {item["fingerprint"] for item in _huge_items(after_report)} == before


def test_no_module_hardcodes_an_ordinal() -> None:
    """The class, not the four call sites.

    An ordinal cannot be known from one finding — it is that finding's
    rank among its same-named siblings, so computing it needs the
    population. Every consumer that reached for `declaration_fingerprint`
    directly had only one item in hand and passed the only ordinal it
    could invent, which was `0`. Three files, one wrong answer, and the
    tests that pinned the identity never saw any of them because they
    checked `finding_fingerprints`.

    `_identity` itself is exempt: the population logic lives there, and
    the tests above hold its behaviour directly. Everywhere else, a
    literal ordinal means the population was not consulted. The remedy is
    `declaration_identities` / `risk_identities` — look the identity up,
    do not derive it.
    """
    import ast

    package = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"
    builders = {"declaration_fingerprint", "risk_fingerprint"}
    offenders: list[str] = []

    for module in sorted(package.glob("*.py")):
        if module.name == "_identity.py":
            continue
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name not in builders:
                continue
            literals = [
                arg.value for arg in node.args
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int)
            ]
            if literals:
                offenders.append(f"{module.name}:{node.lineno} {name}(..., {literals[0]})")

    assert not offenders, (
        "an ordinal was hardcoded instead of computed over the population, "
        "which merges same-named declarations in one file into a single "
        "finding:\n  " + "\n  ".join(offenders)
        + "\nUse declaration_identities(report) / risk_identities(report)."
    )
