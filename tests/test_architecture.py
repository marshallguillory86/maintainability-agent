"""The layering in docs/architecture.md, enforced against the real imports.

An architecture document nobody checks becomes another thing that
drifts, and this repository has enough experience of documents drifting
away from the code they describe. Every rule in "The rules, and why each
exists" is asserted here by reading the actual import graph, so the
document cannot quietly stop being true.

Each rule was bought by a specific failure; the docstrings say which.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"

FOUNDATIONS = {"_metrics_types", "_masking", "_hotspots", "config", "git_tools", "instructions"}
PARSING = {"source", "declarations", "_cognitive", "_ranges", "_tokens"}
SCANNERS = {"metrics", "duplication", "deadcode", "idioms", "similarity", "history"}
SCORING = {"scoring", "_aspects", "_pressures", "_formula", "_calibration", "_derive"}
ASSEMBLY = {"report"}
PRESENTATION = {"renderers", "prompts", "sarif", "baseline"}
ENTRY = {"cli", "__main__"}
BOUNDARY = {"evidence"}

LAYERS = {
    "foundations": FOUNDATIONS,
    "parsing": PARSING,
    "scanners": SCANNERS,
    "scoring": SCORING,
    "assembly": ASSEMBLY,
    "presentation": PRESENTATION,
    "entry": ENTRY,
    "boundary": BOUNDARY,
}


def internal_imports() -> dict[str, set[str]]:
    """Every intra-package import, module -> modules it imports."""
    graph: dict[str, set[str]] = {}
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        deps = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module
        }
        graph[path.stem] = deps
    return graph


def test_every_module_is_assigned_to_exactly_one_layer() -> None:
    """A module nobody placed is a module no rule constrains.

    Without this, adding a file would silently exempt it from every
    check below, and the enforcement would erode by addition rather
    than by edit.
    """
    modules = set(internal_imports()) - {"__init__"}
    placed = set().union(*LAYERS.values())

    assert modules == placed, (
        f"unassigned modules: {sorted(modules - placed)}; "
        f"assigned but missing from the package: {sorted(placed - modules)} "
        "(update docs/architecture.md and the layer sets together)"
    )


def test_the_import_graph_is_acyclic() -> None:
    """A cycle existed once and forced an import inside a function body.

    ``_derive`` needed the scorer and the scorer needed the calibration.
    Splitting scoring into _pressures/_aspects/scoring removed it.
    Cycles are how layering rots without anyone deciding to rot it.
    """
    graph = internal_imports()
    visiting: set[str] = set()
    done: set[str] = set()
    cycles: list[str] = []

    def visit(module: str, trail: list[str]) -> None:
        if module in done or module not in graph:
            return
        if module in visiting:
            cycles.append(" -> ".join([*trail, module]))
            return
        visiting.add(module)
        for dep in sorted(graph[module]):
            visit(dep, [*trail, module])
        visiting.discard(module)
        done.add(module)

    for module in sorted(graph):
        visit(module, [])

    assert not cycles, "import cycles:\n" + "\n".join(cycles)


def test_scoring_never_imports_scanners_or_assembly() -> None:
    """The rubric must not reach back into how a finding was produced.

    If it could, a repository-specific special case would eventually be
    written, and the promise that one uniform rubric applies everywhere
    (product-intent P2) would fail without anything failing loudly.
    """
    graph = internal_imports()
    forbidden = SCANNERS | ASSEMBLY | PRESENTATION | ENTRY
    violations = {
        module: sorted(graph[module] & forbidden) for module in SCORING if graph[module] & forbidden
    }

    assert not violations, f"scoring reached upward: {violations}"


def test_the_rubric_data_modules_are_leaves() -> None:
    """_formula and _calibration are judgment, expressed as data.

    A leaf cannot acquire a dependency on scanning, so the weights and
    bands cannot come to depend on what they are scoring.
    """
    graph = internal_imports()

    assert graph["_formula"] == set(), f"_formula grew imports: {sorted(graph['_formula'])}"
    assert graph["_calibration"] == set(), f"_calibration grew imports: {sorted(graph['_calibration'])}"


def test_the_evidence_boundary_is_a_leaf() -> None:
    """ADR 001 §3: normalization is a boundary, not a participant.

    Everything it needs arrives as an argument. The moment it imports a
    scanner or the scorer it stops being the one place raw-dictionary
    handling lives.
    """
    graph = internal_imports()

    assert graph["evidence"] == set(), f"the evidence boundary grew imports: {sorted(graph['evidence'])}"


def test_presentation_never_computes_a_score() -> None:
    """Renderers consume the report; they do not reach into the scorer.

    Two code paths to a number is how an overall came to contradict the
    categories printed beside it. Presentation may import formatting
    helpers and config, and nothing from the scoring layer.
    """
    graph = internal_imports()
    scoring_internals = SCORING | {"evidence"}
    violations = {
        module: sorted(graph[module] & scoring_internals)
        for module in PRESENTATION
        if graph[module] & scoring_internals
    }

    assert not violations, f"presentation imported scoring: {violations}"


def test_the_calibration_derivation_uses_the_shipped_scorer() -> None:
    """"Same pipeline" is only true when there is one pipeline.

    Three audits found the derivation differing from the live path by a
    single step. It must import the shipped rollup rather than restate
    it — the positive form of the rule, since "does not restate" cannot
    be read off the import graph.
    """
    graph = internal_imports()

    assert {"_formula", "_aspects"} <= graph["_derive"], (
        "_derive must call the shipped rollup and aspect scorers, not its own copy"
    )


def test_the_documented_layering_matches_the_document() -> None:
    """The layer table in docs/architecture.md names these modules.

    Cheap guard against the doc and the test drifting apart: every
    module named in a layer set must appear somewhere in the document.
    """
    text = (Path(__file__).resolve().parents[1] / "docs" / "architecture.md").read_text(encoding="utf-8")
    missing = sorted(module for module in set().union(*LAYERS.values()) if module not in text)

    assert not missing, f"modules absent from docs/architecture.md: {missing}"


def _named_tests(text: str) -> set[str]:
    return set(re.findall(r"`(test_[a-z0-9_]+(?:\.py)?)`", text))


def test_every_test_named_in_the_architecture_doc_exists() -> None:
    """A cited test that does not exist is a claim with nothing behind it.

    An audit found the invariant table asserting enforcement on the
    strength of test *names*, one of them mapped to a test that checked
    something else entirely. Names in that table are now verified
    against the suite, so a renamed or deleted test fails the build
    instead of quietly downgrading a documented invariant to a promise.
    """
    doc = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    suite = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "tests").glob("test_*.py")
    )
    existing_files = {path.name for path in (ROOT / "tests").glob("test_*.py")}

    missing = [
        name
        for name in _named_tests(doc)
        if not (name in existing_files or f"def {name}(" in suite)
    ]

    assert not missing, f"docs/architecture.md cites tests that do not exist: {sorted(missing)}"


def test_the_summarized_stage_range_appears_only_in_the_register() -> None:
    """The *summarized range* lives in the register and nowhere else.

    Named for what it checks. An audit correctly pointed out that the
    previous name claimed single ownership of implementation status
    while the regex only matched numeric ranges like "stages 1-4" —
    individual references such as "blocks stage 5" are legitimate and
    still appear where they are relevant.

    It was copied into five documents and a module docstring, and three
    of the copies were already contradicting each other one commit after
    they were written — README said stages 1–3, the report contract said
    4–9 untouched, and `evidence.py` said scoring did not consume the
    boundary it had just been migrated onto. A status duplicated is a
    status that goes stale, so everything else links to the register.
    """
    register = ROOT / "docs" / "decisions.md"
    pattern = re.compile(r"stages? \d\s*[–-]\s*\d", re.I)
    offenders = []
    for path in [*ROOT.glob("*.md"), *ROOT.glob("docs/*.md"), *ROOT.glob("src/**/*.py")]:
        if path == register or path.name == "self-audit.md":
            continue
        if pattern.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(ROOT)))

    assert not offenders, (
        "a summarized ADR stage range appears outside docs/decisions.md: "
        f"{sorted(offenders)}; link to the register instead"
    )
