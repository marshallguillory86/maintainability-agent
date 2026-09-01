"""Reading declarations out of this package's source, for structural tests.

Two Java guards need the same three functions: parse a module, collect
its top-level assignments, and resolve the string constants reachable
from an expression through those assignments. Held in one place because
the second copy tripped this project's own duplicate-block gate, which
is exactly the finding it should produce.

Structural rather than behavioural on purpose. Whether `.java` is in
`DECLARATION_SUFFIXES` is a question about the source, and asking the
source is what keeps the answer true when the runtime value is assembled
from several pieces.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"
DECLARATIONS = PACKAGE / "declarations.py"
CONFIG = PACKAGE / "_config_defaults.py"   # DEFAULT_CONFIG moved here in 1.1.0
RANGES = sorted(PACKAGE.glob("_ranges*.py"))


def tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def assignments(module: ast.Module) -> dict[str, ast.expr]:
    """Every top-level ``NAME = ...`` in the module, by name."""
    found: dict[str, ast.expr] = {}
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            found[node.target.id] = node.value
    return found


def strings(node: ast.AST, known: dict[str, ast.expr]) -> set[str]:
    """String constants reachable from ``node``, following named references.

    `DECLARATION_SUFFIXES = {".py", ".java"} | BRACE_SUFFIXES` only
    yields its full membership if the referenced name is expanded too.
    """
    values = {
        item.value
        for item in ast.walk(node)
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }
    for name in {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}:
        if name in known:
            values |= strings(known[name], known)
    return values


def declaration_suffixes() -> set[str]:
    module = tree(DECLARATIONS)
    return strings(assignments(module)["DECLARATION_SUFFIXES"], assignments(module))


def default_include_extensions() -> set[str]:
    """``DEFAULT_CONFIG["paths"]["include_extensions"]``, read from source."""
    default_config = assignments(tree(CONFIG))["DEFAULT_CONFIG"]
    for node in ast.walk(default_config):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values, strict=True):
            if isinstance(key, ast.Constant) and key.value == "include_extensions":
                return strings(value, {})
    raise AssertionError("DEFAULT_CONFIG paths.include_extensions was not found")


def scanner_registry() -> dict[str, str]:
    """``declarations.SCANNERS`` read from source: suffix -> scanner name.

    Replaces the reader that looked for ``if`` branches inside
    ``declaration_ranges``. 1.1.0 made the dispatch a table, because a
    branch per language does not survive four more languages — so the
    guards ask what the table says rather than what the function's
    control flow looks like. The question is the same one: does this
    suffix reach a scanner written for it, or the last-resort patterns?
    """
    module = tree(DECLARATIONS)
    known = assignments(module)
    registry = known.get("SCANNERS")
    assert registry is not None, "declarations.SCANNERS is missing"
    found: dict[str, str] = {}
    for row in registry.elts:
        suffixes, scanner = row.elts
        assert isinstance(scanner, ast.Name), "a scanner row must name a function"
        for suffix in strings(suffixes, known):
            found[suffix] = scanner.id
    return found


def range_functions_for(language: str) -> set[str]:
    """Scanner functions named for ``language`` anywhere in the family."""
    return {
        node.name for path in RANGES for node in tree(path).body
        if isinstance(node, ast.FunctionDef)
        and language in node.name.lower()
        and "range" in node.name.lower()
    }


PRODUCER = ROOT / "tools" / "build_catalog.py"


def producer_literal(name: str):
    """A top-level literal from tools/build_catalog.py, frozenset-aware.

    Both JVM adapter suites read the producer's promise maps this way;
    the second verbatim copy of this reader tripped the duplicate-block
    gate, which is the finding it should produce.
    """
    value = assignments(tree(PRODUCER)).get(name)
    if value is None:
        raise AssertionError(f"{name} is missing from tools/build_catalog.py")
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "frozenset"
        and len(value.args) == 1
    ):
        return frozenset(ast.literal_eval(value.args[0]))
    return ast.literal_eval(value)


def producer_module():
    """The real tools/build_catalog.py, imported: is_eligible has one source."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_catalog", PRODUCER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def recomputed_counts(tools):
    """The catalog summary as a function of its rows, never hand arithmetic.

    The third verbatim copy of this reader tripped the duplicate-block
    gate, which is the finding it should produce.
    """
    from collections import Counter

    is_eligible = producer_module().is_eligible
    eligible = [tool for tool in tools if is_eligible(tool)]
    return {
        "in_source": len(tools),
        "eligible": len(eligible),
        "by_tier": dict(Counter(tool["tier"] for tool in eligible)),
        "by_license_status": dict(Counter(tool["license_status"] for tool in tools)),
        "by_license_class": dict(Counter(tool["license_class"] for tool in tools)),
        "by_measure": dict(Counter(
            measure for tool in tools for measure in tool["measures"]
        )),
        "eligible_by_license_class": dict(Counter(
            tool["license_class"] for tool in eligible
        )),
        "adapters_implemented": sum(
            1 for tool in tools if tool["adapter"] == "implemented"
        ),
    }


