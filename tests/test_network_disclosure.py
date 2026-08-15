"""P1's small close: no HTTP client, and no fetch nobody opted into.

The promise separates analysis from acquisition, and the separation was
half-shipped: analysis performs no network access, but `_npx` fell back
to `npx --yes` the moment a Node binary was missing — a package download
in the middle of what the user was told was an offline scan. The version
was recorded, which made it *disclosed*, not *opted into*.

Two rules, both classes:

- **This package must not grow an HTTP client.** Held over the AST of
  every module under `src/`, so the first `import requests` fails the
  build rather than shipping quietly inside a feature.
- **Acquisition is opt-in.** With `analyzers.acquire_tools` off — the
  default — a missing binary is a *not-installed* outcome for coverage
  and the environment work order, never a fetch.

What this does not claim: child processes are not sandboxed. A tool the
user installed can do whatever that tool does; the promise is about what
*this agent* initiates.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from maintainability_audit import _adapters
from maintainability_audit._adapters import _npx, set_tool_acquisition

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"

_FORBIDDEN_IMPORTS = {
    "urllib", "urllib.request", "urllib.error", "requests", "httpx", "aiohttp",
    "http.client",
}
_FORBIDDEN_CALLS = {"urlopen", "create_connection"}


@pytest.fixture(autouse=True)
def _acquisition_off():
    """Every test starts from the shipped default, whatever ran before."""
    set_tool_acquisition(False)
    yield
    set_tool_acquisition(False)


def _modules() -> list[Path]:
    return sorted(PACKAGE.glob("*.py"))


def test_no_module_imports_an_http_client() -> None:
    """The class: the agent has no way to talk to the internet itself.

    Not one file — every module, so the lint covers the module added
    next month. `socket` alone is not forbidden (stdlib neighbours use
    it indirectly); *connecting* is, and the call lint below holds that.
    """
    offenders: list[str] = []
    for module in _modules():
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            for name in names:
                if name in _FORBIDDEN_IMPORTS or name.split(".")[0] in _FORBIDDEN_IMPORTS:
                    offenders.append(f"{module.name}:{node.lineno} imports {name}")

    assert not offenders, (
        "an HTTP client entered src/, and P1 says the analysis performs no "
        "network access:\n  " + "\n  ".join(offenders)
    )


def test_no_module_opens_a_network_connection() -> None:
    offenders: list[str] = []
    for module in _modules():
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in _FORBIDDEN_CALLS:
                offenders.append(f"{module.name}:{node.lineno} calls {name}()")

    assert not offenders, (
        "a network connection is opened from src/:\n  " + "\n  ".join(offenders)
    )


def test_a_missing_node_tool_is_not_fetched_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No binary + no opt-in = not-installed, never `npx --yes`.

    The argv is the whole question: whatever runs it, `--yes` is an
    instruction to download. Returning the bare tool name instead lets
    the runner's probe fail exactly as it does for any absent binary,
    which lands the tool in coverage as not-installed and in the
    environment work order with its install command — the user acts,
    the agent does not.
    """
    monkeypatch.setattr(_adapters.shutil, "which", lambda name: None)

    for tool in ("jscpd", "eslint"):
        argv = _npx(tool, "--version")
        assert "--yes" not in argv, (
            f"{tool} is missing and acquisition is off, yet the argv fetches: {argv}"
        )
        assert "npx" not in argv, (
            f"{tool}: even bare npx resolves the package from the registry when "
            f"it is not cached, which is the same silent fetch: {argv}"
        )


def test_an_installed_tool_is_used_directly_regardless(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_adapters.shutil, "which", lambda name: f"/usr/local/bin/{name}")

    assert _npx("jscpd", "--version") == ("jscpd", "--version")


def test_opting_in_restores_the_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    """The capability is not deleted; it is consented to.

    Refusing acquisition outright would make the multi-language story
    depend on hand-installing a dozen ecosystems — the option product
    intent already rejected. The change is only who decides.
    """
    monkeypatch.setattr(_adapters.shutil, "which", lambda name: None)
    set_tool_acquisition(True)

    assert _npx("jscpd", "--version") == ("npx", "--yes", "jscpd", "--version")


def test_the_config_key_reaches_the_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """`analyzers.acquire_tools` is the documented opt-in, default off."""
    from maintainability_audit._catalog import DEFAULTS, settings_from

    assert DEFAULTS.get("acquire_tools") is False, (
        "the default must be off: a fetch nobody chose is the defect"
    )
    assert settings_from({})["acquire_tools"] is False
    assert settings_from({"analyzers": {"acquire_tools": True}})["acquire_tools"] is True


def test_analyze_honours_the_opt_in(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The switch is thrown from configuration at analysis time, both ways.

    Asserted through `analyze()` because a module-level switch nobody
    sets is exactly the `prompt_when_interactive` defect again: a key
    that exists, documented, read by nothing.
    """
    from maintainability_audit._analysis import analyze
    from maintainability_audit.config import load_config

    (tmp_path / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    observed: list[bool] = []
    monkeypatch.setattr(_adapters, "set_tool_acquisition",
                        lambda enabled: observed.append(bool(enabled)))
    import maintainability_audit._analysis as analysis_module
    monkeypatch.setattr(analysis_module, "set_tool_acquisition",
                        lambda enabled: observed.append(bool(enabled)),
                        raising=False)

    config = load_config(None)
    analyze(tmp_path, config)
    config["analyzers"] = {"acquire_tools": True}
    analyze(tmp_path, config)

    assert observed and observed[0] is False and observed[-1] is True, (
        f"analyze() never threw the acquisition switch from config: {observed}"
    )
