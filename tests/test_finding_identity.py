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
