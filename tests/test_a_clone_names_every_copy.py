"""A finding about several places names all of them (D209).

A duplicate block is a statement about two or more locations. The work
order carries one path — `_locate` takes the first — and the item read
*"duplicated block in `a.py`"* with the target *"remove the duplicated
block"*. An agent handed that deletes `a.py`'s copy, which clears
nothing and breaks the file it was deleted from. The half of the finding
that says **extract** rather than **delete** is the other location, and
the item did not carry it.

Near-duplicates had the same gap from the other side: the item said
*"remove the near-duplicate declaration"* without naming what it nearly
duplicates, while `near_duplicate_section` in the same prompt already
renders *"`near.py:5` `copy` is 95% identical to `orig` at
`orig.py:1`"*. One renderer had it right and the work order did not,
which is the D157 shape — a fix applied to one surface of one report.

"Remove" is also the exact word D165 had to correct for risk patterns,
where it read as "delete the matched text" and cleared the finding
without resolving it. Same verb, same failure, one class over.

The population is `COUNTED_SOURCES` — every finding class the report
carries as a located list, read from the module that defines them — so a
fifth class is covered the moment it is declared, and which of them are
about more than one place is answered by `_sites` rather than by a list
here.
"""

from __future__ import annotations

from typing import Any

from maintainability_audit._work_order import COUNTED_SOURCES, _items_from_counted, _sites

#: The label each class uses in its own single-place target, read from
#: `COUNTED_SOURCES` rather than repeated, so the sentence this test
#: refuses is built the same way the code builds it.
_LABELS = {name: label for name, _key, label in COUNTED_SOURCES}

#: One finding per counted class, each naming two places where its class
#: can. Keyed by the class name so a new entry in `COUNTED_SOURCES` with
#: no fixture fails `test_every_counted_class_has_a_fixture` rather than
#: being silently skipped.
FINDINGS: dict[str, dict[str, Any]] = {
    "duplicate-block": {"count": 3, "lines": 20,
                        "locations": ["a.py:10", "b.py:50", "c.py:7"]},
    "near-duplicate": {"path": "near.py", "start_line": 5, "name": "copy",
                       "similarity": 0.95, "lines": 12,
                       "duplicate_of": {"path": "orig.py", "start_line": 1,
                                        "name": "orig"}},
    "dead-code": {"path": "dead.py", "start_line": 7, "name": "unused", "lines": 9},
    "risk-pattern": {"path": "risk.py", "line": 3, "name": "TODO", "text": "later"},
}


def _items() -> list[dict[str, Any]]:
    report = {key: [FINDINGS[name]] for name, key, _label in COUNTED_SOURCES}
    return _items_from_counted(report)


def test_every_counted_class_has_a_fixture() -> None:
    """Clause two: a class with no finding is a class this file ignores."""
    assert COUNTED_SOURCES, "no counted classes, so every sweep below is empty"
    missing = [name for name, _key, _label in COUNTED_SOURCES if name not in FINDINGS]

    assert not missing, f"COUNTED_SOURCES gained {missing} with no fixture finding"
    assert len(_items()) == len(COUNTED_SOURCES)


def test_a_finding_about_several_places_carries_all_of_them() -> None:
    """Swept over every counted class, not over duplicate blocks alone.

    Which classes are about more than one place is asked of `_sites`,
    the same function the builder uses, so a class that becomes
    multi-place later is covered without editing this test.
    """
    checked = 0
    for item in _items():
        finding = FINDINGS[item["finding_class"]]
        sites = _sites(item["finding_class"], finding, item["path"], item.get("line"))
        if len(sites) < 2:
            continue
        checked += 1

        assert item.get("sites") == sites, (
            f"{item['finding_class']} names {len(sites)} places and the item "
            f"carries {item.get('sites')}"
        )
        assert item["path"] in sites[0], (
            f"{item['finding_class']}'s item points outside its own sites"
        )

    assert checked >= 2, (
        f"only {checked} multi-place classes exercised; the entry found two"
    )


def test_no_multi_place_item_is_told_to_remove_one_copy() -> None:
    """The verb is the defect, not only the missing location.

    D165 corrected "remove" for risk patterns because it read as "delete
    the matched text", which clears a finding without resolving it. For
    a clone the same word is worse: deleting one copy breaks that file
    and leaves the duplication.
    """
    multi = [item for item in _items() if len(item.get("sites") or []) > 1]

    assert multi, "no multi-place items produced, so this asserts nothing"
    for item in multi:
        target = item["target"]

        assert not target.startswith("remove the"), (
            f"{item['finding_class']} still says {target!r}, which for a finding "
            "in several places instructs deleting one of them"
        )
        # The single-place wording is what must not survive, and the
        # locations are asserted where they are rendered rather than
        # here. `"alone leaves" in target` stood in this place and
        # pinned the first phrasing that shipped: a clearer target
        # would have failed it, and any target containing the phrase
        # would have passed however wrong the rest of it was.
        assert target != f"remove the {_LABELS[item['finding_class']]}", target


def test_every_surface_that_prints_a_location_prints_the_others() -> None:
    """The item carrying them is half the fix; the surfaces are the rest.

    The first version of this change put the other locations in the
    bounded prompt and left the copy-paste block — the one that travels
    alone into an agent, with no report around it — still naming one
    place. That is D157's shape exactly: a claim fixed on one surface of
    one report, which survived a full cycle because the other surface
    was never checked.

    The surfaces are named because they are the two that print
    `Location:`; both read `other_sites`, so this asserts they are
    actually wired to it rather than each carrying their own rule.
    """
    from maintainability_audit._prompt_sections import prompt_work_order
    from maintainability_audit._work_order_view import prompt_body_lines

    multi = [item for item in _items() if len(item.get("sites") or []) > 1]
    assert multi, "no multi-place items produced, so this asserts nothing"

    for item in multi:
        full = {**item, "rationale": "because", "class_delta": 0.0,
                "class_count": 1, "class_paths": 1, "band": "quick-win",
                "verification": "pytest -q"}
        block = "\n".join(prompt_body_lines(full))
        bounded = "\n".join(prompt_work_order({"work_order": [full]}))

        for site in item["sites"][1:]:
            assert site in block, (
                f"the copy-paste block for {item['finding_class']} never names "
                f"{site}, so an agent given only that block sees one copy"
            )
            assert site in bounded, (
                f"the bounded prompt for {item['finding_class']} never names {site}"
            )


def test_a_single_place_class_gains_no_sites() -> None:
    """Dead code is one declaration; a risk pattern is one match.

    Attaching a site list to them would put a second location in a
    prompt that has one, which is the opposite failure and just as
    confusing.
    """
    single = [item for item in _items() if not item.get("sites")]

    assert single, "every class claimed to be multi-place, which cannot be right"
    for item in single:
        assert "sites" not in item, item["finding_class"]