def _is_package(name: str, package: str) -> bool:
    """Whether an imported name is `package` itself or something inside it."""
    return name == package or name.startswith(f"{package}.")


def _spelled_as(alias: ast.alias) -> str:
    """How an `import` statement's target can be spelled at a call site.

    Not the name it binds, which is what the second version returned.
    `import xml.etree.ElementTree` binds `xml` and reaches the module
    only through the full dotted path, so neither the bound name nor
    the trailing component is what a call site will read.
    """
    return alias.asname or alias.name


def _dotted(node: ast.expr) -> str | None:
    """The dotted spelling of a Name/Attribute chain, or None."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def reachable_names(
    module: ast.Module, package: str, members: set[str]
) -> tuple[set[str], set[str]]:
    """Every spelling `package` is reachable under here, and its members.

    Two sweeps needed the same thing and each grew its own copy, which
    put both over this project's function-complexity gate. They were
    also written three times. The first matched a literal attribute --
    `subprocess.run`, `ElementTree.fromstring` -- so `import subprocess
    as sp` and `from subprocess import run` walked straight past. The
    second resolved bound *names*, and an audit walked through that too:
    `import xml.etree.ElementTree` binds `xml`, and the call is written
    `xml.etree.ElementTree.fromstring(...)`, whose base is an attribute
    chain rather than a plain name. So this resolves dotted *spellings*,
    and the matching below is by prefix.

    Returns `(aliases, direct)`: dotted spellings the module is reachable
    under, and names from `members` imported out of it directly.
    """
    aliases: set[str] = set()
    direct: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            aliases |= {
                _spelled_as(alias) for alias in node.names
                if _is_package(alias.name, package)
            }
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            for alias in node.names:
                # Members first: `from subprocess import run` names a
                # member, and `subprocess.run` also reads as "inside the
                # package" to the test below -- which is how the first
                # draft of this reclassified every direct import as a
                # module alias, caught by the spelling falsifier.
                if _is_package(base, package) and alias.name in members:
                    direct.add(alias.asname or alias.name)
                # `from xml import etree` names the package one level
                # down, so the module is what `base.name` spells.
                elif _is_package(f"{base}.{alias.name}", package) or _is_package(
                    base, package
                ):
                    aliases.add(alias.asname or alias.name)
    return aliases, direct


def calls_reaching(
    module: ast.Module, aliases: set[str], direct: set[str], members: set[str]
) -> list[ast.Call]:
    """Calls of `members` under `aliases`, or of `direct` names outright.

    Prefix matching, not equality: an alias of `etree` still covers
    `etree.ElementTree.fromstring`, one dotted step further down.
    """
    found: list[ast.Call] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        spelled = _dotted(node.func)
        if spelled is None:
            continue
        prefix, _, last = spelled.rpartition(".")
        if not prefix:
            if spelled in direct:
                found.append(node)
        elif last in members and any(
            prefix == alias or prefix.startswith(f"{alias}.") for alias in aliases
        ):
            found.append(node)
    return found
