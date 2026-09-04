"""D48: every named exception is either a declared refusal or excluded on purpose.

A reviewer eyeballing ``ANTICIPATED_REFUSALS`` got the set wrong twice
in one night, in opposite directions. This file derives the product's
named exception types from the package and demands each one is either
in the tuple the transport excepts, or named here with a reason. Adding
a sixth type and touching neither fails the build.
"""

from __future__ import annotations

import ast
import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
from _mcp_fixtures import _config, _repo, _resource_text

from maintainability_audit._mcp_audit import InvalidAuditArgument
from maintainability_audit._mcp_grants import _RootLedger
from maintainability_audit._mcp_setup import SetupRequired
from maintainability_audit.baseline import StaleBaseline
from maintainability_audit.mcp_server import (
    ANTICIPATED_REFUSALS,
    _audit_tool_for,
    create_server,
)

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"
MCP_SERVER = PACKAGE / "mcp_server.py"
# Every module that binds an MCP seam. The transport is two files
# since the resource bindings moved out of `mcp_server`.
TRANSPORT_MODULES = (MCP_SERVER, PACKAGE / "_mcp_resources.py")

# Exception subclasses that must not be translated. A reason is the
# proof; an empty string is not a classification.
EXCLUSIONS: dict[str, str] = {
    "UnknownTarget": (
        "CLI-only. `--init-agent-standards` is a generator command that "
        "returns before any audit runs and has no MCP door, so this refusal "
        "cannot reach the transport. It exists because an agent nobody has a "
        "convention for must supply its own instructions path rather than be "
        "given a generated filename it will never open"
    ),
    "StaleStandingGrant": (
        "never reaches the transport: `_stored_grants` raises it where a "
        "grant is used, and `authorize_repository` re-raises it as "
        "PathNotAllowed, which is in the tuple. It exists as its own type "
        "so the rule can live beside the grant logic without that module "
        "importing the MCP layer (D83)"
    ),
    "EvidenceValidationError": (
        "on the MCP tool path the report is built internally, so a "
        "failure is an internal bug; the crash path is right to withhold it"
    ),
    "UnsupportedReportSchema": (
        "subclass of EvidenceValidationError; same exclusion"
    ),
    "InvalidRevspec": (
        "the MCP door converts it: validate_revspec catches it and raises "
        "InvalidAuditArgument, which is in the tuple, and changed_paths is "
        "only reached on that path after validation has already run"
    ),
    "GitCommandFailed": (
        "a git invocation that was expected to succeed did not — an "
        "environmental fault, not a refusal a caller can act on, and its "
        "message can carry an OSError naming host paths; the non-repository "
        "and shallow-clone cases a user can actually cause are answered by "
        "probe_git instead of raised"
    ),
    "SkillDrift": (
        "CLI --install-skill only; never raised through the MCP tool "
        "or resource seams"
    ),
}

_EXCEPTION_ROOTS = frozenset(
    {"BaseException", "Exception", "ValueError", "RuntimeError", "Error"}
)


