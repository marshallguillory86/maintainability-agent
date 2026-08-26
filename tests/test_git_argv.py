"""D37: what this package hands git, and what it does with git's failures.

Four properties, because D37 named four faults in one entry: an
unvalidated revspec reaching git as an option, a failure returning as an
empty answer, an unbounded child, and an inherited `GIT_DIR` outranking
the `cwd` and `-C` that were supposed to bind the repository.

The last two are swept over the package rather than asserted for the two
spawners that exist today. Both were closed once at the MCP door and
left open at the CLI, which is the shape this project keeps re-learning:
lint the class, not the instance.
"""

from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._backfill import commits_in_range
from maintainability_audit.git_tools import (
    GIT_TIMEOUT_SECONDS,
    GitCommandFailed,
    InvalidRevspec,
    changed_paths,
    git_env,
    probe_git,
    run_git,
    validate_revspec,
)

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"


def _repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "one"], check=True)
    return root


OPTION_SHAPED = [
    "--output=stolen.txt",     # the demonstrated one: git creates that file
    "--exit-code",
    "-rf",                     # a leading dash the first draft of the regex admitted
    "--upload-pack=touch pwn",
    "-",
]


@pytest.mark.parametrize("revspec", OPTION_SHAPED)
def test_an_option_shaped_revspec_never_reaches_git(revspec: str, tmp_path: Path) -> None:
    """The demonstrated instance created a file. The class is refused.

    `changed_paths(repo, "--output=<path>")` created that path, because
    git reads it as an option. No shell is involved and none is needed;
    argv alone is enough.
    """
    root = _repo(tmp_path / "repo")
    before = set(os.listdir(root))

    with pytest.raises(InvalidRevspec):
        changed_paths(root, revspec)
    with pytest.raises(ValueError):  # commits_in_range re-wraps it
        commits_in_range(root, revspec)

    assert set(os.listdir(root)) == before, (
        f"{revspec!r} reached git and changed the working tree"
    )
    assert not (root / "stolen.txt").exists()


def test_a_real_revspec_still_works(tmp_path: Path) -> None:
    """The guard has to admit the thing it exists to protect."""
    root = _repo(tmp_path / "repo")
    for good in ("HEAD", "HEAD~1..HEAD", "main", "v1.0.0", "abc123", "HEAD^"):
        assert validate_revspec(good) == good
    assert changed_paths(root, "HEAD") == set()


def test_a_failed_git_command_is_not_an_empty_answer(tmp_path: Path) -> None:
    """`run_git` raises; only `probe_git` may answer a failure with "".

    This is the half of D37 that made the product lie rather than merely
    be exploitable: a failed `git log` returned "", `_commits` read that
    as no commits, and the report published `files_changed: 0` — the
    exact confusion `history.has_history` exists to prevent.
    """
    not_a_repo = tmp_path / "bare"
    not_a_repo.mkdir()

    with pytest.raises(GitCommandFailed):
        run_git(["log", "--format=%H"], not_a_repo)

    assert probe_git(["rev-parse", "--git-dir"], not_a_repo) == ""


def test_history_reports_absence_rather_than_zero_when_git_fails(tmp_path: Path) -> None:
    """The user-visible consequence, asserted at the seam that publishes it."""
    from maintainability_audit.history import has_history

    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()
    assert has_history(not_a_repo) is False, (
        "a directory with no git history must report absence, never a zero "
        "that reads as 'nothing changed'"
    )


def test_git_env_drops_every_location_override() -> None:
    """`-C` and `cwd` do not bind git while these are set."""
    overrides = {
        "GIT_DIR": "/elsewhere/.git",
        "GIT_WORK_TREE": "/elsewhere",
        "GIT_INDEX_FILE": "/elsewhere/index",
        "GIT_OBJECT_DIRECTORY": "/elsewhere/objects",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/elsewhere/alt",
        "GIT_COMMON_DIR": "/elsewhere/common",
        "GIT_CEILING_DIRECTORIES": "/",
        "GIT_NAMESPACE": "ns",
    }
    original = {k: os.environ.get(k) for k in overrides}
    try:
        os.environ.update(overrides)
        scrubbed = git_env()
        leaked = sorted(k for k in overrides if k in scrubbed)
        assert not leaked, f"git would be redirected by inherited {leaked}"
        assert "PATH" in scrubbed or "PATH" not in os.environ, (
            "the scrub removed more than git's location variables"
        )
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_a_repository_is_read_through_its_own_path_not_an_inherited_one(
    tmp_path: Path,
) -> None:
    """The scrub, exercised rather than asserted about."""
    real = _repo(tmp_path / "real")
    decoy = _repo(tmp_path / "decoy")
    (decoy / "only_in_decoy.py").write_text("y = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(decoy), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(decoy), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "decoy"], check=True)

    previous = os.environ.get("GIT_DIR")
    try:
        os.environ["GIT_DIR"] = str(decoy / ".git")
        head = run_git(["rev-parse", "HEAD"], real)
        expected = subprocess.run(
            ["git", "-C", str(real), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
            env={k: v for k, v in os.environ.items() if k != "GIT_DIR"},
        ).stdout.strip()
        assert head == expected, "GIT_DIR redirected the read to another repository"
    finally:
        if previous is None:
            os.environ.pop("GIT_DIR", None)
        else:
            os.environ["GIT_DIR"] = previous


def _git_spawns(tree: ast.AST) -> list[ast.Call]:
    """Every `subprocess.*` call in a module whose argv literal starts with git."""
    spawns = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "attr", None)
        if name not in {"run", "check_output", "Popen", "check_call"}:
            continue
        if not node.args:
            continue
        argv = node.args[0]
        first = argv.elts[0] if isinstance(argv, ast.List) and argv.elts else None
        if isinstance(first, ast.Constant) and first.value == "git":
            spawns.append(node)
    return spawns


def test_every_git_spawn_is_bounded_and_scrubbed() -> None:
    """Swept over the package, because this was fixed at one door before.

    A new git call added tomorrow without a timeout, or holding the
    caller's `GIT_DIR`, fails here rather than waiting for the next
    audit to notice it.
    """
    unbounded: list[str] = []
    unscrubbed: list[str] = []
    found = 0
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for call in _git_spawns(tree):
            found += 1
            keywords = {kw.arg for kw in call.keywords}
            where = f"{path.name}:{call.lineno}"
            if "timeout" not in keywords:
                unbounded.append(where)
            if "env" not in keywords:
                unscrubbed.append(where)

    assert found >= 2, f"the sweep found no git spawns to check ({found})"
    assert not unbounded, f"git spawned with no timeout: {unbounded}"
    assert not unscrubbed, f"git spawned holding the inherited environment: {unscrubbed}"
    assert GIT_TIMEOUT_SECONDS > 0
