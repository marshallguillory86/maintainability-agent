"""The D12 drift fix: one skill, shipped in the package, synced on command.

Found in the field (2026-08-19): the repository's skill went
chat-primary while the installed copy kept teaching the dead CLI-first
recipe for three days. Re-keyed by the Codex audit on d5b1c50: sync
means byte-identical including deletions (M3), and a differing copy is
refused with the list unless forced (M5) — overwriting someone's edits
without consent is not a sync.
"""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

import pytest

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


def test_a_symlinked_target_is_drift_and_is_never_written_through(
    tmp_path: Path,
) -> None:
    """Audit M3: writing through a symlink is an out-of-directory write."""
    assert main(["--install-skill", "--skills-dir", str(tmp_path)]) == 0
    target = tmp_path / "maintainability-agent"
    outside = tmp_path / "someone-elses-file.md"
    outside.write_text("do not touch\n", encoding="utf-8")
    skill = target / "SKILL.md"
    skill.unlink()
    skill.symlink_to(outside)

    assert main(["--install-skill", "--skills-dir", str(tmp_path)]) == 1, (
        "a symlinked target was not treated as drift"
    )
    assert outside.read_text(encoding="utf-8") == "do not touch\n"

    assert main(["--install-skill", "--skills-dir", str(tmp_path),
                 "--force-skill"]) == 0
    assert outside.read_text(encoding="utf-8") == "do not touch\n", (
        "forced sync wrote through the symlink to a file outside the "
        "skills directory"
    )
    assert not skill.is_symlink()
    assert skill.read_bytes() == (PACKAGED / "SKILL.md").read_bytes()


def test_a_symlinked_skill_root_is_drift_and_its_destination_is_untouched(
    tmp_path: Path,
) -> None:
    """Audit round three: the root link itself, not just files under it.

    Following it would populate — or delete inside — a directory
    outside the skills tree. Plain install refuses without touching the
    destination; forced sync unlinks the link, makes a real directory,
    and leaves the former destination exactly as it was.
    """
    skills = tmp_path / "skills"
    skills.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    sentinel = elsewhere / "someone-elses-notes.md"
    sentinel.write_text("do not touch\n", encoding="utf-8")
    (skills / "maintainability-agent").symlink_to(elsewhere)

    assert main(["--install-skill", "--skills-dir", str(skills)]) == 1, (
        "a symlinked skill root was not treated as drift"
    )
    assert sentinel.read_text(encoding="utf-8") == "do not touch\n"
    assert not (elsewhere / "SKILL.md").exists(), (
        "the refusal wrote into the symlink destination"
    )

    assert main(["--install-skill", "--skills-dir", str(skills),
                 "--force-skill"]) == 0
    target = skills / "maintainability-agent"
    assert target.is_dir() and not target.is_symlink()
    assert _files(target) == _files(PACKAGED)
    assert sentinel.read_text(encoding="utf-8") == "do not touch\n", (
        "forced sync modified the former symlink destination"
    )
    assert not (elsewhere / "SKILL.md").exists()


