"""A report with no security work order renders no section (D197).

Covers existing behaviour: this passed before the HTML report started
drawing the work order, and it passes after. It is kept because D197 made
that renderer conditional — data, then Markdown, then nothing — and the
branch that returns nothing is the one nobody looks at until a report
grows an empty heading.

Not cited as a closing test: it defends the change rather than proving
it, and citing it would make that entry look better attested than it is.
"""

from __future__ import annotations

from maintainability_audit._security_work_order import complete_html


def test_no_work_order_renders_nothing() -> None:
    """No heading, no intro, no empty section — nothing at all."""
    assert complete_html({}) == []


def test_an_empty_work_order_renders_nothing() -> None:
    """A falsy entry is the same case: the delegate wrote no work order."""
    assert complete_html({"security_work_order": None}) == []
