"""The D12 drift fix: one skill, shipped in the package, synced on command.

Found in the field (2026-08-19): the repository's skill went
chat-primary while the installed copy kept teaching the dead CLI-first
recipe for three days. Three commitments: the packaged copy is pinned
byte-for-byte to the repository's skills tree, --install-skill writes
the chat-primary skill where agents read it, and re-running overwrites
local drift.
"""

from __future__ import annotations

from pathlib import Path

from maintainability_audit.cli import main

ROOT = Path(__file__).resolve().parents[1]
REPO_SKILL = ROOT / "skills" / "maintainability-agent"
PACKAGED = ROOT / "src" / "maintainability_audit" / "_skill_data"


def _files(base: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(base).as_posix()): path.read_bytes()
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def test_packaged_skill_is_byte_identical_to_the_repository_skill() -> None:
    """The internal drift lint: two copies, one honest state."""
    repo = _files(REPO_SKILL)
    packaged = _files(PACKAGED)
    assert repo.keys() == packaged.keys(), (
        f"file sets differ: only-repo={sorted(repo.keys() - packaged.keys())} "
        f"only-packaged={sorted(packaged.keys() - repo.keys())}"
    )
    drifted = [name for name in repo if repo[name] != packaged[name]]
    assert not drifted, f"packaged skill drifted from skills/: {drifted}"


def test_install_skill_writes_the_chat_primary_skill(tmp_path: Path) -> None:
    exit_code = main(["--install-skill", "--skills-dir", str(tmp_path)])
    assert exit_code == 0

    installed = tmp_path / "maintainability-agent" / "SKILL.md"
    assert installed.is_file()
    text = installed.read_text(encoding="utf-8")
    assert "Chat is the primary surface" in text, (
        "the installed skill must teach the chat-primary flow, not the "
        "CLI-first recipe the field test caught"
    )
    assert _files(tmp_path / "maintainability-agent").keys() == _files(PACKAGED).keys()


def test_reinstall_overwrites_local_drift(tmp_path: Path) -> None:
    """An installed skill has one honest state: identical to the packaged one."""
    assert main(["--install-skill", "--skills-dir", str(tmp_path)]) == 0
    installed = tmp_path / "maintainability-agent" / "SKILL.md"
    installed.write_text("# locally drifted\n", encoding="utf-8")

    assert main(["--install-skill", "--skills-dir", str(tmp_path)]) == 0

    assert installed.read_bytes() == (PACKAGED / "SKILL.md").read_bytes(), (
        "re-running --install-skill did not sync a drifted copy"
    )
