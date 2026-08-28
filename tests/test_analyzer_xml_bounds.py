"""D46: an analyzer cannot decide how much work parsing its output is.

Filed as inferred rather than demonstrated — the input is a child this
project spawned, not an upload, so the realistic exposure is resource
exhaustion rather than classic XXE. The demonstration turned out to be
easy, and it is the *internal* entity expansion `ElementTree` still
performs: four levels of the standard shape take a 400-byte document to
30,000 characters, and every further level multiplies by ten.

External entity expansion and DTD retrieval are already safe in this
interpreter. Those are the ones "XXE" usually means, which is probably
why the entry hedged.
"""

from __future__ import annotations

import pytest
from _ast_reading import calls_reaching, reachable_names

from maintainability_audit._xml import (
    MAX_ANALYZER_XML_CHARS,
    AnalyzerXmlRefused,
    parse_analyzer_xml,
)

# The classic shape, kept small: each level multiplies by ten, so this
# is the mechanism rather than an actual attempt to exhaust the host.
BOMB = """<?xml version="1.0"?>
<!DOCTYPE lolz [
 <!ENTITY lol "lol">
 <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
 <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
]>
<checkstyle>&lol2;</checkstyle>"""

REAL_CHECKSTYLE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<checkstyle version="10.0">\n'
    '  <file name="Main.java">\n'
    '    <error line="4" severity="warning" message="Line too long" '
    'source="com.puppycrawl.tools.checkstyle.checks.LineLengthCheck"/>\n'
    "  </file>\n"
    "</checkstyle>\n"
)

REAL_BUGCOLLECTION = (
    '<BugCollection version="4.7.3">\n'
    '  <BugInstance type="NP_NULL_ON_SOME_PATH" priority="1">\n'
    '    <SourceLine sourcepath="Main.java" start="9" end="9"/>\n'
    "  </BugInstance>\n"
    "</BugCollection>\n"
)


def test_an_entity_bomb_is_refused_before_it_is_expanded() -> None:
    """The demonstration, and the reason the entry stops being inferred."""
    with pytest.raises(AnalyzerXmlRefused) as refused:
        parse_analyzer_xml(BOMB, fallback="<checkstyle/>")
    assert "entity" in str(refused.value).lower()


def test_a_declared_doctype_is_refused_even_without_entities() -> None:
    """No analyzer this project runs emits a DTD, so one is not our output."""
    with pytest.raises(AnalyzerXmlRefused):
        parse_analyzer_xml(
            '<!DOCTYPE checkstyle SYSTEM "http://example.invalid/c.dtd">'
            "<checkstyle/>",
            fallback="<checkstyle/>",
        )


def test_absurdly_large_output_is_refused_rather_than_read() -> None:
    """The flood case, which the declaration check cannot catch.

    A bomb is small by construction; this is the other direction — a
    tool that simply will not stop writing.
    """
    with pytest.raises(AnalyzerXmlRefused) as refused:
        parse_analyzer_xml("<checkstyle>" + "x" * MAX_ANALYZER_XML_CHARS,
                           fallback="<checkstyle/>")
    assert "characters" in str(refused.value)


@pytest.mark.parametrize(
    ("payload", "fallback", "tag"),
    [
        (REAL_CHECKSTYLE, "<checkstyle/>", "checkstyle"),
        (REAL_BUGCOLLECTION, "<BugCollection/>", "BugCollection"),
        (None, "<checkstyle/>", "checkstyle"),
        ("", "<BugCollection/>", "BugCollection"),
    ],
)
def test_real_analyzer_output_still_parses(
    payload: str | None, fallback: str, tag: str,
) -> None:
    """The guard has to admit the output it exists to protect.

    Including the empty case: a tool that ran and found nothing must
    stay distinguishable from one whose output could not be read.
    """
    assert parse_analyzer_xml(payload, fallback=fallback).tag == tag


def test_a_refusal_reads_as_unparseable_output_to_every_caller() -> None:
    """Refusal is a stated coverage gap, never a crash.

    Both call sites already catch `ElementTree.ParseError` and convert
    it into "unreadable output", which is exactly the right handling for
    output this project declines to read — so the refusal subclasses it
    rather than introducing a second path nobody catches.
    """
    from xml.etree import ElementTree

    assert issubclass(AnalyzerXmlRefused, ElementTree.ParseError)

    from maintainability_audit._generic import parse_checkstyle

    with pytest.raises(ElementTree.ParseError):
        parse_checkstyle(BOMB, "checkstyle", "style")


def test_no_parse_site_bypasses_the_guard() -> None:
    """`ElementTree.fromstring` lives in one place, behind the checks.

    Swept rather than asserted at the two call sites that exist today,
    because a third added tomorrow is exactly how this comes back.
    """
    import ast
    from pathlib import Path

    parsers = {"fromstring", "parse", "XML", "fromstringlist", "XMLParser"}
    package = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"
    offenders = []
    for path in sorted(package.rglob("*.py")):
        if path.name == "_xml.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        aliases, direct = reachable_names(tree, "xml.etree", parsers)
        offenders += [
            f"{path.name}:{call.lineno}"
            for call in calls_reaching(tree, aliases, direct, parsers)
        ]

    assert not offenders, (
        "analyzer XML parsed outside the guard, so an entity bomb would "
        f"reach the expander: {offenders}"
    )
