"""Executable checks for the authorship-attestation workflow.

The workflow is shell code with repository-protection authority.  These tests
run the three scripts against small, real Git repositories instead of merely
asserting that familiar strings still occur in YAML.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "authorship.yml"
PERSONAL_EMAIL = "152444602+marshallguillory86@users.noreply.github.com"


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run Git in a synthetic repository without borrowing its user config."""
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _require_git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = _git(repo, *args, env=env)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _step_scripts() -> dict[str, str]:
    """Extract the three literal run blocks with the constrained YAML shape here.

    Tests intentionally do not depend on PyYAML.  The workflow's relevant
    grammar is limited to named steps and ``run: |`` bodies; a shape change
    makes this parser return no matching step and fails loudly.
    """
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    job_name = "    name: Every commit declares who wrote it"
    start = lines.index(job_name)
    steps = lines.index("    steps:", start)
    scripts: dict[str, str] = {}
    index = steps + 1
    while index < len(lines):
        if lines[index] and not lines[index].startswith("      "):
            break
        match = re.match(r"^      - name: (.+)$", lines[index])
        if not match:
            index += 1
            continue
        name = match.group(1)
        index += 1
        while index < len(lines) and not re.match(r"^      - name: ", lines[index]):
            if lines[index] == "        run: |":
                body: list[str] = []
                index += 1
                while index < len(lines) and (
                    not lines[index] or lines[index].startswith("          ")
                ):
                    body.append(lines[index])
                    index += 1
                scripts[name] = "\n".join(
                    line[10:] if line.startswith("          ") else line for line in body
                )
                break
            index += 1
    assert scripts.keys() == {
        "Each commit carries an Agent trailer",
        "Each commit carries the personal identity, never the work one",
        "Each commit is signed, so its Agent trailer is attested",
    }
    return scripts


SCRIPTS = _step_scripts()