def test_the_validated_root_is_bound_by_descriptor_not_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D18: swapping the root between check and write cannot redirect it.

    The installer validated a pathname and then wrote to it. An audit
    swapped an identical installed directory for a symlink in that
    window and a plain reinstall wrote through to an external file.
    The root is now opened once with O_NOFOLLOW and every write goes
    through that descriptor, so the swap can no longer be followed.
    """
    from maintainability_audit import _skill_install

    skills = tmp_path / "skills"
    skills.mkdir()
    assert main(["--install-skill", "--skills-dir", str(skills)]) == 0
    target = skills / "maintainability-agent"

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    sentinel = elsewhere / "SKILL.md"
    sentinel.write_text("do not touch\n", encoding="utf-8")

    real_drift = _skill_install._drift

    def swap_then_check(*args, **kwargs):
        # The exact window the audit exploited: the tree has been read
        # and judged, the write has not happened yet.
        result = real_drift(*args, **kwargs)
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
            target.symlink_to(elsewhere)
        return result

    monkeypatch.setattr(_skill_install, "_drift", swap_then_check)
    exit_code = main(["--install-skill", "--skills-dir", str(skills)])

    assert exit_code == 1, "a target that changed under the write reported success"
    assert sentinel.read_text(encoding="utf-8") == "do not touch\n", (
        "the installer followed a root swapped after validation and "
        "overwrote a file outside the skills directory"
    )


def test_a_nested_symlink_in_an_empty_root_still_needs_consent(
    tmp_path: Path,
) -> None:
    """D19: the refusal counted regular files only, so this slipped past."""
    skills = tmp_path / "skills"
    target = skills / "maintainability-agent"
    target.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "notes.md").write_text("keep\n", encoding="utf-8")
    (target / "references").symlink_to(elsewhere)

    assert main(["--install-skill", "--skills-dir", str(skills)]) == 1, (
        "a nested symlink in an otherwise empty root was removed "
        "without consent"
    )
    assert (target / "references").is_symlink()
    assert (elsewhere / "notes.md").read_text(encoding="utf-8") == "keep\n"

    assert main(["--install-skill", "--skills-dir", str(skills),
                 "--force-skill"]) == 0
    assert not (target / "references").is_symlink()
    assert _files(target) == _files(PACKAGED)
    assert (elsewhere / "notes.md").read_text(encoding="utf-8") == "keep\n"


def test_missing_root_swap_never_falls_back_to_process_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D18: a failed rebind must refuse, not resolve against the CWD.

    With no target, the installer creates the directory and binds it
    again. If that second bind fails, `dir_fd=None` sends every write
    to the PROCESS WORKING DIRECTORY — an audit found a stray SKILL.md
    there.
    """
    from maintainability_audit import _skill_install

    skills = tmp_path / "skills"
    skills.mkdir()
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    real_bind = _skill_install._bind_root
    calls: list[int] = []

    def failing_rebind(target_root):
        calls.append(1)
        return None if len(calls) > 1 else real_bind(target_root)

    monkeypatch.setattr(_skill_install, "_bind_root", failing_rebind)
    exit_code = main(["--install-skill", "--skills-dir", str(skills)])

    assert exit_code == 1, "a failed rebind reported success"
    assert not (workdir / "SKILL.md").exists(), (
        "the installer wrote into the process working directory"
    )
    assert not list(workdir.iterdir()), f"stray files: {list(workdir.iterdir())}"


def test_leaf_hardlink_swap_cannot_modify_external_file(tmp_path: Path) -> None:
    """D18: O_NOFOLLOW does not stop a HARD link; a rename does."""
    skills = tmp_path / "skills"
    skills.mkdir()
    assert main(["--install-skill", "--skills-dir", str(skills)]) == 0
    target = skills / "maintainability-agent"

    external = tmp_path / "external.md"
    external.write_text("someone else's file\n", encoding="utf-8")
    (target / "SKILL.md").unlink()
    os.link(external, target / "SKILL.md")

    assert main(["--install-skill", "--skills-dir", str(skills),
                 "--force-skill"]) == 0

    assert external.read_text(encoding="utf-8") == "someone else's file\n", (
        "the installer wrote through a hard link into an external file"
    )
    assert (target / "SKILL.md").read_bytes() == (PACKAGED / "SKILL.md").read_bytes()


