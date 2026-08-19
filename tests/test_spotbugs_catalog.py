"""SpotBugs catalog promise, license policy, pool document, ADR 012 honesty.

Split from the runtime contract the way every oversized suite here has
been split. Measures are only what the pinned invocation emits (style);
complexity and structure pools must drop this tool. D15 stays unclaimed.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from _ast_reading import producer_literal

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


def _producer():
    """The real producer module: is_eligible has exactly one source (L1)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_catalog", PRODUCER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _recomputed_counts(tools: list[dict[str, Any]]) -> dict[str, Any]:
    is_eligible = _producer().is_eligible
    eligible = [tool for tool in tools if is_eligible(tool)]
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
    assert catalog["counts"] == _recomputed_counts(catalog["tools"])


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
    """Do-not-copy 12: no D15 present-tense; register stays honest until the class exists."""
    adr = ADR_012.read_text(encoding="utf-8")
    assert "still to be written" in adr or "will have to cover" in adr
    assert not re.search(r"D15's composition test covers both shapes", adr)

    row = next(
        line for line in REGISTER.read_text(encoding="utf-8").splitlines()
        if line.startswith("| [012]")
    )
    shipped = adapter_for("spotbugs") is not None
    if shipped:
        assert "not implemented" not in row.lower()
    else:
        assert "not implemented" in row.lower()
