"""The declarative parsers read untrusted analyzer output safely.

`_generic` is the module a new tool is added through without writing
code: a spec says where the findings array is and which keys hold the
location, and one of four parsers does the rest. That makes these
functions the widest untrusted-input surface in the package — every one
of them is handed whatever a third-party binary printed — and the
2026-09-10 work-order run measured them at **60.4%**, the lowest in the
tree and the only genuine coverage gap among 58 unpaired-file findings.

What is exercised here is the behaviour a malformed or merely chatty
tool produces: a missing key, a wrong shape at the declared path, a
progress line in the middle of a stream, an entry that is not an object.
The rule each parser follows is not "trust the tool" and not "fail on
anything unexpected" — it is stated per function below, because the two
formats deliberately differ.

Covers existing behaviour: these parsers shipped before this file. The
gap was in the tests, not in them.
"""
from __future__ import annotations

import pytest

from maintainability_audit._generic import (
    DECLARED,
    PARSERS,
    _dig,
    _rule_id,
    parse_json_findings,
    parse_json_lines,
    specs_by_format,
)


def _spec(slug: str):
    spec = DECLARED.get(slug)
    assert spec is not None, f"{slug} is no longer a declared tool"
    return spec


def _json_findings_spec():
    """A declared spec that actually uses the JSON-array parser."""
    for spec in DECLARED.values():
        if spec.output_format == "json-findings":
            return spec
    pytest.skip("no declared tool uses the json-findings parser")


def _json_lines_spec():
    for spec in DECLARED.values():
        if spec.output_format == "json-lines":
            return spec
    pytest.skip("no declared tool uses the json-lines parser")


# --- rule identity ---------------------------------------------------------

def test_the_first_populated_rule_key_wins_in_declared_order() -> None:
    """A rule id is what makes a finding groupable and suppressible.

    The order is a preference, not an accident: pylint ships both a
    `symbol` and a `message-id`, and `missing-module-docstring` tells a
    reader more than `C0114`.
    """
    both = {"symbol": "missing-module-docstring", "message-id": "C0114"}
    assert _rule_id(both) == "missing-module-docstring"
    assert _rule_id({"message-id": "C0114"}) == "C0114"


def test_an_item_with_no_rule_key_has_no_rule_rather_than_a_blank_one() -> None:
    """`None` and `""` are different answers; a blank would group.

    Every finding with an empty-string rule would collapse into one
    group, which reads as a repeated defect that does not exist.
    """
    assert _rule_id({}) is None
    assert _rule_id({"symbol": ""}) is None
    assert _rule_id({"symbol": None, "code": 0}) is None


# --- dotted traversal ------------------------------------------------------

def test_a_dotted_path_walks_nested_objects() -> None:
    assert _dig({"a": {"b": {"c": 7}}}, "a.b.c") == 7


def test_traversal_stops_at_a_non_object_instead_of_raising() -> None:
    """A tool that changed its shape must not crash the audit.

    The declared path is a promise about someone else's output format,
    and it is the kind of promise that breaks on a minor release. A
    `None` here becomes an absent field on the finding, which is
    recoverable; a `TypeError` ends the run.
    """
    assert _dig({"a": [1, 2, 3]}, "a.b") is None
    assert _dig({"a": "text"}, "a.b") is None
    assert _dig(None, "a") is None


def test_an_empty_path_returns_the_payload_unchanged() -> None:
    payload = {"a": 1}
    assert _dig(payload, "") is payload


# --- JSON array format -----------------------------------------------------

def test_a_wrong_shape_at_the_declared_path_is_refused_by_name() -> None:
    """Refused loudly, and the message names the tool and the path.

    This is the one place these parsers raise rather than degrade, and
    the reason is that the *declaration* is wrong rather than the data:
    somebody said the findings live at a path where an object lives.
    A silent empty result would report the tool as clean.
    """
    spec = _json_findings_spec()
    with pytest.raises(ValueError) as caught:
        parse_json_findings('{"not": "a list"}', spec, "style")
    assert spec.slug in str(caught.value)


def test_empty_output_reads_as_no_findings_rather_than_an_error() -> None:
    """A tool that found nothing prints nothing. That is a clean run."""
    spec = _json_findings_spec()
    assert parse_json_findings("", spec, "style").findings == ()


def test_entries_that_are_not_objects_are_skipped_not_fatal() -> None:
    """One malformed entry must not discard the findings around it."""
    spec = _json_findings_spec()
    path_key, line_key, message_key = spec.json_keys
    good = {path_key: "a.py", line_key: 3, message_key: "something"}
    extraction = parse_json_findings(
        _as_declared_document(spec, [good, "junk", None, 42]), spec, "style")
    assert len(extraction.findings) == 1
    assert extraction.findings[0].path == "a.py"


def test_a_finding_carries_the_concern_it_was_parsed_for() -> None:
    spec = _json_findings_spec()
    path_key, line_key, message_key = spec.json_keys
    item = {path_key: "a.py", line_key: 1, message_key: "m"}
    found = parse_json_findings(
        _as_declared_document(spec, [item]), spec, "types").findings[0]
    assert found.concept == "types"
    assert found.tool == spec.slug


def _as_declared_document(spec, items: list) -> str:
    """Wrap items where this spec says its findings live."""
    import json

    if not spec.json_path:
        return json.dumps(items)
    document: dict = {}
    cursor = document
    parts = [p for p in spec.json_path.split(".") if p]
    for part in parts[:-1]:
        cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = items
    return json.dumps(document)


# --- JSON lines format -----------------------------------------------------

def test_progress_noise_between_objects_is_skipped() -> None:
    """Streaming tools share the stream with summary lines.

    Skipping non-objects rather than failing is what keeps a chatty tool
    usable — and it is a deliberate difference from the array parser
    above, which refuses a wrong shape. There the *declaration* was
    wrong; here the tool is simply talking.
    """
    spec = _json_lines_spec()
    path_key, line_key, message_key = spec.json_keys
    import json

    stream = "\n".join([
        "Scanning 12 files...",
        json.dumps({path_key: "a.py", line_key: 2, message_key: "first"}),
        "",
        "Found 1 issue",
        json.dumps({path_key: "b.py", line_key: 9, message_key: "second"}),
        "Done.",
    ])
    findings = parse_json_lines(stream, spec, "types").findings
    assert [f.path for f in findings] == ["a.py", "b.py"]


def test_an_empty_stream_is_a_clean_run() -> None:
    spec = _json_lines_spec()
    assert parse_json_lines("", spec, "types").findings == ()


# --- the format registry ---------------------------------------------------

def test_every_declared_tool_names_a_parser_that_exists() -> None:
    """The population is the declaration table, not a list typed here.

    A tool added tomorrow with a typo in its `output_format` reaches the
    `_read` fallthrough and raises at audit time. This fails at test
    time instead, and it covers the tool nobody remembered to add here.
    """
    assert DECLARED, "no declared tools; this sweep would prove nothing"
    wrong = {
        spec.slug: spec.output_format
        for spec in DECLARED.values()
        if spec.output_format not in PARSERS
    }
    assert not wrong, f"declared tools name unknown parsers: {wrong}"


def test_the_format_index_accounts_for_every_declared_tool() -> None:
    grouped = specs_by_format()
    listed = {slug for slugs in grouped.values() for slug in slugs}
    assert listed == set(DECLARED), (
        "specs_by_format lost or invented a tool: "
        f"{listed ^ set(DECLARED)}"
    )
