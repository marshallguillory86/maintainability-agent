"""The security pillar reports what the tool that owns it measured.

[ADR 007](../docs/adr-007-pillars-and-practice.md) makes the source
framework's five pillars the top-level taxonomy and delegates **Security
to `secure-code-agent`**, reported as `NotApplicable` so silence is never
read as safety. That entry was a placeholder for an artifact: the other
tool measures the pillar, so the other tool reports it.

`secure-code-agent` 0.5.0 emits `security-pillar.json` against this
tool's vocabulary — the scope words, the two-axis split and the posture
matrix all come from `_pillars.py`, because two tools saying "level 3"
about one repository have to mean the same thing by it. This is the
consuming half.

Three properties are held here, and each is a way the join could quietly
go wrong:

**Absence keeps the placeholder.** Most repositories run one tool. No
file is the ordinary case, not a failure.

**A document that cannot be trusted is refused, not partly believed.**
Wrong schema, wrong version, bad JSON, wrong shape — every one falls
back to the placeholder rather than reporting a posture assembled from a
document this tool does not understand.

**The two axes are never averaged**, whoever measured them. The
prohibition is ADR 007 §2's and it does not weaken because the numbers
arrived from another process.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintainability_audit._delegated_pillar import (
    DEFAULT_PILLAR_PATH,
    SCHEMA,
    SCHEMA_VERSION,
    read_delegated,
)
from maintainability_audit._pillars import PILLARS, Scope, pillar_report


def _document(**overrides) -> dict:
    """A minimal document in the shape secure-code-agent 0.5.0 writes."""
    payload = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "producer": {"tool": "secure-code-agent", "version": "0.5.0"},
        "generated": "2026-09-10T14:03:33Z",
        "pillar": "security",
        "scope": "owned",
        "reason": "secure-code-agent owns the security pillar",
        "practice": {"level": 5, "summary": "discipline", "signals": [], "caps": []},
        "condition": None,
        "posture": "unverified",
        "verified_grade": None,
        "evidence_status": "incomplete",
        "evidence_reasons": ["scanner coverage is partial"],
        "coverage": {"status": "partial", "scanners_run": [], "scanners_missing": []},
        "findings_by_severity": {},
        "reported_not_scored": {},
        "loc_scanned": 1000,
    }
    payload.update(overrides)
    return payload


def _write(root: Path, payload) -> None:
    target = root / DEFAULT_PILLAR_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")


def _security(rows: list[dict]) -> dict:
    found = [row for row in rows if row["pillar"] == "security"]
    assert found, "the report no longer carries a security pillar"
    return found[0]


# --- the pillar is delegated in the first place ----------------------------

def test_security_is_the_delegated_pillar_this_reads_for() -> None:
    """Derived from `PILLARS`, so a scope change cannot leave this stale.

    Covers existing behaviour: ADR 007 declared the delegation before
    this file existed. It passes at any base where the decision stands,
    which is what makes it a guard.
    """
    delegated = {p.name for p in PILLARS if p.scope is Scope.DELEGATED}
    assert delegated == {"security"}, (
        f"the delegated pillars are now {sorted(delegated)}; this consumer "
        "reads for security alone and would silently ignore the others"
    )


# --- absence ---------------------------------------------------------------

def test_no_document_keeps_the_placeholder(tmp_path: Path) -> None:
    """One tool is the ordinary case, and it is not a failure."""
    assert read_delegated(tmp_path) is None
    entry = _security(pillar_report({"aspects": {}}, {"level": 3}, None))
    assert entry["scope"] == "delegated"
    assert entry["condition"] is None
    assert entry.get("delegated_to") is None, (
        "a pillar with no document claimed a producer"
    )


# --- refusal ---------------------------------------------------------------

@pytest.mark.parametrize(("name", "payload"), [
    ("wrong schema", _document(schema="some-other-tool/pillar")),
    ("wrong version", _document(schema_version=SCHEMA_VERSION + 1)),
    ("not an object", [1, 2, 3]),
    ("not json", "{not json at all"),
])
def test_an_untrustworthy_document_is_refused(tmp_path: Path, name: str, payload) -> None:
    """Refused whole, never read in part.

    A posture assembled from a document this tool does not understand is
    worse than no posture: the placeholder at least says who to ask.
    """
    _write(tmp_path, payload)
    assert read_delegated(tmp_path) is None, f"{name} was accepted"


def test_a_fifo_refuses_rather_than_hanging(tmp_path: Path) -> None:
    """The path comes from the audited tree, so D145's rule applies."""
    import os

    from maintainability_audit._operator_reads import PathNotAllowed

    target = tmp_path / DEFAULT_PILLAR_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(target)
    with pytest.raises(PathNotAllowed):
        read_delegated(tmp_path)


