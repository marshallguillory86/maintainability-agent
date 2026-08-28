"""D82/D83: the audit door re-checks consent, and does not name targets.

Two findings at the same function, from a UAT audit of `2fa909e`.

`authorize_repository` asked one question -- is this path inside the
ledger? -- against a ledger `allowed_roots()` builds **once**, when the
server is constructed. A standing grant whose directory was swapped
afterwards kept authorizing whatever now sat there until the host died,
and an MCP server is long-lived. That is D38's original shape: the
in-process seam was already right, and a later read of a stored fact
went around it. Here the later read was not happening at all.

And its refusal named the *resolved* path, which is where a symlink the
user typed actually points. D72 removed that disclosure from
`server_info`; this door kept it, because D72's falsifier read the
refusal dictionary and nothing else.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit import _grant_ledger, _mcp_audit
from maintainability_audit._stored_grants import IDENTITY_KEY, directory_identity
from maintainability_audit.config import PathNotAllowed


def _standing_grant(
    monkeypatch: pytest.MonkeyPatch, granted: Path
) -> tuple[Path, ...]:
    """A persisted "always" grant, recorded the way the product records it."""
    stored = {
        "allowed_roots": [str(granted)],
        IDENTITY_KEY: {str(granted): directory_identity(granted)},
    }
    monkeypatch.setattr(_grant_ledger, "load_user_config", lambda: dict(stored))
    # The launch root is a *sibling*, not the parent. Launching on the
    # parent would cover the granted path independently, so the standing
    # grant would never be the thing under test -- which is exactly the
    # fixture bug that let D83's closer pass for the wrong reason until
    # D90 separated the two sources of authorization.
    elsewhere = granted.parent / "launch-elsewhere"
    elsewhere.mkdir(exist_ok=True)
    return _mcp_audit.allowed_roots(explicit=(str(elsewhere),))


def test_a_swapped_directory_loses_its_grant_without_a_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D83: the standing grant is re-checked at use, not only at start-up.

    Reproduced exactly as reported: grant it, swap the directory, and
    ask again inside the same process.
    """
    base = tmp_path.resolve()
    granted = base / "project"
    granted.mkdir()
    roots = _standing_grant(monkeypatch, granted)

    assert _mcp_audit.authorize_repository(str(granted), roots) == granted

    granted.rename(base / "moved-away")
    granted.mkdir()
    (granted / "pwned.txt").write_text("x\n", encoding="utf-8")

    if directory_identity(granted) == directory_identity(base / "moved-away"):
        pytest.skip("this filesystem reused the inode; D79 discloses that limit")

    with pytest.raises(PathNotAllowed) as refused:
        _mcp_audit.authorize_repository(str(granted), roots)
    assert "withdrawn" in str(refused.value), str(refused.value)


def test_a_launch_root_is_not_re_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fix must not withdraw this process's own configuration.

    `--allow-root`, the environment variable and the working directory
    carry no recorded identity because they are not standing consent.
    Re-checking them would refuse every ordinary launch.
    """
    monkeypatch.setattr(_grant_ledger, "load_user_config", lambda: {})
    root = tmp_path.resolve() / "work"
    root.mkdir()
    roots = _mcp_audit.allowed_roots(explicit=(str(root),))
    assert _mcp_audit.authorize_repository(str(root), roots) == root


def test_a_refusal_does_not_tell_the_host_where_a_symlink_points(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D82: the same disclosure D72 closed, at the other door.

    The user names `innocent`. The host is told `secret-target`, a
    directory the user never mentioned and this agent had no business
    publishing.
    """
    import os

    base = tmp_path.resolve()
    secret = base / "secret-target"
    secret.mkdir()
    innocent = base / "innocent"
    os.symlink(secret, innocent)
    launch = base / "launch"
    launch.mkdir()

    monkeypatch.setattr(_grant_ledger, "load_user_config", lambda: {})
    roots = _mcp_audit.allowed_roots(explicit=(str(launch),))

    with pytest.raises(PathNotAllowed) as refused:
        _mcp_audit.authorize_repository(str(innocent), roots)

    message = str(refused.value)
    assert "secret-target" not in message, (
        f"the refusal published the symlink's target: {message}"
    )
    assert "innocent" in message, (
        "the refusal should still name what the user typed, which is "
        f"theirs already: {message}"
    )


