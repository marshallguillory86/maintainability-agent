"""ADR 009: findings resolve across renames and same-name reordering."""

from __future__ import annotations

import ast
import json
import subprocess
import textwrap
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from maintainability_audit._finding_match import (
    Identity,
    identities_from_report,
    rename_map,
    same_finding,
    unmatched,
)
from maintainability_audit._recurrence import Outcome, outcomes, recurrence
from maintainability_audit._scan_history import Segment, record_of
from maintainability_audit.baseline import (
    BASELINE_VERSION,
    StaleBaseline,
    findings_not_in_baseline,
    load_baseline,
    load_baseline_identities,
    write_baseline,
)
from maintainability_audit.config import VERSION, load_config
from maintainability_audit.report import build_report

ROOT = Path(__file__).resolve().parents[1]
LONG_LINES = 90


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    return root


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", message)
    return _git(root, "rev-parse", "HEAD")


def _huge(name: str = "huge", marker: int = 0) -> str:
    body = "\n".join(f"    value_{marker}_{line} = {line}" for line in range(LONG_LINES))
    return f"def {name}():\n{body}\n    return {marker}\n"


def _report(root: Path) -> dict:
    return build_report(root, load_config(None))


def _declarations(report: dict, name: str | None = None) -> frozenset[Identity]:
    return frozenset(
        identity
        for identity in identities_from_report(report)
        if identity.kind == "declaration" and (name is None or identity.name == name)
    )


def _record(report: dict, *, targeted: tuple[str, ...] = ()):
    config = load_config(None)
    record = record_of(report, config, VERSION, 2.6279, targeted)
    return replace(record, targeted=targeted)


def test_git_mv_of_a_failing_function_is_neither_new_nor_cleared(tmp_path: Path) -> None:
    root = _repo(tmp_path, "function-rename")
    (root / "old.py").write_text(_huge(), encoding="utf-8")
    old_commit = _commit(root, "old path")
    before = _report(root)
    baseline = tmp_path / "baseline.json"
    write_baseline(str(baseline), before)
    old_label = next(iter(_declarations(before))).fingerprint

    _git(root, "mv", "old.py", "new.py")
    new_commit = _commit(root, "rename")
    after = _report(root)
    segment = Segment(records=[
        _record(before, targeted=(old_label,)),
        _record(after),
    ])

    assert not findings_not_in_baseline(after, str(baseline), root)
    assert not recurrence(segment, root=root)
    assert outcomes(segment, root=root)[old_label] is Outcome.NEVER_CLEARED
    assert rename_map(root, old_commit, new_commit) == {"old.py": "new.py"}


def test_git_mv_of_an_oversized_file_is_not_new(tmp_path: Path) -> None:
    root = _repo(tmp_path, "file-rename")
    (root / "old.py").write_text("\n".join("# line" for _ in range(850)), encoding="utf-8")
    _commit(root, "old path")
    before = _report(root)
    baseline = tmp_path / "file-baseline.json"
    write_baseline(str(baseline), before)
    assert any(identity.kind == "file" for identity in identities_from_report(before))

    _git(root, "mv", "old.py", "new.py")
    _commit(root, "rename")
    after = _report(root)

    assert not findings_not_in_baseline(after, str(baseline), root)


def test_swapping_same_named_declarations_matches_both_by_body(tmp_path: Path) -> None:
    root = _repo(tmp_path, "swap")
    (root / "same.py").write_text(_huge(marker=1) + "\n" + _huge(marker=2), encoding="utf-8")
    _commit(root, "before")
    known = _declarations(_report(root), "huge")
    assert len(known) == 2

    (root / "same.py").write_text(_huge(marker=2) + "\n" + _huge(marker=1), encoding="utf-8")
    _commit(root, "swap")
    current = _declarations(_report(root), "huge")

    assert not unmatched(current, known, {})


def test_inserting_same_named_sibling_leaves_only_the_new_one_unmatched(tmp_path: Path) -> None:
    root = _repo(tmp_path, "insert")
    original = _huge(marker=1) + "\n" + _huge(marker=2)
    (root / "same.py").write_text(original, encoding="utf-8")
    _commit(root, "two")
    known = _declarations(_report(root), "huge")

    (root / "same.py").write_text(_huge(marker=3) + "\n" + original, encoding="utf-8")
    _commit(root, "three")
    current = _declarations(_report(root), "huge")
    new = unmatched(current, known, {})

    assert len(new) == 1
    assert next(iter(new)).body_digest not in {identity.body_digest for identity in known}


def test_editing_a_still_failing_body_matches_by_ordinal(tmp_path: Path) -> None:
    root = _repo(tmp_path, "body-edit")
    (root / "hot.py").write_text(_huge(marker=1), encoding="utf-8")
    _commit(root, "before")
    known = _declarations(_report(root), "huge")

    (root / "hot.py").write_text(_huge(marker=9), encoding="utf-8")
    _commit(root, "after")
    current = _declarations(_report(root), "huge")

    assert {item.body_digest for item in current} != {item.body_digest for item in known}
    assert not unmatched(current, known, {})


def test_reindent_only_preserves_the_body_digest_and_match(tmp_path: Path) -> None:
    root = _repo(tmp_path, "reindent")
    source = _huge(marker=1)
    (root / "hot.py").write_text(source, encoding="utf-8")
    _commit(root, "before")
    known = _declarations(_report(root), "huge")

    (root / "hot.py").write_text("if True:\n" + textwrap.indent(source, "    "), encoding="utf-8")
    _commit(root, "after")
    current = _declarations(_report(root), "huge")

    assert {item.body_digest for item in current} == {item.body_digest for item in known}
    assert not unmatched(current, known, {})


