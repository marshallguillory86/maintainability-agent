"""How a flagged declaration is described, in every output format.

Extracted from ``renderers.py`` (2026-08-06) so ``sarif.py`` does not
have to import the markdown renderer to phrase a result, and so both
modules stay inside the self-audit's file-length budget — the same split
that produced ``_metrics_types.py`` and ``_masking.py``.

Classes share the hotspot list with functions but are graded on length
alone, and their measured complexity is the sum of branches already
charged to their own methods — see ``metrics.class_status``. So a class
is named as one, and its complexity is withheld rather than inviting
someone to act on a double count. Reports and baselines written before
0.4.0 carry no ``kind``; its absence means "function".
"""
from __future__ import annotations

from typing import Any


def _is_class(item: dict[str, Any]) -> bool:
    return item.get("kind") == "class"


def hotspot_name(item: dict[str, Any], quote: str = "`") -> str:
    """Name a hotspot, labelled by kind. ``quote`` is "" for plain text."""
    return f"{quote}{item['name']}{quote}" + (" (class)" if _is_class(item) else "")


def hotspot_complexity(item: dict[str, Any]) -> str:
    """The complexity table cell, or ``-`` for a class."""
    return "-" if _is_class(item) else str(item["complexity"])


def hotspot_cognitive(item: dict[str, Any]) -> str:
    """The cognitive-complexity table cell, or ``-`` for a class.

    A class is a container rather than something read top to bottom, so
    it carries no reading cost of its own; its methods are charged
    individually.
    """
    return "-" if _is_class(item) else str(item.get("cognitive", 0))


def hotspot_measure(item: dict[str, Any]) -> str:
    """The parenthetical size/complexity clause used in prose renderings.

    Cognitive complexity is named separately from the branch count when
    present, because they mean different things: a function can have few
    paths and still be punishing to read if they are deeply nested.
    """
    size = f"{item['lines']} lines"
    if _is_class(item):
        return f"{size}, {item['status']}"
    cognitive = item.get("cognitive")
    reading = f", cognitive {cognitive}" if cognitive else ""
    return f"{size}, complexity {item['complexity']}{reading}, {item['status']}"