def test_a_missing_directory_refusal_does_not_name_the_resolved_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sibling refusal on the same function, checked for the same leak."""
    from maintainability_audit._mcp_audit import InvalidAuditArgument

    monkeypatch.setattr(_grant_ledger, "load_user_config", lambda: {})
    roots = _mcp_audit.allowed_roots(explicit=(str(tmp_path.resolve()),))
    with pytest.raises(InvalidAuditArgument) as refused:
        _mcp_audit.authorize_repository(str(tmp_path / "nope"), roots)
    assert str(tmp_path.resolve()) not in str(refused.value), str(refused.value)


def test_a_launch_root_still_authorizes_despite_a_stale_grant_beneath_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D90: the freshness check must not withdraw what nobody consented to.

    D83 re-checks persisted grants at use. It applied that to any
    request a stale grant happened to *cover*, so launching with
    `--allow-root <base>` while holding a stale grant for
    `<base>/project` refused `<base>/project` -- which the launch root
    authorized on its own, independently of any consent.

    A freshness rule that revokes access granted by this process's own
    configuration is not a tightening; it is a denial of service, and
    it was introduced by the fix for the defect above.

    `test_a_launch_root_is_not_re_checked` passed throughout, because
    its launch-root case has no overlapping persisted grant -- the
    narrower-than-the-claim shape, in a test written the same hour as
    the claim.
    """
    base = tmp_path.resolve()
    project = base / "project"
    project.mkdir()
    stored = {
        "allowed_roots": [str(project)],
        IDENTITY_KEY: {str(project): directory_identity(project)},
    }
    monkeypatch.setattr(_grant_ledger, "load_user_config", lambda: dict(stored))

    # The launch grants the parent. The stale grant below it is irrelevant.
    roots = _mcp_audit.allowed_roots(explicit=(str(base),))
    project.rename(base / "moved-away")
    project.mkdir()

    assert _mcp_audit.authorize_repository(str(project), roots) == project, (
        "a stale standing grant vetoed a launch root that authorizes this "
        "path on its own"
    )


def test_a_stale_grant_with_no_launch_cover_is_still_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D90's fix must not reopen D83.

    The launch root here does not cover the request, so the standing
    grant is the only thing that could authorize it -- and it is stale.
    """
    base = tmp_path.resolve()
    project = base / "project"
    project.mkdir()
    elsewhere = base / "elsewhere"
    elsewhere.mkdir()
    stored = {
        "allowed_roots": [str(project)],
        IDENTITY_KEY: {str(project): directory_identity(project)},
    }
    monkeypatch.setattr(_grant_ledger, "load_user_config", lambda: dict(stored))
    roots = _mcp_audit.allowed_roots(explicit=(str(elsewhere),))

    project.rename(base / "gone")
    project.mkdir()
    if directory_identity(project) == directory_identity(base / "gone"):
        pytest.skip("this filesystem reused the inode; D79 discloses that limit")

    with pytest.raises(PathNotAllowed):
        _mcp_audit.authorize_repository(str(project), roots)


def test_the_config_refusals_name_no_resolved_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D91: D82 closed one door and published two paths one function down.

    A caller naming `innocent.json` was told the symlink's target *and*
    the canonical repository path. D82's falsifier read
    `authorize_repository` only, so the fix that removed one disclosure
    left a worse one beside it.
    """
    import os

    from maintainability_audit._mcp_audit import InvalidAuditArgument

    base = tmp_path.resolve()
    repo = base / "repo"
    repo.mkdir()
    secret = base / "secret-target.json"
    secret.write_text("{}\n", encoding="utf-8")
    os.symlink(secret, repo / "innocent.json")
    monkeypatch.setattr(_grant_ledger, "load_user_config", lambda: {})

    with pytest.raises(PathNotAllowed) as escaped:
        _mcp_audit.authorize_config("innocent.json", repo)
    message = str(escaped.value)
    assert "secret-target" not in message, f"the target was published: {message}"
    assert str(repo) not in message, f"the canonical repo path was published: {message}"
    assert "innocent.json" in message, "the refusal should name what the caller typed"

    with pytest.raises(InvalidAuditArgument) as missing:
        _mcp_audit.authorize_config("nope.json", repo)
    assert str(repo) not in str(missing.value), str(missing.value)


def test_no_repository_scoped_path_refusal_names_what_it_resolved_to(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D96: the last two doors in a family of six.

    D72 closed `server_info`, D82 `authorize_repository`, D91
    `authorize_config`. `baseline_path` and `config.repository_path`
    were still publishing resolved targets, and the second runs on an
    **ordinary audit** whenever the repository's own config names a
    path -- so a symlinked `history.jsonl` told the chat host where it
    pointed.

    Every closer in that family read the one function it was written
    for, which is why the family took six entries instead of one.
    """
    import os

    from maintainability_audit.config import repository_path

    base = tmp_path.resolve()
    repo = base / "repo"
    repo.mkdir()
    secret = base / "secret-history-dir"
    secret.mkdir()
    os.symlink(secret, repo / "linkdir")
    monkeypatch.setattr(_grant_ledger, "load_user_config", lambda: {})

    with pytest.raises(PathNotAllowed) as refused:
        repository_path(repo, "linkdir/history.jsonl", ".maintainability/history.jsonl")
    message = str(refused.value)
    assert "secret-history-dir" not in message, message
    assert str(repo) not in message, message
    assert "linkdir/history.jsonl" in message, (
        "the refusal should name the configured spelling, which the "
        f"repository wrote itself: {message}"
    )
