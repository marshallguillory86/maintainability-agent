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
from _ast_reading import calls_reaching, reachable_names

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


SPAWN_CALLS = {"run", "check_output", "Popen", "check_call", "call", "getoutput",
               "getstatusoutput"}

# A spawn that may inherit the caller's environment, and why. A reason is
# the classification; an empty string is not one. Anything not listed
# must pass `env`.
ENV_EXEMPT: dict[str, str] = {}


def _subprocess_spawns(tree: ast.AST) -> list[ast.Call]:
    """Every `subprocess` spawn in a module, however its argv is built.

    Deliberately not "calls whose first argument is a list literal
    starting with `git`". That was the first version, and an audit
    showed it enforced almost nothing. The second matched the literal
    attribute `subprocess.<call>`, and a later audit showed
    `import subprocess as sp` and `from subprocess import run` walked
    past that too — twice narrow, in two different ways.

    Name resolution lives in `_ast_reading` because the XML sweep needs
    the same thing, and two copies of it put both functions over this
    project's own complexity gate.
    """
    aliases, direct = reachable_names(tree, "subprocess", SPAWN_CALLS)
    return calls_reaching(tree, aliases, direct, SPAWN_CALLS)


def test_every_subprocess_spawn_is_bounded_and_classified() -> None:
    """A spawn added tomorrow fails here, however its argv is written.

    Two properties. *Bounded*: no child of this process may run without
    a timeout, because a wedged one hangs the host that asked for an
    audit. *Scrubbed*: it passes an explicit environment, or it is named
    in `ENV_EXEMPT` with a reason — `GIT_DIR` and its siblings outrank
    both `cwd` and `-C`, so an inherited value silently redirects a
    command at another repository.
    """
    unbounded: list[str] = []
    unclassified: list[str] = []
    found = 0
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for call in _subprocess_spawns(tree):
            found += 1
            keywords = {kw.arg: kw.value for kw in call.keywords}
            where = f"{path.name}:{call.lineno}"
            timeout = keywords.get("timeout")
            bounded = timeout is not None and not (
                isinstance(timeout, ast.Constant) and timeout.value is None
            )
            if not bounded:
                # `timeout=None` is the documented spelling of "wait
                # forever", and counting it as bounded is why presence
                # was never the property worth testing.
                unbounded.append(where)
            if "env" not in keywords and path.name not in ENV_EXEMPT:
                unclassified.append(where)

    assert found >= 3, f"the sweep found {found} spawns; it should see every one"
    assert not unbounded, f"a child process with no timeout: {unbounded}"
    assert not unclassified, (
        "a spawn inherits the caller's environment without being classified "
        f"in ENV_EXEMPT with a reason: {unclassified}"
    )
    assert all(reason.strip() for reason in ENV_EXEMPT.values()), (
        "an exemption without a reason is not a classification"
    )
    assert set(ENV_EXEMPT) <= {p.name for p in PACKAGE.rglob("*.py")}, (
        "ENV_EXEMPT names a module the package does not contain"
    )
    assert GIT_TIMEOUT_SECONDS > 0


def _commit(root: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", message], check=True)


def test_an_unborn_head_reports_absence_not_quiet_history(tmp_path: Path) -> None:
    """A repository with no commits, which the first fix missed.

    `rev-parse --git-dir` succeeds here and every `git log` then fails on
    the unborn HEAD. While the spawner swallowed that, the history
    section was computed from zeros and the tree scored as though its
    history had been measured and found quiet — evidence completeness
    manufactured from a failed subprocess, which is P3, not merely D37.
    """
    from maintainability_audit.history import has_history

    root = tmp_path / "unborn"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")

    assert probe_git(["rev-parse", "--git-dir"], root), "fixture is not a repository"
    assert has_history(root) is False, (
        "an unborn HEAD reported history; zeros from a failed log would "
        "then read as 'nothing changed'"
    )


def test_a_shallow_clone_reports_absence(tmp_path: Path) -> None:
    """The case the entry opened with, finally built rather than mocked."""
    from maintainability_audit.history import has_history

    origin = _repo(tmp_path / "origin")
    (origin / "b.py").write_text("y = 2\n", encoding="utf-8")
    _commit(origin, "two")

    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{origin}", str(shallow)],
        check=True)

    assert probe_git(["rev-parse", "--is-shallow-repository"], shallow) == "true", (
        "fixture is not actually shallow"
    )
    assert has_history(shallow) is False
    assert has_history(origin) is True, "a full clone must still report history"


def test_an_unanswerable_shallow_check_withholds_rather_than_claims(
    tmp_path: Path,
) -> None:
    """Fail closed: `!= "true"` read a failed check as "not shallow".

    A git that does not know `--is-shallow-repository` errors, the error
    became "", and `"" != "true"` reported complete history — the same
    failure-becomes-evidence collapse D37 closed at `git log`, left
    standing three lines above it.
    """
    from unittest.mock import patch

    from maintainability_audit import history as history_module

    root = _repo(tmp_path / "repo")

    def unanswerable(args: list[str], cwd: Path) -> str:
        if "--is-shallow-repository" in args:
            raise GitCommandFailed("this git does not know the option")
        return "ok"

    with patch.object(history_module, "run_git", unanswerable):
        assert history_module.has_history(root) is False, (
            "an unanswerable shallow check claimed complete history"
        )


