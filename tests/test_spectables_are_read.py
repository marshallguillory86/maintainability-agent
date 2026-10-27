"""Spectables specifications are read where a repository keeps them (Decision 19).

Ken Pugh's AlignThree Spectables writes behaviour as typed Given/When/Then
tables in `.spectable` files, and its tooling reports authoring mistakes
before anything runs. Where a repository keeps such files, this audit reports
three of those mistakes, each from the grammar on alignthree.com/syntax.html:

- a table row whose cell count differs from the table's first row;
- two scenarios with the same name in one specification;
- an `=Name` cell that refers to no `Define` — "`=Name` must refer to a valid
  Define block" — in any of its forms, including a bare `Define` table whose
  `Name` column declares several at once.

Unknown types are not reported: the grammar publishes no list of built-in
types, so every primitive would read as unknown. Findings are reported only,
link to Spectables, and move no score.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

TYPES = """Specification Types

DataType Dollar
Uses Decimal
Examples: ValidValues
| Value | IsValid |
| 0     | true    |

Define
| Name | Value | Notes          |
| TBR  | -1    | not yet rolled |
"""

CART = """Specification Cart

Entity CartItem
| Attribute | Type   | Default  | Notes |
| Name      | String | =NoName  |       |
| Price     | Dollar | 1        |       |

Define NoName = nobody
Define EmptyCart
| Name | Price |

Scenario Add items
Given cart is : CartItem
| Name   | Price |
| Widget | 10    |
| Gadget |
When item added : CartItem Vertical
| Name  | =Missing |
| Price | =TBR     |
Then cart is : CartItem
| Name   | Price |
| Widget | 10    |

Scenario  Add   items
Given cart is : CartItem
| =EmptyCart |
\"\"\"
| a docstring | is not | a table |
| at all |
\"\"\"
# | a comment | is not a table |
"""


def _tree(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "tree"
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "cart.py").write_text("def total():\n    return 0\n", encoding="utf-8")
    return root


def _report(root: Path, exclude: list[str] | None = None) -> dict:
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    config = copy.deepcopy(load_config(None))
    config["paths"]["exclude_patterns"].extend(exclude or [])
    return build_report(root, config, run_analyzers=False)


def _findings(report: dict) -> set[tuple[str, int, str]]:
    return {(f["path"], f["line"], f["check"])
            for f in report["test_honesty"]["spectables"]["findings"]}


@pytest.fixture
def report(tmp_path: Path) -> dict:
    return _report(_tree(tmp_path, {"spec/Types.spectable": TYPES, "spec/Cart.spectable": CART}))


def test_the_three_mistakes_are_reported_by_file_line_and_check(report: dict) -> None:
    assert _findings(report) == {
        ("spec/Cart.spectable", 16, "column-count"),
        ("spec/Cart.spectable", 18, "undefined-reference"),
        ("spec/Cart.spectable", 24, "duplicate-scenario"),
    }


def test_a_reference_resolves_across_files_and_through_every_define_form(report: dict) -> None:
    # =NoName (one-line), =EmptyCart (table form), =TBR (bare Define table, another file).
    messages = " ".join(f["message"] for f in report["test_honesty"]["spectables"]["findings"])
    assert "Missing" in messages
    assert not {"NoName", "EmptyCart", "TBR"} & set(messages.replace("`", " ").split())


def test_the_files_read_are_counted_and_spectables_is_linked(report: dict) -> None:
    block = report["test_honesty"]["spectables"]
    assert block["files"] == 2
    assert "alignthree.com" in block["link"]


def test_an_excluded_spectable_is_not_read(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"spec/Types.spectable": TYPES, "spec/Cart.spectable": CART})
    report = _report(root, exclude=["spec/Cart.spectable"])

    assert report["test_honesty"]["spectables"]["files"] == 1
    assert _findings(report) == set()


def test_a_repository_without_spectables_reports_none(tmp_path: Path) -> None:
    report = _report(_tree(tmp_path, {}))

    assert report["test_honesty"]["spectables"]["files"] == 0
    assert report["test_honesty"]["spectables"]["findings"] == []


def test_the_report_names_each_finding_and_links_spectables(report: dict) -> None:
    from maintainability_audit.renderers import render_markdown

    markdown = render_markdown(report)
    assert "spec/Cart.spectable:18" in markdown
    assert "alignthree.com" in markdown


def test_the_finding_moves_no_score(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from maintainability_audit import report as report_module

    root = _tree(tmp_path, {"spec/Types.spectable": TYPES, "spec/Cart.spectable": CART})
    with_finding = _report(root)
    monkeypatch.setattr(report_module, "spectables", lambda *_args: {
        "files": 0, "findings": [], "link": ""})
    without = _report(root)

    assert with_finding["test_honesty"]["spectables"]["findings"]
    assert with_finding["score"] == without["score"]
