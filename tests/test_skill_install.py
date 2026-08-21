"""The D12 drift fix: one skill, shipped in the package, synced on command.

Found in the field (2026-08-19): the repository's skill went
chat-primary while the installed copy kept teaching the dead CLI-first
recipe for three days. Re-keyed by the Codex audit on d5b1c50: sync
means byte-identical including deletions (M3), and a differing copy is
refused with the list unless forced (M5) — overwriting someone's edits
without consent is not a sync.
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


def test_a_differing_copy_is_refused_without_force(tmp_path: Path) -> None:
    """Audit M5: edits are someone's work; destroying them needs consent."""
    assert main(["--install-skill", "--skills-dir", str(tmp_path)]) == 0
    installed = tmp_path / "maintainability-agent" / "SKILL.md"
    installed.write_text("# locally edited\n", encoding="utf-8")

    assert main(["--install-skill", "--skills-dir", str(tmp_path)]) == 1, (
        "a drifted copy was overwritten without --force-skill"
    )
    assert installed.read_text(encoding="utf-8") == "# locally edited\n"


def test_force_syncs_edits_and_deletions_to_the_packaged_state(tmp_path: Path) -> None:
    """Audit M3+M5: forced sync means byte-identical — leftovers removed."""
    assert main(["--install-skill", "--skills-dir", str(tmp_path)]) == 0
    target = tmp_path / "maintainability-agent"
    (target / "SKILL.md").write_text("# drifted\n", encoding="utf-8")
    obsolete = target / "obsolete-from-old-version.md"
    obsolete.write_text("stale\n", encoding="utf-8")

    assert main(["--install-skill", "--skills-dir", str(tmp_path),
                 "--force-skill"]) == 0

    assert _files(target) == _files(PACKAGED), (
        "forced sync did not restore the packaged state exactly"
    )
    assert not obsolete.exists(), (
        "a file the package no longer ships survived the sync (M3)"
    )


def test_an_identical_copy_reinstalls_without_force(tmp_path: Path) -> None:
    """Identical is not drift: the plain command stays usable for upgrades."""
    assert main(["--install-skill", "--skills-dir", str(tmp_path)]) == 0
    assert main(["--install-skill", "--skills-dir", str(tmp_path)]) == 0