def test_renaming_a_declaration_never_matches_on_digest_alone(tmp_path: Path) -> None:
    root = _repo(tmp_path, "declaration-rename")
    (root / "hot.py").write_text(_huge("huge"), encoding="utf-8")
    _commit(root, "before")
    known = next(iter(_declarations(_report(root))))

    (root / "hot.py").write_text(_huge("enormous"), encoding="utf-8")
    _commit(root, "after")
    current = next(iter(_declarations(_report(root))))
    known_with_same_digest = replace(known, body_digest=current.body_digest)

    assert not same_finding(current, known_with_same_digest, {})


def test_copy_without_git_rename_is_new(tmp_path: Path) -> None:
    root = _repo(tmp_path, "copy")
    source = _huge()
    (root / "original.py").write_text(source, encoding="utf-8")
    old_commit = _commit(root, "one")
    known = _declarations(_report(root))

    (root / "copy.py").write_text(source, encoding="utf-8")
    new_commit = _commit(root, "copy")
    current = _declarations(_report(root))
    renames = rename_map(root, old_commit, new_commit)
    new = unmatched(current, known, renames)

    assert not renames
    assert len(new) == 1
    assert next(iter(new)).path == "copy.py"


def test_baseline_v3_round_trips_structured_identities_and_rejects_v2(tmp_path: Path) -> None:
    stale = tmp_path / "v2.json"
    stale.write_text(json.dumps({"version": 2, "findings": []}), encoding="utf-8")
    with pytest.raises(StaleBaseline, match="version 3"):
        load_baseline(str(stale))

    root = _repo(tmp_path, "baseline")
    (root / "hot.py").write_text(_huge(), encoding="utf-8")
    commit = _commit(root, "finding")
    report = _report(root)
    path = tmp_path / "v3.json"
    write_baseline(str(path), report)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert BASELINE_VERSION == 3
    assert payload["version"] == 3
    assert payload["commit"] == commit
    assert payload["identities"]
    assert set(payload["identities"][0]) == {
        "kind", "path", "name", "ordinal", "body_digest", "fingerprint",
    }
    assert load_baseline_identities(str(path)) == identities_from_report(report)
    assert load_baseline(str(path)) == {i.fingerprint for i in identities_from_report(report)}


def test_structured_identity_uses_the_four_governing_kinds() -> None:
    report = {
        "largest_files": [{"path": "large.py", "status": "fail"}],
        "function_hotspots": [{
            "path": "hot.py", "name": "huge", "start_line": 1,
            "status": "fail", "body_digest": "abc123",
        }],
        "risk_findings": [{
            "path": "risk.py", "name": "debt-marker", "line": 2, "text": "TODO",
        }],
        "duplicate_blocks": [{
            "locations": ["a.py:1", "b.py:2"], "sample": "same",
        }],
    }

    assert {identity.kind for identity in identities_from_report(report)} == {
        "declaration", "file", "risk", "duplicate",
    }


def test_new_history_records_store_schema_three_identities(tmp_path: Path) -> None:
    root = _repo(tmp_path, "history")
    (root / "hot.py").write_text(_huge(), encoding="utf-8")
    _commit(root, "finding")
    report = _report(root)
    record = _record(report)
    payload = json.loads(record.as_line())

    assert payload["history_schema_version"] == 3
    assert payload["identities"] == [asdict(i) for i in sorted(
        identities_from_report(report), key=lambda item: item.fingerprint
    )]


def test_fail_on_new_uses_structured_matching_not_a_label_set_difference() -> None:
    package = ROOT / "src" / "maintainability_audit"
    offenders: list[str] = []
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Sub):
                continue
            if (
                isinstance(node.left, ast.Call)
                and isinstance(node.left.func, ast.Name)
                and node.left.func.id == "finding_fingerprints"
            ):
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, f"label-set finding comparison remains at {offenders}"

    cli_tree = ast.parse((package / "cli.py").read_text(encoding="utf-8"))
    audit_exit = next(
        node for node in cli_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "audit_exit_code"
    )
    calls = {
        node.func.id
        for node in ast.walk(audit_exit)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "findings_not_in_baseline" in calls
    assert "finding_fingerprints" not in calls


def test_hotspot_digests_are_scan_time_data_and_identity_never_reads_source(tmp_path: Path) -> None:
    root = _repo(tmp_path, "digests")
    (root / "warn.py").write_text(
        "def warm():\n" + "\n".join(f"    value_{n} = {n}" for n in range(55)) + "\n",
        encoding="utf-8",
    )
    (root / "fail.py").write_text(_huge(), encoding="utf-8")
    _commit(root, "hotspots")
    hotspots = [item for item in _report(root)["function_hotspots"]
                if item["status"] in {"warn", "fail"}]

    assert {item["status"] for item in hotspots} == {"warn", "fail"}
    assert all(item.get("body_digest") for item in hotspots)

    tree = ast.parse(
        (ROOT / "src" / "maintainability_audit" / "_identity.py").read_text(encoding="utf-8")
    )
    forbidden = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"open", "read_text"}
    }
    assert not forbidden, "_identity must consume report digests, not reopen the audited tree"
