"""Parsing analyzer XML without letting the analyzer decide how much work that is.

`ElementTree` expands internal entities. Four levels of the standard
"billion laughs" shape expand a 400-byte document to 30,000 characters
in this interpreter, and each further level multiplies by ten — so a
small, well-formed file from a hostile or PATH-hijacked analyzer can
exhaust the memory of the process that asked for an audit (D46).

External entities and DTD retrieval are already safe here; the entry
filed this as inferred rather than demonstrated, and the demonstration
turned out to be the *internal* expansion, which is the one
`ElementTree` still performs.

**Refusing the declaration rather than neutering the expander.** The
obvious fix is to disable expat's `EntityDeclHandler`, and CPython 3.11
does not expose the underlying parser to reach it. The narrower guard
is better anyway: no analyzer this project runs emits a DTD, so a
document that declares entities is not output this code should be
trying to read. It is refused before a parser sees it.

`AnalyzerXmlRefused` subclasses `ElementTree.ParseError` on purpose:
every caller already treats unreadable analyzer output as a stated gap
rather than a crash, and a refusal is exactly that — output this
project will not read, reported as coverage the run did not get.
"""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree

# Generous next to real analyzer output — a Checkstyle run over a large
# tree is a few megabytes — and far below what would trouble the host.
# This bounds the flood case; the declaration check below bounds the
# amplification case, which a size limit cannot catch because the input
# is small by construction.
MAX_ANALYZER_XML_CHARS = 64 * 1024 * 1024

# A document that declares entities, or announces a DTD that could.
# Both appear in the byte stream only as markup: inside text or CDATA a
# real analyzer would have escaped the `<`.
_DECLARATIONS = ("<!ENTITY", "<!DOCTYPE")


class AnalyzerXmlRefused(ElementTree.ParseError):
    """Analyzer output this project declines to parse."""


def parse_analyzer_xml(text: str | None, *, fallback: str) -> Any:
    """Parse analyzer XML, or refuse it. Never parses a declared entity.

    `fallback` is the empty document each caller substitutes when a tool
    produced nothing, so "ran and found nothing" stays distinct from
    "could not be read".
    """
    payload = text or fallback
    if len(payload) > MAX_ANALYZER_XML_CHARS:
        raise AnalyzerXmlRefused(
            f"analyzer XML is {len(payload)} characters, over the "
            f"{MAX_ANALYZER_XML_CHARS} this project will read"
        )
    upper = payload.upper()
    for declaration in _DECLARATIONS:
        if declaration in upper:
            raise AnalyzerXmlRefused(
                f"analyzer XML declares {declaration.lstrip('<!').lower()}; "
                "entity expansion is refused because a small document can "
                "expand without bound"
            )
    return ElementTree.fromstring(payload)  # noqa: S314 - declarations refused above
