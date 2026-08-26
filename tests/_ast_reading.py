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
CONFIG = PACKAGE / "config.py"
RANGES = PACKAGE / "_ranges.py"


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


def dispatch_branches_for(suffix: str) -> list[ast.If]:
    """``if`` branches inside ``declaration_ranges`` that test ``suffix``."""
    module = tree(DECLARATIONS)
    known = assignments(module)
    dispatcher = next(
        node for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "declaration_ranges"
    )
    return [
        node for node in ast.walk(dispatcher)
        if isinstance(node, ast.If) and suffix in strings(node.test, known)
    ]


def branch_calls(branch: ast.If) -> tuple[set[str], set[str]]:
    """``(called names, all referenced names)`` inside one branch body."""
    body = ast.Module(body=branch.body, type_ignores=[])
    calls = {
        node.func.id for node in ast.walk(body)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    names = {node.id for node in ast.walk(body) if isinstance(node, ast.Name)}
    return calls, names


def java_range_functions() -> set[str]:
    return {
        node.name for node in tree(RANGES).body
        if isinstance(node, ast.FunctionDef)
        and "java" in node.name.lower()
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


def _bound_as(alias: ast.alias) -> str:
    """The local name an `import x.y.z` statement binds."""
    return alias.asname or alias.name.split(".")[-1]


def reachable_names(
    module: ast.Module, package: str, members: set[str]
) -> tuple[set[str], set[str]]:
    """Every name `package` is reachable under here, and its imported members.

    Two sweeps needed the same thing and each grew its own copy, which
    put both over this project's function-complexity gate. They were
    also both written twice: the first versions matched a literal
    attribute — `subprocess.run`, `ElementTree.fromstring` — so
    `import subprocess as sp` and `from subprocess import run` walked
    straight past. Resolving the names is the whole difference between
    linting a class and linting a spelling.

    Returns `(aliases, direct)`: names the module itself is bound to,
    and names from `members` imported out of it directly.
    """
    aliases: set[str] = set()
    direct: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            aliases |= {
                _bound_as(alias) for alias in node.names
                if _is_package(alias.name, package)
            }
        elif isinstance(node, ast.ImportFrom) and _is_package(node.module or "", package):
            for alias in node.names:
                target = direct if alias.name in members else aliases
                target.add(alias.asname or alias.name)
    return aliases, direct


def calls_reaching(
    module: ast.Module, aliases: set[str], direct: set[str], members: set[str]
) -> list[ast.Call]:
    """Calls of `members` through `aliases`, or of `direct` names outright."""
    found: list[ast.Call] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in members:
            value = getattr(func, "value", None)
            if isinstance(value, ast.Name) and value.id in aliases:
                found.append(node)
        elif isinstance(func, ast.Name) and func.id in direct:
            found.append(node)
    return found