def test_a_rename_is_read_from_git_and_a_failure_is_not_no_renames(
    tmp_path: Path,
) -> None:
    """D37: `rename_map` probed, so a fault arrived as missing rename glue.

    The negative answer here is a successful diff with no `R` lines, not
    a failing command — so a timeout or an unreadable object became "no
    renames" and every moved finding surfaced as new on a `git mv`, which
    is the ADR 009 hole produced by the spawner rather than the matcher.
    A commit git no longer has is the one legitimate empty case and is
    established by probing for it first.
    """
    from unittest.mock import patch

    from maintainability_audit import _finding_match
    from maintainability_audit._finding_match import rename_map

    root = _repo(tmp_path / "repo")
    old = run_git(["rev-parse", "HEAD"], root)
    subprocess.run(["git", "-C", str(root), "mv", "a.py", "moved.py"], check=True)
    _commit(root, "move")
    new = run_git(["rev-parse", "HEAD"], root)

    assert rename_map(root, old, new) == {"a.py": "moved.py"}
    # A commit that is gone: legitimately empty, never a crash.
    assert rename_map(root, "0" * 40, new) == {}

    def broken(args: list[str], cwd: Path) -> str:
        raise GitCommandFailed("timed out")

    with patch.object(_finding_match, "run_git", broken), pytest.raises(GitCommandFailed):
        rename_map(root, old, new)


def test_the_analyzer_child_cannot_be_told_what_to_import() -> None:
    """D39 / Decision 9: the environment cannot choose the analyzer's code.

    Not a sandbox and not claimed as one. What it removes is the narrow
    thing the decision rules out — a variable that makes an interpreter
    or a linter load code the operator did not choose. `PATH` survives,
    because the tool still has to be found.
    """
    from maintainability_audit._runner import analyzer_env

    loaders = {
        "PYTHONPATH": "/tmp/evil",
        "PYTHONSTARTUP": "/tmp/evil.py",
        "PYTHONHOME": "/tmp",
        "NODE_PATH": "/tmp/node",
        "NODE_OPTIONS": "--require /tmp/evil.js",
        "LD_PRELOAD": "/tmp/evil.so",
        "DYLD_INSERT_LIBRARIES": "/tmp/evil.dylib",
    }
    original = {k: os.environ.get(k) for k in loaders}
    try:
        os.environ.update(loaders)
        env = analyzer_env()
        leaked = sorted(k for k in loaders if k in env)
        assert not leaked, f"the analyzer child could be told what to load: {leaked}"
        assert "PATH" in env or "PATH" not in os.environ, (
            "the scrub took PATH and the tool can no longer be found"
        )
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_every_git_command_disables_gits_own_housekeeping() -> None:
    """D71: reading a repository must not let git rewrite it.

    Every git command this package runs is a read. But git runs
    housekeeping of its own after many commands, and housekeeping
    repacks objects and writes commit-graphs *inside* `.git` -- so a
    read-only audit still wrote to the tree it audited.

    A macOS CI run caught it as `.git/objects/maintenance.lock` turning
    up in a tree the MCP tool promises never to write. It surfaced only
    then because auto-maintenance triggers on accumulated loose objects
    rather than on every call: D66 added two `rev-list` invocations per
    audit and pushed a latent defect over the line. Two earlier runs of
    the same product code passed.

    So the guarantee is pinned to the argv rather than to a snapshot of
    a temporary directory, which is what made it probabilistic. The
    settings are prepended for every command in one place, and this
    fails if that place stops applying them.
    """
    from maintainability_audit.git_tools import _READ_ONLY

    assert _READ_ONLY == ("-c", "gc.auto=0", "-c", "maintenance.auto=false"), (
        f"the read-only git settings changed: {_READ_ONLY}"
    )

    source = (PACKAGE / "git_tools.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="git_tools.py")
    spawns = _subprocess_spawns(tree)
    assert spawns, "no spawn found in git_tools; this sweep proves nothing"

    for call in spawns:
        argv = call.args[0] if call.args else None
        assert isinstance(argv, ast.List), (
            f"git_tools.py:{call.lineno} builds its argv somewhere this "
            "check cannot read"
        )
        starred = [
            element.value.id
            for element in argv.elts
            if isinstance(element, ast.Starred) and isinstance(element.value, ast.Name)
        ]
        assert "_READ_ONLY" in starred, (
            f"git_tools.py:{call.lineno} runs git without _READ_ONLY, so "
            "git may repack objects and write commit-graphs into the "
            "repository this package only meant to read"
        )


def test_the_suites_own_git_has_maintenance_disabled(tmp_path: Path) -> None:
    """The conftest guard reaches git, rather than merely being set.

    `GIT_CONFIG_COUNT`/`KEY`/`VALUE` are honoured by git 2.31+. Asserting
    the environment variables exist would prove only that conftest ran;
    this asks git what it actually resolved, which is the thing the
    fixture repositories depend on.
    """
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for key, expected in (("gc.auto", "0"), ("maintenance.auto", "false")):
        seen = subprocess.run(
            ["git", "-C", str(tmp_path), "config", "--get", key],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        assert seen == expected, (
            f"git resolved {key}={seen!r}, not {expected!r}: a fixture's own "
            "commit can still schedule detached maintenance and write "
            ".git/objects/maintenance.lock into a tree a test is watching"
        )
