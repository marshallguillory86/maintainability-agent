"""`paths.exclude_additional` adds exclusions without discarding the defaults (#292).

`deep_update` merges dicts and *replaces* lists, so a repository that set
`paths.exclude_patterns` to skip one more directory silently discarded the
whole default list — `.git/`, `node_modules/`, `vendor/`, `*.min.js` and
whatever a later release adds — and froze a copy of it that drifts on the
next release. secure-code-agent declined to do that rather than add one
exclusion. `exclude_additional` appends to whatever the earlier tiers
produced, at each tier, so a repository can add without restating.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from maintainability_audit.config import load_config
from maintainability_audit.report import build_report

ROOT = Path(__file__).resolve().parents[1]


def _config_with(tmp_path: Path, paths: dict) -> str:
    path = tmp_path / "maintainability-agent.json"
    path.write_text(json.dumps({"version": 1, "paths": paths}), encoding="utf-8")
    return str(path)


def test_additions_keep_every_default(tmp_path: Path) -> None:
    defaults = load_config(None)["paths"]["exclude_patterns"]

    merged = load_config(_config_with(tmp_path, {"exclude_additional": ["scratch/"]}))

    assert merged["paths"]["exclude_patterns"] == [*defaults, "scratch/"]


def test_an_addition_is_honoured_by_the_scan(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (tmp_path / "scratch").mkdir()
    (tmp_path / "scratch" / "junk.py").write_text("def g():\n    return 2\n", encoding="utf-8")

    config = load_config(_config_with(tmp_path, {"exclude_additional": ["scratch/"]}))
    report = build_report(tmp_path, config)

    assert report["summary"]["files_scanned"] == 1


def test_the_published_schema_accepts_it() -> None:
    schema = json.loads((ROOT / "maintainability-agent.schema.json").read_text(encoding="utf-8"))

    jsonschema.validate({"version": 1, "paths": {"exclude_additional": ["scratch/"]}}, schema)