def _base_names(node: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _named_exceptions() -> dict[str, str]:
    """Every class in the package that inherits from Exception, by name.

    Walks the source, not the import graph, so a type added in a module
    nobody imports still has to be classified.
    """
    bases_of: dict[str, set[str]] = {}
    defined_in: dict[str, str] = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases_of[node.name] = _base_names(node)
                defined_in[node.name] = str(path.relative_to(PACKAGE.parent.parent))

    named: set[str] = set()
    changed = True
    while changed:
        changed = False
        for name, bases in bases_of.items():
            if name in named:
                continue
            if bases & _EXCEPTION_ROOTS or bases & named:
                named.add(name)
                changed = True
    return {name: defined_in[name] for name in sorted(named)}


def _except_handler_types(tree: ast.AST) -> tuple[list[str], list[tuple[str, ...]]]:
    """Except names, and except-tuples, from one module."""
    names: list[str] = []
    groups: list[tuple[str, ...]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or node.type is None:
            continue
        if isinstance(node.type, ast.Name):
            names.append(node.type.id)
        elif isinstance(node.type, ast.Tuple):
            groups.append(tuple(
                elt.id for elt in node.type.elts if isinstance(elt, ast.Name)
            ))
    return names, groups


def test_every_named_exception_is_a_declared_refusal_or_excluded() -> None:
    """A sixth type added tomorrow, with nobody touching the tuple, fails here.

    The tuple is the MCP translation set. The derivation is every named
    exception in the package, so SkillDrift (CLI-only) and
    EvidenceValidationError (internal on this path) have to be excluded
    with a reason rather than silently omitted.
    """
    discovered = _named_exceptions()
    anticipated = {cls.__name__ for cls in ANTICIPATED_REFUSALS}

    empty_reasons = [name for name, reason in EXCLUSIONS.items() if not reason.strip()]
    assert not empty_reasons, (
        "an exclusion without a reason is not a classification: "
        f"{empty_reasons}"
    )

    overlap = anticipated & set(EXCLUSIONS)
    assert not overlap, (
        f"classified as both a refusal and an exclusion: {sorted(overlap)}"
    )

    missing = set(EXCLUSIONS) - set(discovered)
    assert not missing, (
        f"exclusions that are not named exception types in the package: {sorted(missing)}"
    )

    stale = anticipated - set(discovered)
    assert not stale, (
        f"ANTICIPATED_REFUSALS names types the package does not define: {sorted(stale)}"
    )

    unclassified = set(discovered) - anticipated - set(EXCLUSIONS)
    assert not unclassified, (
        "named exception types with no classification — add each to "
        "ANTICIPATED_REFUSALS or to EXCLUSIONS with a reason: "
        + ", ".join(f"{name} ({discovered[name]})" for name in sorted(unclassified))
    )

    assert anticipated == set(discovered) - set(EXCLUSIONS), (
        "ANTICIPATED_REFUSALS is not exactly the discovered types minus "
        f"the exclusions. tuple={sorted(anticipated)} "
        f"expected={sorted(set(discovered) - set(EXCLUSIONS))}"
    )
    assert all(issubclass(cls, BaseException) for cls in ANTICIPATED_REFUSALS)


def test_the_transport_excepts_the_named_tuple_not_a_copy() -> None:
    """The three seams must except ANTICIPATED_REFUSALS, not a stale list.

    Membership in the tuple is not enough if a copy at an ``except``
    site omits a type. The night's second miss — StaleBaseline and
    PolicyError dropped from the tuple — would have been invisible at
    those sites if they listed three types by hand.

    Scanned across every transport module, not just `mcp_server`. The
    report resource and its security validator moved to
    `_mcp_resources` when that file crossed the length gate, and this
    check counted seams in one file: after the move it saw one of three
    and would have been satisfied by deleting the other two. The
    module that arrived carrying them excepted bare `ValueError`, which
    is the defect D48 exists to prevent, so the gap was not theoretical.
    """
    caught: list[str] = []
    listed: list[tuple[str, ...]] = []
    for module in TRANSPORT_MODULES:
        tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
        module_caught, module_listed = _except_handler_types(tree)
        caught += module_caught
        listed += module_listed

    anticipated_names = {cls.__name__ for cls in ANTICIPATED_REFUSALS}
    # A hand-written subset of the tuple is the night's second miss
    # wearing a different coat. `except (PathNotAllowed, ValueError)` in
    # the setup resolver is not that: ValueError is not an anticipated
    # name, and that handler swallows so the tool body can raise.
    stale = [group for group in listed if group and set(group) <= anticipated_names]

    assert caught.count("ANTICIPATED_REFUSALS") >= 3, (
        "the tool, the report resource and its security validator must "
        f"except ANTICIPATED_REFUSALS; found {caught} across "
        f"{[m.name for m in TRANSPORT_MODULES]}"
    )
    assert not stale, (
        "an except site lists anticipated types by hand instead of the "
        f"named tuple: {stale}"
    )


def _tool_for(root: Path) -> Any:
    """The exact coroutine `_bind_audit_tool` registers, over one allowed root.

    Driving the registered seam rather than a client keeps this
    assertion independent of the resolved SDK. `mcp` 2.0.0 interpolates
    crash text into the caller's message, so "the message is not the
    generic crash string" is true on 2.0.0 whether or not the refusal
    was ever declared — an earlier draft of these tests asserted exactly
    that and passed with `StaleBaseline` deleted from the tuple. What is
    version-independent is our own translation: an anticipated refusal
    leaves this seam as the SDK's `ToolError`, and anything else leaves
    it as itself.
    """
    return _audit_tool_for(_RootLedger((root.resolve(),)))


def test_a_stale_baseline_leaves_the_seam_as_a_declared_refusal() -> None:
    """D48: the one anticipated type that travels this path, driven through it.

    Membership in ``ANTICIPATED_REFUSALS`` is settled by derivation, but
    derivation cannot show that a type ever reaches an ``except`` site.
    Until this test the entry recorded honestly that no seam test raised
    ``StaleBaseline``, and that gap was the whole argument for the type
    being in the tuple: a baseline written under an older identity
    scheme is refused, and the refusal is only useful if the sentence
    telling the caller to regenerate it survives translation.

    ``PolicyError`` deliberately has no twin here. It cannot reach these
    seams at all — ``_analysis.analyze()`` catches it and returns
    ``Analysis(error=...)`` — so a test driving it through the transport
    could only be written by faking a call path the product does not
    have. Architecture invariant 12 states that asymmetry rather than
    implying both types were proven the same way.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    with tempfile.TemporaryDirectory() as work:
        root = _repo(Path(work), config=_config())
        stale = root / ".maintainability" / "baseline.json"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text(
            json.dumps({"version": 1, "findings": ["anything"]}), encoding="utf-8",
        )
        tool = _tool_for(root)

        with pytest.raises(ToolError) as refusal:
            asyncio.run(tool(
                repository_root=str(root), format="json", action="run",
            ))

    assert "--write-baseline" in str(refusal.value), (
        "the refusal reached the caller without its remedy: "
        f"{refusal.value}"
    )
    assert isinstance(refusal.value.__cause__, StaleBaseline), (
        "the declared refusal lost the type it was translated from"
    )


def test_the_seams_own_argument_refusals_leave_it_declared() -> None:
    """D48: `InvalidAuditArgument` is the seam's own validation, and it teaches.

    These three are why the tuple names `InvalidAuditArgument` rather
    than the bare `ValueError` it subclasses. Each is a mistake the
    caller can correct from the message, and each left the seam
    undeclared until the type was named.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    with tempfile.TemporaryDirectory() as work:
        base = Path(work)
        root = _repo(base, config=_config())
        tool = _audit_tool_for(_RootLedger((base.resolve(),)))

        cases = {
            "repository_root is not a directory": {
                "repository_root": str(root / "README.md"), "action": "run",
            },
            "config_path is not a file": {
                "repository_root": str(root),
                "config_path": str(root / "nope.json"),
                "action": "run",
            },
            "format must be": {
                "repository_root": str(root), "format": "yaml", "action": "run",
            },
        }
        seen: dict[str, tuple[str, Any]] = {}
        for expected, arguments in cases.items():
            with pytest.raises(ToolError) as refusal:
                asyncio.run(tool(**arguments))
            seen[expected] = (str(refusal.value), refusal.value.__cause__)

    for expected, (message, cause) in seen.items():
        assert expected in message, (
            f"expected {expected!r} in the declared refusal, got: {message}"
        )
        assert isinstance(cause, InvalidAuditArgument), (
            f"{expected!r} lost the domain type it was translated from: "
            f"{type(cause).__name__}"
        )


def test_an_unconfigured_repository_refuses_through_the_resource_seam() -> None:
    """D48: the report resource's own handler, not the function beneath it.

    D30's refusal — an unconfigured repository gets no fallback-tier
    report, it gets a sentence naming `audit_repository` — was proved by
    calling `_report_markdown` directly. That is the shape of defect this
    file exists for: in-process the refusal looked perfect, and whether
    it survived the protocol was a separate question nobody asked.

    The resource's `except` is also the backstop for its own validator.
    The validator refuses an unauthorized root first, so every existing
    resource refusal is caught there; this root is authorized and
    unconfigured, which is the one way through to the handler below it.

    Unlike the two tool tests above, this one goes through the SDK, so
    what proves "declared" is version-dependent and neither the class
    nor `__cause__` is enough on its own. Undeclaring `SetupRequired`
    and reading what arrives: the type is still `ResourceError`, and
    `__cause__` is still `SetupRequired`, because the SDK wraps the
    escaping exception and chains it. On 2.1.0 the wrapper is the
    narrower `UnexpectedResourceError`, which subclasses `ResourceError`
    and so is caught by the same `pytest.raises`; excluding it is what
    separates the two there. On 2.0.0 no such class exists and the
    wrapper's message — "Error creating resource from template {uri}" —
    replaces the refusal's own text, so text is the discriminator there.
    Both assertions are load-bearing, on different versions.

    **Which text, though.** An audit of this test found that checking
    for `audit_repository` alone false-passes on 2.0.0: the wrapper
    interpolates the URI, the URI contains the repository path, and a
    repository directory *named* `audit_repository` puts the substring
    into the crash message. Reproduced — a crash then satisfied the
    check that exists to catch crashes.

    So the fixture builds the repository under exactly that directory
    name, and the discriminator is a fragment of D30's own sentence
    that cannot survive being replaced. Weakening the assertion back to
    the substring is now a failing test rather than a silent hole.
    """
    from mcp.server.mcpserver.exceptions import ResourceError

    try:
        from mcp.server.mcpserver.exceptions import UnexpectedResourceError
    except ImportError:  # pragma: no cover - depends on the resolved mcp
        UnexpectedResourceError = ()  # type: ignore[assignment,misc]

    with tempfile.TemporaryDirectory() as work:
        # Adversarial on purpose: this name lands in the URI, and so in
        # the 2.0.0 crash wrapper's message. See the docstring.
        base = Path(work) / "audit_repository"
        base.mkdir()
        root = _repo(base)  # authorized below, deliberately unconfigured
        server = create_server(roots=(base.resolve(),))

        with pytest.raises(ResourceError) as refusal:
            _resource_text(server, root)

    message = str(refusal.value)
    assert not isinstance(refusal.value, UnexpectedResourceError), (
        "the resource refusal reached the reader as the SDK's crash wrapper"
    )
    # The discriminator on 2.0.0. A crash replaces the refusal's text
    # wholesale, and this fragment cannot appear in an interpolated URI.
    assert "has not been set up" in message, (
        "the refusal's own text did not survive: the reader got the SDK's "
        f"crash wrapper instead of D30's sentence: {message}"
    )
    # D30's actual requirement, kept separately: the refusal names the
    # door that *can* ask. On its own this is not a crash/refusal
    # discriminator — see the docstring.
    assert "audit_repository" in message, (
        "the resource refusal reached the reader without naming the door "
        f"that can ask: {message}"
    )
    assert isinstance(refusal.value.__cause__, SetupRequired), (
        "the declared refusal lost the type it was translated from"
    )
