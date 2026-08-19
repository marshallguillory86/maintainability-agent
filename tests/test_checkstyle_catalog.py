"""Checkstyle's catalog promise, license policy, and pool document.

Split verbatim from test_checkstyle_adapter.py when the contract file
crossed the repository's own size warn line — the same split every
oversized suite in this project has taken. Runtime behavior stays in
test_checkstyle_adapter.py; this file holds the catalog, selection,
and documentation halves of the contract.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from _ast_reading import producer_literal

from maintainability_audit._catalog import (
    DEFAULTS,
    LICENSE_POLICIES,
    resolve_pool,
)
from maintainability_audit._mcp_setup import setup_questions
from maintainability_audit.config import load_config

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "analyzer-catalog.json"
PRODUCER = ROOT / "tools" / "build_catalog.py"
POOL_DOC = ROOT / "docs" / "analyzer-pool.md"
CHECKSTYLE_CONCERNS = ("style", "documentation")
POOLABLE = {"permissive", "weak-copyleft", "strong-copyleft"}


def _pool_config(policy: str, **analyzers: Any) -> dict[str, Any]:
    config = load_config(None)
    config["analyzers"].update({
        "run": True, "depth": "moderate", "license_policy": policy, **analyzers,
    })
    return config


def _catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _entry() -> dict[str, Any]:
    return next(tool for tool in _catalog()["tools"] if tool["slug"] == "checkstyle")


def _producer():
    """The real producer module: is_eligible has exactly one source (L1)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_catalog", PRODUCER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _eligible(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    is_eligible = _producer().is_eligible
    return [tool for tool in tools if is_eligible(tool)]


def _recomputed_counts(tools: list[dict[str, Any]]) -> dict[str, Any]:
    """The catalog summary is a function of the rows, not hand arithmetic."""
    eligible = _eligible(tools)
    return {
        "in_source": len(tools),
        "eligible": len(eligible),
        "by_tier": dict(Counter(tool["tier"] for tool in eligible)),
        "by_license_status": dict(Counter(tool["license_status"] for tool in tools)),
        "by_license_class": dict(Counter(tool["license_class"] for tool in tools)),
        "by_measure": dict(Counter(
            measure for tool in tools for measure in tool["measures"]
        )),
        "eligible_by_license_class": dict(Counter(
            tool["license_class"] for tool in eligible
        )),
        "adapters_implemented": sum(
            1 for tool in tools if tool["adapter"] == "implemented"
        ),
    }


def _weak_copyleft_policy() -> str:
    """The least-restrictive shipped policy that already admits weak-copyleft."""
    admitting = [
        name for name, classes in LICENSE_POLICIES.items()
        if "weak-copyleft" in classes
    ]
    return min(admitting, key=lambda name: len(LICENSE_POLICIES[name]))


def test_catalog_and_producer_record_the_weak_copyleft_contract() -> None:
    """LGPL is verified honestly; measures lead with concerns, not concepts."""
    catalog = _catalog()
    entry = _entry()

    assert entry["license"] == "LGPL-2.1-or-later"
    assert entry["license_status"] == "foss"
    assert entry["license_class"] == "weak-copyleft"
    assert "license" in entry["license_evidence"].lower()
    assert entry["languages"] == ["java"]
    assert tuple(entry["measures"][:2]) == CHECKSTYLE_CONCERNS, (
        "measures must lead with concern names; a concepts-only tuple "
        "dropped PMD from concern pools"
    )
    assert entry["tier"] == "moderate"
    assert entry["adapter"] == "implemented"

    note = catalog["provenance"]["note"].lower()
    assert "checkstyle" in note and "lgpl" in note and "license" in note

    tiers = producer_literal("VERIFIED_TIERS")
    adapters = producer_literal("IMPLEMENTED_ADAPTERS")
    assert set(tiers) == set(adapters), (
        "a below-all tier is a promise that a runnable adapter ships"
    )
    assert tiers["checkstyle"] == "moderate"
    assert producer_literal("VERIFIED_MEASURES")["checkstyle"][:2] == CHECKSTYLE_CONCERNS
    license_name, evidence = producer_literal("VERIFIED_LICENSES")["checkstyle"]
    assert license_name == "LGPL-2.1-or-later"
    assert "license" in evidence.lower()


def test_catalog_counts_are_recomputed_from_the_tool_records() -> None:
    """The PMD slice's count error came from hand-decrementing the summary."""
    catalog = _catalog()
    expected = _recomputed_counts(catalog["tools"])
    assert catalog["counts"] == expected


@pytest.mark.parametrize("concern", CHECKSTYLE_CONCERNS)
def test_a_concern_pool_keeps_checkstyle(concern: str) -> None:
    """Audit M: measures name the concern, so concern pools can select it."""
    pool, _decisions = resolve_pool(_pool_config(
        _weak_copyleft_policy(), concerns=[concern],
    ))
    assert "checkstyle" in {tool["slug"] for tool in pool}, (
        f"a {concern}-only pool dropped the {concern} tool"
    )


def test_selection_honours_the_license_policy_in_both_directions() -> None:
    """Weak-copyleft is the user's call: excluded by default, one policy away."""
    defaults = {question["name"]: question["default"] for question in setup_questions({})}
    assert defaults["license_policy"] == DEFAULTS["license_policy"] == "permissive"
    assert "weak-copyleft" not in LICENSE_POLICIES["permissive"]

    _pool, decisions = resolve_pool(_pool_config("permissive"))
    decision = next(item for item in decisions if item.slug == "checkstyle")
    assert not decision.selected
    assert "license class" in decision.reason
    assert "weak-copyleft" in decision.reason

    admitting = _weak_copyleft_policy()
    assert admitting in LICENSE_POLICIES
    weak_pool, weak_decisions = resolve_pool(_pool_config(admitting))
    assert "checkstyle" in {tool["slug"] for tool in weak_pool}
    selected = next(item for item in weak_decisions if item.slug == "checkstyle")
    assert selected.selected


def test_pool_document_names_checkstyle_and_its_license_evidence() -> None:
    """Docs yours: the pool page gains checkstyle and names the LICENSE evidence."""
    text = POOL_DOC.read_text(encoding="utf-8")
    assert re.search(r"^\| checkstyle \|", text, flags=re.MULTILINE)
    assert "lgpl" in text.lower()
    assert "checkstyle" in text.lower() and "license" in text.lower()