def test_short_write_is_completed_or_refused_without_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D18: os.write may write less than asked; success must mean complete."""
    from maintainability_audit import _skill_install

    skills = tmp_path / "skills"
    skills.mkdir()
    real_write = os.write
    budget = {"first": True}

    def short_write(fd: int, data: bytes) -> int:
        if budget["first"] and len(data) > 16:
            budget["first"] = False
            return real_write(fd, data[:16])
        return real_write(fd, data)

    monkeypatch.setattr(_skill_install.os, "write", short_write)
    exit_code = main(["--install-skill", "--skills-dir", str(skills)])

    installed = skills / "maintainability-agent" / "SKILL.md"
    if exit_code == 0:
        assert installed.read_bytes() == (PACKAGED / "SKILL.md").read_bytes(), (
            "a truncated file was installed while reporting success"
        )
    else:
        assert not installed.exists() or installed.read_bytes() == b""


def test_empty_subdirectory_counts_as_occupied(tmp_path: Path) -> None:
    """D19: 'anything already present' includes an empty directory."""
    skills = tmp_path / "skills"
    target = skills / "maintainability-agent"
    (target / "leftover").mkdir(parents=True)

    assert main(["--install-skill", "--skills-dir", str(skills)]) == 1, (
        "an empty subdirectory was treated as a fresh install"
    )
    assert (target / "leftover").is_dir()

    assert main(["--install-skill", "--skills-dir", str(skills),
                 "--force-skill"]) == 0
    assert not (target / "leftover").exists()
    assert _files(target) == _files(PACKAGED)


def test_fifo_counts_as_occupied_without_blocking(tmp_path: Path) -> None:
    """D19: a FIFO is occupancy, and opening one would hang forever."""
    skills = tmp_path / "skills"
    target = skills / "maintainability-agent"
    target.mkdir(parents=True)
    os.mkfifo(target / "SKILL.md")

    assert main(["--install-skill", "--skills-dir", str(skills)]) == 1, (
        "a FIFO was treated as a fresh install"
    )
    assert stat.S_ISFIFO(os.stat(target / "SKILL.md", follow_symlinks=False).st_mode)

    assert main(["--install-skill", "--skills-dir", str(skills),
                 "--force-skill"]) == 0
    assert _files(target) == _files(PACKAGED)


def test_socket_counts_as_occupied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D19: sockets were ignored identically to FIFOs."""
    import socket

    skills = tmp_path / "skills"
    target = skills / "maintainability-agent"
    target.mkdir(parents=True)
    endpoint = socket.socket(socket.AF_UNIX)
    try:
        # AF_UNIX paths are capped near 104 bytes and pytest's tmp_path
        # is longer than that; bind by a relative name from inside.
        monkeypatch.chdir(target)
        endpoint.bind("listener.sock")

        assert main(["--install-skill", "--skills-dir", str(skills)]) == 1, (
            "a socket was treated as a fresh install"
        )
        assert main(["--install-skill", "--skills-dir", str(skills),
                     "--force-skill"]) == 0
        assert _files(target) == _files(PACKAGED)
    finally:
        endpoint.close()


def test_force_refuses_or_safely_removes_special_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D19: forced sync clears what it understands and refuses what it does not."""
    from maintainability_audit._skill_install import SkillDrift, _remove_at

    skills = tmp_path / "skills"
    target = skills / "maintainability-agent"
    target.mkdir(parents=True)
    os.mkfifo(target / "pipe")
    (target / "empty").mkdir()

    assert main(["--install-skill", "--skills-dir", str(skills),
                 "--force-skill"]) == 0
    assert _files(target) == _files(PACKAGED)
    assert not (target / "pipe").exists() and not (target / "empty").exists()

    # A kind this tool does not understand — a device node, say — is
    # refused by name rather than deleted on a guess.
    handle = os.open(target, os.O_RDONLY | os.O_DIRECTORY)
    try:
        real_stat = os.stat

        def as_device(name, *args, **kwargs):
            info = real_stat(name, *args, **kwargs)
            return os.stat_result((
                stat.S_IFBLK | 0o600, *tuple(info)[1:],
            ))

        monkeypatch.setattr(os, "stat", as_device)
        with pytest.raises(SkillDrift):
            _remove_at(handle, "SKILL.md")
    finally:
        monkeypatch.undo()
        os.close(handle)
    assert (target / "SKILL.md").exists(), "the refused entry was removed anyway"
