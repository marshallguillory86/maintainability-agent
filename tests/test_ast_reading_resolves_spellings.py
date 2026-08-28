"""The sweeps' own falsifier: every spelling of the same call.

`test_git_argv` and `test_analyzer_xml_bounds` both sweep the package for
a class of call. Each sweep is only as good as its name resolution, and
that resolution has now been wrong twice -- once by matching a literal
attribute, once by resolving the *bound* name when the call site reads a
dotted path. Both times the sweep passed while the thing it protected
was reachable, which is the failure a sweep exists to prevent.

So the resolver is tested against source directly, one case per spelling
Python accepts. A tenth spelling found tomorrow belongs here first.
"""

from __future__ import annotations

import ast

import pytest
from _ast_reading import calls_reaching, reachable_names

PARSERS = {"fromstring", "parse", "XML", "fromstringlist", "XMLParser"}

REACHES_XML = [
    ("plain from-import", "from xml.etree import ElementTree\nElementTree.fromstring(x)"),
    ("aliased from-import", "from xml.etree import ElementTree as E\nE.fromstring(x)"),
    ("member import", "from xml.etree.ElementTree import fromstring\nfromstring(x)"),
    ("aliased member", "from xml.etree.ElementTree import fromstring as f\nf(x)"),
    ("dotted import", "import xml.etree.ElementTree\nxml.etree.ElementTree.fromstring(x)"),
    ("dotted import, aliased", "import xml.etree.ElementTree as ET\nET.fromstring(x)"),
    ("package import", "from xml import etree\netree.ElementTree.fromstring(x)"),
    ("submodule import", "import xml.etree\nxml.etree.ElementTree.fromstring(x)"),
    (
        "import inside a function",
        "def f():\n    from xml.etree import ElementTree\n    return ElementTree.parse(x)",
    ),
    ("other member", "from xml.etree import ElementTree\nElementTree.XMLParser()"),
]


@pytest.mark.parametrize(
    "source", [source for _, source in REACHES_XML],
    ids=[name for name, _ in REACHES_XML],
)
def test_every_spelling_of_an_unguarded_parse_is_seen(source: str) -> None:
    """A parse the sweep cannot see is a parse the sweep does not bound."""
    tree = ast.parse(source)
    aliases, direct = reachable_names(tree, "xml.etree", PARSERS)
    assert calls_reaching(tree, aliases, direct, PARSERS), (
        f"this spelling reaches the XML expander unswept:\n{source}"
    )


SPAWNS = {"run", "Popen", "call", "check_call", "check_output"}

REACHES_SUBPROCESS = [
    ("plain import", "import subprocess\nsubprocess.run(argv)"),
    ("aliased import", "import subprocess as sp\nsp.run(argv)"),
    ("member import", "from subprocess import run\nrun(argv)"),
    ("aliased member", "from subprocess import run as r\nr(argv)"),
    ("Popen", "import subprocess\nsubprocess.Popen(argv)"),
]


@pytest.mark.parametrize(
    "source", [source for _, source in REACHES_SUBPROCESS],
    ids=[name for name, _ in REACHES_SUBPROCESS],
)
def test_every_spelling_of_a_spawn_is_seen(source: str) -> None:
    """A spawn the sweep cannot see is a spawn with no timeout rule."""
    tree = ast.parse(source)
    aliases, direct = reachable_names(tree, "subprocess", SPAWNS)
    assert calls_reaching(tree, aliases, direct, SPAWNS), (
        f"this spelling spawns a child unswept:\n{source}"
    )


UNRELATED = [
    ("a different package", "import json\njson.loads(x)"),
    ("same member, other module", "from ast import parse\nparse(x)"),
    ("a method of a local object", "self.parse(x)"),
    ("shadowed name, no import", "parse(x)"),
]


@pytest.mark.parametrize(
    "source", [source for _, source in UNRELATED],
    ids=[name for name, _ in UNRELATED],
)
def test_the_resolver_does_not_widen_to_unrelated_calls(source: str) -> None:
    """A sweep that flags everything is retired by whoever hits it next."""
    tree = ast.parse(source)
    aliases, direct = reachable_names(tree, "xml.etree", PARSERS)
    assert not calls_reaching(tree, aliases, direct, PARSERS), (
        f"the sweep claimed an unrelated call:\n{source}"
    )
