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

from maintainability_audit import _mcp_audit
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
    monkeypatch.setattr(_mcp_audit, "load_user_config", lambda: dict(stored))
    return _mcp_audit.allowed_roots(explicit=(str(granted.parent),))


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
    monkeypatch.setattr(_mcp_audit, "load_user_config", lambda: {})
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

    monkeypatch.setattr(_mcp_audit, "load_user_config", lambda: {})
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

    monkeypatch.setattr(_mcp_audit, "load_user_config", lambda: {})
    roots = _mcp_audit.allowed_roots(explicit=(str(tmp_path.resolve()),))
    with pytest.raises(InvalidAuditArgument) as refused:
        _mcp_audit.authorize_repository(str(tmp_path / "nope"), roots)
    assert str(tmp_path.resolve()) not in str(refused.value), str(refused.value)
