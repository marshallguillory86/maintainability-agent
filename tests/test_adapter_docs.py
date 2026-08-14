"""Keep analyzer capability prose aligned with the shipped registries."""

import re
from pathlib import Path

from maintainability_audit._catalog import load_catalog
from maintainability_audit._generic import declared_adapter
from maintainability_audit._tool_adapters import adapter_for


ROOT = Path(__file__).parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_analyzer_flag_docs_do_not_say_adapters_are_still_being_written() -> None:
    for path in (
        "src/maintainability_audit/cli.py",
        "src/maintainability_audit/report.py",
    ):
        assert re.search(
            r"adapters? (?:are |is )?still being written",
            _text(path),
            flags=re.IGNORECASE,
        ) is None, path


def test_shipped_native_adapters_are_not_listed_as_planned() -> None:
    adapters = _text("docs/adapters.md")
    planned = adapters.split("## Planned Native Adapters", maxsplit=1)[1]
    roadmap = _text("docs/roadmap.md")
    roadmap_plan = re.search(
        r"\*\*(?:Additional )?Analyzer adapters\*\*[^\n]*",
        roadmap,
        flags=re.IGNORECASE,
    )
    assert roadmap_plan is not None

    for slug in ("eslint", "ruff", "radon"):
        assert re.search(rf"\b{slug}\b", planned, flags=re.IGNORECASE) is None
        assert re.search(
            rf"\b{slug}\b", roadmap_plan.group(), flags=re.IGNORECASE
        ) is None


def test_adapter_status_table_names_only_shipped_adapters() -> None:
    page = _text("docs/analyzer-pool.md")
    section = page.split("## Adapter status, stated plainly", maxsplit=1)[1].split(
        "## Regenerating", maxsplit=1
    )[0]
    claimed = {
        match.group(1)
        for match in re.finditer(r"^\| ([a-z][a-z0-9.-]*) \|", section, flags=re.MULTILINE)
        if match.group(1) != "adapter"
    }
    shipped = {
        tool["slug"]
        for tool in load_catalog()
        if adapter_for(tool["slug"]) is not None
        or declared_adapter(tool["slug"]) is not None
    }

    assert claimed == shipped
    for slug in ("flake8", "cohesion", "wily", "xenon"):
        assert adapter_for(slug) is None
        assert declared_adapter(slug) is None
        assert slug not in claimed
