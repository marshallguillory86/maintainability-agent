"""Competing libraries for one concern.

Three HTTP clients means three error shapes and three retry stories. The
cost is not duplication — each call site may be fine — it is that no
single mental model covers the codebase.

This detector is the one that needs a curated list, so it is also the one
most able to embarrass itself. The first run against the reference corpus
produced *only* false positives, and every one of them is pinned here:

- a package named in a fenced code block inside a Markdown document
- a CI helper under ``scripts/`` using a different client from the daemon
  it ships alongside

After those fixes it reports nothing across all 14 corpus repositories
and fires once, correctly, on a repo genuinely running two HTTP clients
in its service layer. Quiet is the intended behaviour: a curated list is
incomplete by construction, so silence means "nothing recognised", never
"nothing wrong".
"""
from __future__ import annotations

from pathlib import Path

from maintainability_audit.config import load_config
from maintainability_audit.idioms import DEFAULT_IDIOM_GROUPS, divergent_idioms, idiom_groups
from maintainability_audit.metrics import iter_files


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def scan(root: Path, config: dict | None = None) -> dict[str, set[str]]:
    write(root / "README.md", "# Test\n")
    cfg = config or load_config(None)
    found = divergent_idioms(root, iter_files(root, cfg), cfg)
    return {item["concern"]: {p["package"] for p in item["packages"]} for item in found}


# ---------------------------------------------------------------------------
# What must be found
# ---------------------------------------------------------------------------

def test_two_http_clients_in_production_code_are_reported(tmp_path: Path) -> None:
    write(tmp_path / "svc" / "a.py", "import httpx\n\n\ndef fetch():\n    return httpx.get('/')\n")
    write(tmp_path / "svc" / "b.py", "import aiohttp\n\n\ndef poll():\n    return aiohttp.ClientSession()\n")

    assert scan(tmp_path)["http client"] == {"httpx", "aiohttp"}


def test_javascript_imports_are_detected(tmp_path: Path) -> None:
    write(tmp_path / "src" / "a.ts", "import axios from 'axios';\nexport const go = () => axios.get('/');\n")
    write(tmp_path / "src" / "b.ts", "import got from 'got';\nexport const run = () => got('/');\n")

    assert scan(tmp_path)["http client"] == {"axios", "got"}


def test_one_library_per_concern_is_not_a_finding(tmp_path: Path) -> None:
    write(tmp_path / "svc" / "a.py", "import httpx\n")
    write(tmp_path / "svc" / "b.py", "import httpx\n")

    assert scan(tmp_path) == {}


# ---------------------------------------------------------------------------
# The false positives the corpus produced
# ---------------------------------------------------------------------------

def test_packages_named_in_markdown_are_not_imports(tmp_path: Path) -> None:
    """Regression: two of three findings on one repo came from fenced code
    blocks inside Markdown skill documents."""
    write(tmp_path / "svc" / "a.ts", "import zod from 'zod';\n")
    write(tmp_path / "docs" / "guide.md", "Example:\n\n```ts\nimport joi from 'joi';\n```\n")

    assert scan(tmp_path) == {}


def test_standalone_scripts_do_not_diverge_from_the_codebase(tmp_path: Path) -> None:
    """Regression: black was reported as running two HTTP clients — aiohttp
    in the blackd daemon, urllib3 in a CI helper under scripts/. Those are
    separate programs sharing a repository."""
    write(tmp_path / "src" / "server.py", "import aiohttp\n")
    write(tmp_path / "scripts" / "release_helper.py", "import urllib3\n")

    assert scan(tmp_path) == {}


def test_test_files_do_not_diverge_from_the_codebase(tmp_path: Path) -> None:
    write(tmp_path / "svc" / "a.py", "import httpx\n")
    write(tmp_path / "tests" / "test_a.py", "import requests\n")

    assert scan(tmp_path) == {}


def test_a_repository_does_not_diverge_from_itself(tmp_path: Path) -> None:
    """`httpx` imports `httpx`. That is not two mental models."""
    root = tmp_path / "httpx"
    write(root / "src" / "httpx" / "_api.py", "import httpx\nimport requests\n")

    assert "http client" not in scan(root)


def test_relative_imports_are_ignored(tmp_path: Path) -> None:
    write(tmp_path / "svc" / "a.py", "from . import requests\nfrom .httpx import thing\n")

    assert scan(tmp_path) == {}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def test_config_can_replace_the_shipped_groups() -> None:
    """The shipped list is incomplete by construction, so a repo must be
    able to state the concerns that matter to it."""
    custom = {"logging": ["loguru", "structlog"]}

    assert idiom_groups({"idiom_groups": custom}) == custom
    assert idiom_groups({}) == DEFAULT_IDIOM_GROUPS
    assert idiom_groups({"idiom_groups": {}}) == DEFAULT_IDIOM_GROUPS


def test_configured_groups_are_actually_applied(tmp_path: Path) -> None:
    config = load_config(None)
    config["idiom_groups"] = {"logging": ["loguru", "structlog"]}
    write(tmp_path / "svc" / "a.py", "import loguru\n")
    write(tmp_path / "svc" / "b.py", "import structlog\n")

    assert scan(tmp_path, config)["logging"] == {"loguru", "structlog"}
