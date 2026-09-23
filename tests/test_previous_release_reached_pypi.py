"""A release does not ship over one that never reached PyPI.

3.7.2 was tagged, and its release build failed: the suite ran without
secure-code-agent installed, four security-pillar tests failed, and the
publish step was skipped. 3.7.3 added the missing install (D177) and
shipped — over the hole. 3.7.2's changes reached users inside 3.7.3, so
nothing was lost that time, and nothing recorded that anything had
happened either.

`test_the_previous_release_was_tagged` does not catch this: the tag
existed. What was missing was the publish, and only the release build can
see that — the suite runs without network access by design. So this is a
release-time check: before publishing a version, confirm the one before
it is on PyPI, and refuse otherwise. The right response to a failed
publish is to re-run that release, not to stack the next one on top.

The logic is tested here with the index lookup injected, so no test needs
the network.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "check_previous_release_published.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_previous_release_published", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_previous_release_published"] = module
    spec.loader.exec_module(module)
    return module


check = _load()

CHANGELOG = """# Changelog

## Unreleased

## 3.8.2 - 2026-09-24

### Fixed — something

## 3.8.1 - 2026-09-23

### Fixed — something earlier

## 3.8.0 - 2026-09-23
"""


def test_the_previous_release_is_read_from_the_changelog() -> None:
    """One back from the shipping version, skipping `Unreleased`."""
    assert check.previous_version(CHANGELOG, "3.8.2") == "3.8.1"


def test_a_published_previous_release_passes() -> None:
    assert check.verdict(CHANGELOG, "3.8.2", published=lambda v: True) is None


def test_an_unpublished_previous_release_is_refused_by_name() -> None:
    """The 3.7.2 shape: tagged, never published, next one about to ship."""
    complaint = check.verdict(CHANGELOG, "3.8.2", published=lambda v: v != "3.8.1")

    assert complaint is not None
    assert "3.8.1" in complaint
    assert "re-run" in complaint.lower()


def test_the_shipping_version_must_lead_the_changelog() -> None:
    """Otherwise "one back" names the wrong release and proves nothing."""
    complaint = check.verdict(CHANGELOG, "9.9.9", published=lambda v: True)

    assert complaint is not None
    assert "9.9.9" in complaint


def test_only_a_plain_version_ever_becomes_a_request(monkeypatch) -> None:
    """Nothing but `X.Y.Z` reaches the index, and nothing else is fetched.

    Code scanning flagged the first cut, which built a URL and handed it to
    `urllib.request.urlopen` — a call that opens whatever scheme it is
    given, `file:` included. The prefix was a constant, but "the prefix is
    a constant" is a property a reader has to verify by hand. Now the host
    is fixed in the connection itself and the version is validated first,
    so a hostile string fails closed before any connection is made.
    """
    def no_network(*args, **kwargs):
        raise AssertionError("a connection was attempted for an invalid version")

    monkeypatch.setattr(check.http.client, "HTTPSConnection", no_network)

    for hostile in ("file:///etc/passwd", "3.8.0/../../simple", "3.8", "", "3.8.0\n"):
        assert check.on_pypi(hostile) is None, hostile


def test_the_lookup_cannot_choose_a_scheme() -> None:
    """The only network call is an HTTPS connection to a fixed host.

    Read from the syntax tree, not the text: the docstring explains why
    `urlopen` is gone, and a text search would fail on the explanation.
    """
    import ast

    tree = ast.parse(TOOL.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    hosts = [
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", None) == "HTTPSConnection"
        and node.args and isinstance(node.args[0], ast.Constant)
    ]

    assert "urllib" not in imported, "urllib can open any scheme it is handed"
    assert hosts == ["pypi.org"], f"expected one fixed-host connection, found {hosts}"


def test_an_unreachable_index_fails_rather_than_passes() -> None:
    """A lookup that could not answer is not a yes.

    `published` returns `None` when PyPI could not be reached. Reading that
    as "published" would make the check pass exactly when it could not run.
    """
    complaint = check.verdict(CHANGELOG, "3.8.2", published=lambda v: None)

    assert complaint is not None
    assert "could not" in complaint.lower()