# --- the join ---------------------------------------------------------------

def test_a_trusted_document_becomes_the_pillar(tmp_path: Path) -> None:
    """The entry carries the measurement and names who made it."""
    _write(tmp_path, _document())
    document = read_delegated(tmp_path)
    assert document is not None

    entry = _security(pillar_report({"aspects": {}}, {"level": 2}, {"security": document}))
    assert entry["scope"] == "delegated", "this tool still does not measure security"
    assert entry["delegated_to"] == "secure-code-agent"
    assert entry["producer_version"] == "0.5.0"
    assert entry["practice"] == 5
    assert entry["posture"] == "unverified"


def test_the_producers_practice_wins_not_this_tools(tmp_path: Path) -> None:
    """The delegated pillar is not scored on this tool's practice axis.

    `pillar_report` is handed this repository's own practice level for
    the pillars it owns. Letting that number stand in for the delegated
    one would report a maintainability practice level as a *security*
    maturity — two different judgments wearing one number.
    """
    _write(tmp_path, _document(practice={"level": 1, "summary": "none", "signals": [], "caps": []}))
    document = read_delegated(tmp_path)
    entry = _security(pillar_report({"aspects": {}}, {"level": 5}, {"security": document}))
    assert entry["practice"] == 1, (
        "the security pillar reported this tool's practice level instead of "
        "the security tool's"
    )


def test_the_entry_never_offers_a_mean_of_the_two_axes(tmp_path: Path) -> None:
    """ADR 007 §2 does not weaken because another process measured them.

    Both axes are present and no field combines them. The producer keeps
    the same guard over its own module; this is the consuming half.
    """
    _write(tmp_path, _document(condition=4.0, practice={
        "level": 2, "summary": "s", "signals": [], "caps": []}))
    document = read_delegated(tmp_path)
    entry = _security(pillar_report({"aspects": {}}, {"level": 3}, {"security": document}))

    assert entry["condition"] == 4.0
    assert entry["practice"] == 2
    mean = (4.0 + 2) / 2
    numbers = [
        value for key, value in entry.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    assert mean not in numbers, (
        f"the entry carries {mean}, the mean of its two axes; practice and "
        "condition answer different questions and must never be combined"
    )

# --- it has to reach the reader --------------------------------------------

def test_every_skin_renders_the_delegated_pillar_as_a_number(tmp_path: Path) -> None:
    """The entry is shaped for the renderers, not only for the JSON.

    The first cut carried the producer's practice *block* under
    `practice`, which every skin prints into a column beside the other
    pillars — so the Markdown table rendered
    `{'level': 5, 'summary': ...}` into a cell. The data was right and
    the report was garbage.

    That is this project's oldest failure shape: the product produced
    the right thing and nothing told the reader. Both skins are checked
    here because checking one is how the other drifts.
    """
    from maintainability_audit._html_report_sections import _pillars_section
    from maintainability_audit._scan_view import pillars_markdown

    _write(tmp_path, _document(practice={
        "level": 5, "summary": "discipline", "signals": [], "caps": []}))
    document = read_delegated(tmp_path)
    practice = {"level": 4, "summary": "own", "signals": [], "caps": []}
    rows = pillar_report({"aspects": {}}, practice, {"security": document})

    entry = _security(rows)
    assert isinstance(entry["practice"], int), (
        f"practice is {type(entry['practice']).__name__}; every skin prints "
        "it into a column and a dict lands in the cell verbatim"
    )
    assert entry["practice_detail"]["signals"] == [], (
        "the producer's block was dropped; the signals naming the files "
        "that prove a maturity level are what make it checkable"
    )

    for name, lines in (
        ("markdown", pillars_markdown(rows, practice)),
        ("html", _pillars_section({"pillars": rows, "practice": practice})),
    ):
        rendered = "\n".join(lines)
        assert "'level'" not in rendered and "{" not in rendered.split("security")[-1][:80], (
            f"the {name} skin printed a raw structure for the delegated "
            f"pillar: {rendered[:200]!r}"
        )
