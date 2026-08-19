"""SpotBugs catalog promise, license policy, pool document, ADR 012 honesty.

Split from the runtime contract the way every oversized suite here has
been split. Measures are only what the pinned invocation emits (style);
complexity and structure pools must drop this tool. D15's composition
test lives in test_d15_composition.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _ast_reading import producer_literal, recomputed_counts

from maintainability_audit._catalog import (
    DEFAULTS,
    LICENSE_POLICIES,
    resolve_pool,
)
from maintainability_audit._mcp_setup import setup_questions
from maintainability_audit._tool_adapters import adapter_for
from maintainability_audit.config import load_config

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "analyzer-catalog.json"
PRODUCER = ROOT / "tools" / "build_catalog.py"
POOL_DOC = ROOT / "docs" / "analyzer-pool.md"
ADR_012 = ROOT / "docs" / "adr-012-spotbugs-build-boundary.md"
REGISTER = ROOT / "docs" / "decisions.md"
SPOTBUGS_CONCERNS = ("style",)


def _pool_config(policy: str, **analyzers: Any) -> dict[str, Any]:
    config = load_config(None)
    config["analyzers"].update({
        "run": True, "depth": "moderate", "license_policy": policy, **analyzers,
    })
    return config


def _catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _entry() -> dict[str, Any]:
    return next(tool for tool in _catalog()["tools"] if tool["slug"] == "spotbugs")


def _weak_copyleft_policy() -> str:
    admitting = [
        name for name, classes in LICENSE_POLICIES.items()
        if "weak-copyleft" in classes
    ]
    return min(admitting, key=lambda name: len(LICENSE_POLICIES[name]))


def test_catalog_and_producer_record_the_weak_copyleft_bytecode_contract() -> None:
    """Already-classified LGPL; measures are only what the invocation emits."""
    catalog = _catalog()
    entry = _entry()

    assert "lgpl" in entry["license"].lower() or "lesser" in entry["license"].lower()
    assert entry["license_status"] == "foss"
    assert entry["license_class"] == "weak-copyleft"
    assert entry["languages"] == ["java"]
    assert tuple(entry["measures"]) == SPOTBUGS_CONCERNS, (
        "do not stuff complexity or structure into measures to prettify a tuple"
    )
    assert entry["tier"] == "moderate"
    assert entry["adapter"] == "implemented"

    note = catalog["provenance"]["note"].lower()
    assert "spotbugs" in note and "lgpl" in note

    tiers = producer_literal("VERIFIED_TIERS")
    adapters = producer_literal("IMPLEMENTED_ADAPTERS")
    assert set(tiers) == set(adapters)
    assert tiers["spotbugs"] == "moderate"
    assert producer_literal("VERIFIED_MEASURES")["spotbugs"] == SPOTBUGS_CONCERNS


def test_catalog_counts_are_recomputed_from_the_tool_records() -> None:
    catalog = _catalog()
    assert catalog["counts"] == recomputed_counts(catalog["tools"])


def test_a_style_pool_keeps_spotbugs_and_complexity_does_not() -> None:
    """Honest measures: STYLE is in the invocation; complexity is not."""
    style, _ = resolve_pool(_pool_config(
        _weak_copyleft_policy(), concerns=["style"],
    ))
    assert "spotbugs" in {tool["slug"] for tool in style}

    for concern in ("complexity", "structure", "documentation"):
        pool, _ = resolve_pool(_pool_config(
            _weak_copyleft_policy(), concerns=[concern],
        ))
        assert "spotbugs" not in {tool["slug"] for tool in pool}, (
            f"a {concern}-only pool selected a bug-pattern tool"
        )


def test_selection_honours_the_license_policy_in_both_directions() -> None:
    defaults = {question["name"]: question["default"] for question in setup_questions({})}
    assert defaults["license_policy"] == DEFAULTS["license_policy"] == "permissive"
    assert "weak-copyleft" not in LICENSE_POLICIES["permissive"]

    _pool, decisions = resolve_pool(_pool_config("permissive"))
    decision = next(item for item in decisions if item.slug == "spotbugs")
    assert not decision.selected
    assert "license class" in decision.reason
    assert "weak-copyleft" in decision.reason

    admitting = _weak_copyleft_policy()
    weak_pool, weak_decisions = resolve_pool(_pool_config(admitting))
    assert "spotbugs" in {tool["slug"] for tool in weak_pool}
    selected = next(item for item in weak_decisions if item.slug == "spotbugs")
    assert selected.selected


def test_pool_document_names_spotbugs_bytecode_and_build_remedy() -> None:
    text = POOL_DOC.read_text(encoding="utf-8")
    assert re.search(r"^\| spotbugs \|", text, flags=re.MULTILINE)
    assert "bytecode" in text.lower() or "class" in text.lower()
    assert "build" in text.lower()
    assert "lgpl" in text.lower()


def test_adr_012_does_not_claim_d15_or_a_shipped_adapter() -> None:
    """D15's composition test now exists; the adapter must still be the shipped one."""
    adr = ADR_012.read_text(encoding="utf-8")
    assert "still to be written" not in adr
    assert "test_d15_composition" in adr or "covers both shapes" in adr

    row = next(
        line for line in REGISTER.read_text(encoding="utf-8").splitlines()
        if line.startswith("| [012]")
    )
    shipped = adapter_for("spotbugs") is not None
    if shipped:
        assert "not implemented" not in row.lower()
    else:
        assert "not implemented" in row.lower()
