"""Keep ADR 009's shipped matching contract aligned across live docs."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_live_identity_docs_name_structured_matching_and_git_rename_following() -> None:
    surfaces = {
        path: _read(path)
        for path in (
            "docs/adr-009-scan-history.md",
            "docs/decisions.md",
            "docs/architecture.md",
            "docs/migration-1.0.md",
            "docs/report-contract.md",
        )
    }
    joined = "\n".join(surfaces.values()).lower()

    assert "_finding_match" in surfaces["docs/architecture.md"]
    assert "body_digest" in surfaces["docs/report-contract.md"]
    assert "structured identit" in joined
    assert "git" in joined and "rename" in joined
    assert "baseline" in joined and "version 3" in joined


def test_live_identity_docs_do_not_call_the_body_digest_unshipped() -> None:
    surfaces = "\n".join(
        _read(path)
        for path in (
            "docs/adr-009-scan-history.md",
            "docs/decisions.md",
            "docs/architecture.md",
            "docs/migration-1.0.md",
            "docs/report-contract.md",
        )
    )
    stale = (
        r"(?:body|declaration-body) (?:hash|digest).{0,100}(?:did not ship|unshipped)",
        r"(?:did not ship|unshipped).{0,100}(?:body|declaration-body) (?:hash|digest)",
        r"rename following.{0,100}(?:did not ship|unshipped)",
    )
    for pattern in stale:
        assert re.search(pattern, surfaces, re.I | re.S) is None


def test_human_label_stays_ordinal_and_line_independent() -> None:
    contract = _read("docs/report-contract.md")
    adr = _read("docs/adr-009-scan-history.md")

    assert "function:{path}:{name}#{ordinal}" in contract
    assert "function:{path}:{name}#{ordinal}" in adr
    assert "function:<path>:<name>:<line>" not in contract
    assert "function:{path}:{name}:{start_line}" not in contract


def test_history_schema_three_is_current_and_older_history_is_readable() -> None:
    adr = _read("docs/adr-009-scan-history.md").lower()
    migration = _read("docs/migration-1.0.md").lower()

    assert "schema 3" in adr
    assert "schema 1" in adr and "schema 2" in adr
    assert "baseline" in migration and "version 3" in migration
    assert "regenerate" in migration
