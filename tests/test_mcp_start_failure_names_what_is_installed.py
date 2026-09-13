"""When the chat door cannot start, it says what is installed and what put it there (D178).

Found setting up a second machine for a demo. Installing secure-code-agent's
scanner extras into this package's environment pulled in semgrep, which pins
`mcp<2`; pip replaced `mcp` 2.0.0 with 1.23.3, and `maintainability-agent-mcp`
failed to start with "MCP support is not installed" and the remedy
`pip install "maintainability-agent[mcp]"` — describing a package that was
installed, and prescribing the install that had just been undone.

The claim: **for every way the import can fail, the message states the
installed version and, where one exists, the package that requires `mcp`.**
The states are the three the version metadata can be in: absent, outside
this server's range, and inside it but unimportable.
"""
from __future__ import annotations

import importlib.metadata as metadata

import pytest


class _Dist:
    def __init__(self, name: str, requires: list[str]) -> None:
        self.metadata = {"Name": name}
        self.requires = requires


def _patch(monkeypatch, version: str | None, dists: list[_Dist]) -> None:
    def fake_version(name: str) -> str:
        if name == "mcp" and version is not None:
            return version
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "version", fake_version)
    monkeypatch.setattr(metadata, "distributions", lambda: iter(dists))


def test_a_version_outside_the_range_names_it_and_who_required_it(monkeypatch) -> None:
    from maintainability_audit.mcp_server import MCP_REQUIREMENT, mcp_unavailable_message

    _patch(monkeypatch, "1.23.3", [
        _Dist("semgrep", ["mcp==1.23.3", "click>=8"]),
        _Dist("mcp-helper", ["mcpx>=1"]),  # a name that merely starts with mcp is not mcp
        _Dist("maintainability-agent", ['mcp<3,>=2; extra == "mcp"']),
    ])
    message = mcp_unavailable_message(ImportError("cannot import name 'MCPServer'"))

    assert "1.23.3" in message and MCP_REQUIREMENT in message, message
    assert "semgrep" in message, f"the package that pinned mcp is not named: {message}"
    assert "mcp-helper" not in message, f"a package that does not require mcp was blamed: {message}"
    assert "not installed" not in message, f"an installed mcp was described as missing: {message}"


def test_an_absent_mcp_still_says_how_to_install_the_extra(monkeypatch) -> None:
    """Covers existing behaviour: the absent case was already worded correctly.

    Guards that naming versions did not change what a fresh environment is told.
    """
    from maintainability_audit.mcp_server import mcp_unavailable_message

    _patch(monkeypatch, None, [])
    message = mcp_unavailable_message(ImportError("No module named 'mcp'"))
    assert "not installed" in message and "maintainability-agent[mcp]" in message, message


def test_a_version_inside_the_range_reports_the_import_error_itself(monkeypatch) -> None:
    """An in-range mcp that will not import is not a version problem; do not say it is."""
    from maintainability_audit.mcp_server import mcp_unavailable_message

    _patch(monkeypatch, "2.0.0", [])
    message = mcp_unavailable_message(ImportError("broken wheel: missing pydantic_core"))
    assert "2.0.0" in message and "broken wheel" in message, message
    assert "not installed" not in message, message


@pytest.mark.parametrize("version", ["1.23.3", "3.0.0"])
def test_the_console_entry_raises_the_named_message(monkeypatch, version) -> None:
    """D178 at the seam the operator sees: `create_server` raises the named message."""
    import builtins

    from maintainability_audit import mcp_server

    _patch(monkeypatch, version, [_Dist("semgrep", [f"mcp=={version}"])])
    real_import = builtins.__import__

    def failing_import(name, *args, **kwargs):
        if name == "mcp.server" or name.startswith("mcp.server."):
            raise ImportError(f"cannot import name 'MCPServer' from 'mcp.server' ({version})")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", failing_import)
    with pytest.raises(RuntimeError) as raised:
        mcp_server.create_server(roots=())
    assert version in str(raised.value) and "semgrep" in str(raised.value), str(raised.value)
