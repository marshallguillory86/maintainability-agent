"""Keep shipped fingerprint documentation aligned with the implementation."""

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
IDENTITY_SOURCE = ROOT / "src" / "maintainability_audit" / "_identity.py"


def _ordinal_fingerprints_ship_without_a_body_hash() -> bool:
    source = IDENTITY_SOURCE.read_text(encoding="utf-8")
    ordinal_format_ships = "function:{path}:{name}#{ordinal}" in source
    body_hash_ships = re.search(
        r"(?:declaration|unit|normalized)[_ ](?:body|content).{0,80}(?:hash|digest)"
        r"|(?:hash|digest).{0,80}(?:declaration|unit|normalized)[_ ](?:body|content)",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return ordinal_format_ships and body_hash_ships is None


@pytest.fixture(scope="module", autouse=True)
def ordinal_identity_is_the_shipped_contract() -> None:
    if not _ordinal_fingerprints_ship_without_a_body_hash():
        pytest.skip("identity implementation no longer matches the ordinal-only contract")


def test_architecture_current_state_does_not_claim_content_addressing() -> None:
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    current_state = architecture.split(
        "## Proposed extension boundaries", maxsplit=1
    )[0]
    current_state_without_known_debt = re.sub(
        r"^## Known debt\n.*?(?=^## )",
        "",
        current_state,
        flags=re.MULTILINE | re.DOTALL,
    )

    stale_claims = (
        r"(?:identity|fingerprints?).{0,100}content[- ]addressed",
        r"content[- ]addressed.{0,100}(?:identity|fingerprints?)",
        r"hash of (?:the )?(?:unit|normalized) content",
    )
    for pattern in stale_claims:
        assert re.search(
            pattern,
            current_state_without_known_debt,
            flags=re.IGNORECASE | re.DOTALL,
        ) is None


def test_report_contract_does_not_document_line_coupled_fingerprints() -> None:
    contract = (ROOT / "docs" / "report-contract.md").read_text(encoding="utf-8")

    assert "function:<path>:<name>:<line>" not in contract
    assert "function:{path}:{name}:{start_line}" not in contract


def test_migration_guide_does_not_promise_a_normalized_content_hash() -> None:
    migration = (ROOT / "docs" / "migration-0.7.md").read_text(encoding="utf-8")

    assert "Finding identity is **content-addressed** in 0.7" not in migration
    assert re.search(
        r"hash of (?:the )?normalized content",
        migration,
        flags=re.IGNORECASE,
    ) is None


def test_unreleased_changelog_does_not_claim_content_addressed_identity() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = changelog.split("## Unreleased", maxsplit=1)[1].split(
        "\n## ", maxsplit=1
    )[0]

    assert "Identity is now content-addressed." not in unreleased