def _run_gate(repo: Path, name: str) -> subprocess.CompletedProcess[str]:
    """Substitute the only Actions expression used by the checked script."""
    script = SCRIPTS[name].replace("${{ github.base_ref }}", "main")
    return subprocess.run(
        ["bash", "-c", script],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.fixture
def signed_repo(tmp_path: Path) -> tuple[Path, Callable[..., str]]:
    """A topic repository with an SSH signing key trusted only by itself."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _require_git(repo, "init", "--initial-branch=main")
    _require_git(repo, "config", "user.name", "Marshall Guillory")
    _require_git(repo, "config", "user.email", PERSONAL_EMAIL)
    key = tmp_path / "signing_key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        text=True,
        capture_output=True,
        check=True,
    )
    _require_git(repo, "config", "gpg.format", "ssh")
    _require_git(repo, "config", "user.signingkey", str(key))
    (repo / ".github").mkdir()
    public_key = key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    (repo / ".github" / "allowed_signers").write_text(
        f"{PERSONAL_EMAIL} {public_key}\n", encoding="utf-8"
    )
    (repo / "base").write_text("base\n", encoding="utf-8")
    _require_git(repo, "add", ".")
    _require_git(repo, "commit", "-m", "base")
    base = _require_git(repo, "rev-parse", "HEAD")
    _require_git(repo, "update-ref", "refs/remotes/origin/main", base)

    counter = 0

    def commit(
        *,
        agent: str = "codex",
        signed: bool = True,
        author: str = PERSONAL_EMAIL,
        committer: str = PERSONAL_EMAIL,
    ) -> str:
        nonlocal counter
        counter += 1
        (repo / f"change-{counter}").write_text(f"{counter}\n", encoding="utf-8")
        _require_git(repo, "add", ".")
        result = _git(
            repo,
            "-c",
            f"user.email={committer}",
            "-c",
            "user.name=Marshall Guillory",
            "commit",
            "-S" if signed else "--no-gpg-sign",
            "--author",
            f"Marshall Guillory <{author}>",
            "-m",
            f"change {counter}\n\nAgent: {agent}",
            env={**os.environ, "GIT_IDENTITY_OVERRIDE": "1"}
            if committer != PERSONAL_EMAIL
            else None,
        )
        assert result.returncode == 0, result.stderr
        return _require_git(repo, "rev-parse", "HEAD")

    return repo, commit


def test_fixture_commits_ignore_ambient_global_signing(tmp_path: Path) -> None:
    """The suite must work for developers following machine-setup section 2."""
    repo = tmp_path / "fixture"
    repo.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / "xdg")}
    _require_git(repo, "init", env=env)
    _require_git(repo, "config", "--global", "commit.gpgsign", "true", env=env)
    (repo / "fixture").write_text("fixture\n", encoding="utf-8")
    _require_git(repo, "add", ".", env=env)

    result = _git(
        repo,
        "-c",
        f"user.email={PERSONAL_EMAIL}",
        "-c",
        "user.name=Fixture",
        "commit",
        "-m",
        "fixture",
        env=env,
    )

    assert result.returncode == 0, result.stderr


def test_signed_agent_commit_passes_every_gate(signed_repo: tuple[Path, Callable[..., str]]) -> None:
    repo, commit = signed_repo
    commit()

    for name in SCRIPTS:
        result = _run_gate(repo, name)
        assert result.returncode == 0, f"{name}: {result.stdout}\n{result.stderr}"


def test_unsigned_commit_fails_signature_as_n(signed_repo: tuple[Path, Callable[..., str]]) -> None:
    repo, commit = signed_repo
    commit(signed=False)

    result = _run_gate(repo, "Each commit is signed, so its Agent trailer is attested")

    assert result.returncode == 1
    assert "unsigned" in result.stdout


def test_edited_signed_trailer_fails_signature_as_b(
    signed_repo: tuple[Path, Callable[..., str]],
) -> None:
    repo, commit = signed_repo
    sha = commit(agent="claude")
    payload = _require_git(repo, "cat-file", "commit", sha).replace("Agent: claude", "Agent: grok")
    altered = subprocess.run(
        ["git", "hash-object", "-w", "-t", "commit", "--stdin"],
        cwd=repo,
        input=payload,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    _require_git(repo, "reset", "--hard", altered)

    result = _run_gate(repo, "Each commit is signed, so its Agent trailer is attested")

    assert result.returncode == 1
    assert "BAD signature" in result.stdout


def test_untrusted_signing_key_fails_as_u(signed_repo: tuple[Path, Callable[..., str]]) -> None:
    repo, commit = signed_repo
    commit()
    (repo / ".github" / "allowed_signers").write_text("", encoding="utf-8")

    result = _run_gate(repo, "Each commit is signed, so its Agent trailer is attested")

    assert result.returncode == 1
    assert "signature state 'U'" in result.stdout


def test_empty_range_fails_all_three_gates(signed_repo: tuple[Path, Callable[..., str]]) -> None:
    repo, _commit = signed_repo

    for name in SCRIPTS:
        result = _run_gate(repo, name)
        assert result.returncode == 1, name
        assert "this check proved nothing" in result.stdout


@pytest.mark.parametrize(
    ("agent", "expected_returncode"),
    [("codex ", 0), ("Codex", 1)],
)
def test_agent_trailer_whitespace_is_normalized_but_case_is_not(
    signed_repo: tuple[Path, Callable[..., str]], agent: str, expected_returncode: int
) -> None:
    repo, commit = signed_repo
    commit(agent=agent)

    result = _run_gate(repo, "Each commit carries an Agent trailer")

    assert result.returncode == expected_returncode


def test_wrong_committer_fails_identity_gate(signed_repo: tuple[Path, Callable[..., str]]) -> None:
    repo, commit = signed_repo
    commit(committer="wrong@example.com")

    result = _run_gate(repo, "Each commit carries the personal identity, never the work one")

    assert result.returncode == 1
    assert "committer: wrong@example.com" in result.stdout


def test_partly_unsigned_range_fails_signature_gate(
    signed_repo: tuple[Path, Callable[..., str]],
) -> None:
    repo, commit = signed_repo
    commit()
    commit(signed=False)

    result = _run_gate(repo, "Each commit is signed, so its Agent trailer is attested")

    assert result.returncode == 1
    assert "unsigned" in result.stdout


def test_unsigned_merge_commit_fails_the_signature_gate(
    signed_repo: tuple[Path, Callable[..., str]],
) -> None:
    repo, commit = signed_repo
    commit()
    _require_git(repo, "branch", "side", "HEAD")
    _require_git(repo, "reset", "--hard", "origin/main")
    _require_git(repo, "merge", "--no-ff", "side", "-m", "merge side")

    assert _require_git(repo, "log", "-1", "--format=%G?") == "N"
    result = _run_gate(repo, "Each commit is signed, so its Agent trailer is attested")

    assert result.returncode == 1, (
        "the gate skipped an unsigned merge commit; conflict-resolution content "
        "in that commit was never attested\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_the_signature_gate_still_checks_merge_commits() -> None:
    """D105. The control someone will be tempted to remove.

    The trailer step uses `--no-merges`; the signature step deliberately
    does not, because a merge carries the conflict resolution its author
    wrote — an unsigned merge is unattested content, and skipping it let
    exactly that through once already.

    The temptation is concrete. `gh pr update-branch` and GitHub's green
    "Update branch" button create a merge signed with GitHub's key, which
    is not in `.github/allowed_signers`, so the gate fails on a commit no
    agent wrote. The convenient fix is to add `--no-merges` here, and it
    would undo the control to buy a button. The answer is to rebase
    instead, and this pins the control so the shortcut fails loudly.

    Covers existing behaviour: the control it pins is older than this
    change and nothing here edited the workflow, so no revert can make it
    fail. It defends a future edit rather than one made now — which is
    the point of it.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.split("Each commit is signed", 1)
    assert len(step) > 1, "the signature step is no longer named that way"
    body = step[1]
    enumerated = [
        line for line in body.splitlines()
        if "git rev-list" in line and "if [" not in line
    ]
    assert enumerated, "the signature step no longer enumerates commits"
    assert not any("--no-merges" in line for line in enumerated), (
        "the signature step skips merge commits again. A merge carries "
        "the conflict resolution its author wrote; rebase a stale branch "
        "rather than weakening this to make 'Update branch' pass (D105)."
    )
