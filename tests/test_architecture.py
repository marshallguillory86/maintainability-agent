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

# `_runner` sits in foundations beside `git_tools` for the same reason:
# both spawn processes and depend on nothing internal. Rule 7 names
# those two plus `_backfill` (assembly; git for history backfill).
# Keeping the foundation spawners in one layer is what makes the
# analyzer half of that rule checkable.
FOUNDATIONS = {"_metrics_types", "_masking", "_hotspots", "_scan_history", "config",
               "git_tools", "instructions",
               # `_runner` sits beside `git_tools`: both spawn processes and
               # import nothing internal. `_catalog` is analyzer selection
               # data -- a leaf that reads the shipped catalog and nothing
               # else.
               "_runner", "_catalog"}
PARSING = {"source", "declarations", "_cognitive", "_ranges", "_tokens"}
# `_adapters` is a scanner: it produces findings and measurements from a
# tree, exactly as the built-in detectors do, and like them it may not
# import scoring. The difference is only that an external process does
# the looking (ADR 006).
SCANNERS = {"metrics", "_discovery", "_practice", "duplication", "deadcode", "idioms",
            "similarity",
            "history", "_adapters",
            # `_generic` is the same layer: it turns tool output into
            # findings, differing only in that its parsers are shared
            # across tools rather than written per tool.
            "_generic",
            # Adapters split by emitter kind when `_adapters` breached this
            # project's own 500-line limit: `_metric_adapters` for tools
            # reporting every unit, `_verdict_adapters` for tools reporting
            # only threshold breaches, `_tool_adapters` for the registry
            # naming them. The base module keeps only shared plumbing.
            "_metric_adapters", "_verdict_adapters", "_tool_adapters"}
# `_bands` joins the rubric-data leaves: it is the band matrix, a table
# of judgments like `_formula`, and imports nothing internal.
SCORING = {"scoring", "_aspects", "_pressures", "_formula", "_calibration", "_derive",
           "_pillars", "_trends", "_recurrence",
           "_verification", "_bands",
           # `_corroborate` reduces several tools' readings of one concept to
           # a single value plus its spread. That is scoring input
           # preparation, and like the rest of this layer it reads
           # measurements and never scanners.
           "_corroborate"}
# `_analysis` orchestrates: it calls the catalog, the runner and the
# adapters and hands `report` a coverage document. That makes it assembly,
# not a scanner — it composes rather than measures.
ASSEMBLY = {"report", "_analysis", "_documents", "_built_ins", "_work_order",
            "_backfill"}
PRESENTATION = {"renderers", "prompts", "sarif", "baseline", "_evidence_view",
                "_scan_view", "_history_view", "_identity"}
ENTRY = {"cli", "__main__", "mcp_server"}
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


REMOVED_PUBLIC_KEYS = ("overall", "overall_range", "grade", "grade_blockers")

# Reading a removed key out of a report dictionary. Deliberately narrow:
# it matches subscript and .get access with a string literal, so internal
# variables named `overall`, `low`, `high` or `grade` are untouched — the
# scorer still uses them and the brief permits it. Prose, changelog
# history and ADR explanations are not code and are never scanned.
_REMOVED_READ = re.compile(
    r"""\[\s*["'](?:overall|overall_range|grade|grade_blockers)["']\s*\]"""
    r"""|\.get\(\s*["'](?:overall|overall_range|grade|grade_blockers)["']"""
)


def test_production_code_never_reads_a_removed_public_key() -> None:
    """The version-2 contract, enforced against reintroduction.

    ADR 001 stage 8 removed `overall`, `overall_range`, `grade` and
    `grade_blockers` from the public score. A consumer that starts
    reading one again would either KeyError in production or, worse,
    silently fall back — which is the class of defect the whole evidence
    architecture exists to remove.

    Scans `src/` and `tools/` only. Tests legitimately reference the old
    names when comparing against captured anchors from before the
    migration.
    """
    offenders: list[str] = []
    for path in [*(ROOT / "src").rglob("*.py"), *(ROOT / "tools").rglob("*.py")]:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _REMOVED_READ.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()[:90]}")

    assert not offenders, (
        "production code reads a score key removed in ADR 001 stage 8:\n" + "\n".join(offenders)
    )


def test_production_code_never_emits_a_removed_public_key() -> None:
    """The producer side of the same rule."""
    scoring = (ROOT / "src" / "maintainability_audit" / "scoring.py").read_text(encoding="utf-8")
    emitted = re.findall(r'^\s{8}"([a-z_]+)":', scoring, re.M)

    assert not set(emitted) & set(REMOVED_PUBLIC_KEYS), (
        f"the score document emits removed keys: {sorted(set(emitted) & set(REMOVED_PUBLIC_KEYS))}"
    )


# The as-is document once listed shipped modules as unimplemented while
# the layering test still passed: a name appearing *anywhere* satisfied
# it, including a Known-debt sentence that said the file did not exist.
# The proposal section at the end may name future work; everything
# above it may not deny a file that is in the tree.
_PROPOSAL_HEADING = "## Proposed extension boundaries"
_MODULE_DENIAL = re.compile(
    r"(do not exist|does not exist|did not exist|"
    r"unimplemented|not shipped|never created|"
    r"were never created|was never created|"
    r"does not ship|do not ship)",
    re.I,
)
_BACKTICK_NAME = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
_KNOWN_DEBT_SECTION = re.compile(r"^## Known debt\n(.*?)(?=^## )", re.S | re.M)
# Phrases that were true of an earlier tree and are now false. Mentioning
# them as *resolved* ("no longer", strikethrough) is fine; asserting them
# as current debt is the class of lie this file existed to stop.
_RESOLVED_AS_CURRENT = (
    (re.compile(r"today nothing records", re.I),
     "scans append through _scan_history"),
    (re.compile(r"finding identity is line-coupled", re.I),
     "identity is function:{path}:{name}#{ordinal} in _identity"),
    (re.compile(r"function:\{path\}:\{name\}:\{start_line\}"),
     "line-coupled identity format is gone"),
    (re.compile(r"ten modules do not exist", re.I),
     "the named modules mostly shipped under other names"),
    (re.compile(r"ADR 00[5-9].{0,20}unimplemented", re.I),
     "005-009 landed in code; remaining gaps are listed as specific debt"),
)


def _asis_architecture(text: str) -> str:
    idx = text.find(_PROPOSAL_HEADING)
    return text if idx < 0 else text[:idx]


def test_architecture_doc_does_not_deny_modules_that_exist() -> None:
    """A claim that a module does not exist must be true of the tree.

    Inverse of ``test_the_documented_layering_matches_the_document``.
    Only names in the clause that carries the denial are checked, so a
    Known-debt sentence can say ``_analyzers`` was never created and
    then name the files that absorbed the role.
    """
    text = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    asis = _asis_architecture(text)
    offenders: list[str] = []
    for match in _MODULE_DENIAL.finditer(asis):
        window = asis[max(0, match.start() - 160):match.end()]
        for name in _BACKTICK_NAME.findall(window):
            py = PACKAGE / f"{name}.py"
            pkg = PACKAGE / name
            if py.exists() or pkg.is_dir():
                located = py if py.exists() else pkg
                offenders.append(
                    f"{name} is denied but {located.relative_to(ROOT)} exists:\n"
                    f"  {window.strip()[:220]}"
                )

    assert not offenders, (
        "docs/architecture.md denies modules that exist:\n" + "\n".join(offenders)
    )


def test_architecture_known_debt_does_not_reassert_resolved_defects() -> None:
    """Live Known-debt bullets may not resurrect defects that already shipped."""
    text = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    match = _KNOWN_DEBT_SECTION.search(text)
    assert match, "docs/architecture.md is missing a Known debt section"
    live = "\n".join(
        line
        for line in match.group(1).splitlines()
        if not line.lstrip().startswith(("~~", "- ~~"))
        and "no longer" not in line.lower()
    )
    offenders = [
        f"{reason}: /{pattern.pattern}/ matched live Known debt"
        for pattern, reason in _RESOLVED_AS_CURRENT
        if pattern.search(live)
    ]

    assert not offenders, (
        "docs/architecture.md Known debt reasserts resolved defects:\n"
        + "\n".join(offenders)
    )


ALLOWED_SPAWN = {"_runner", "git_tools", "_backfill"}


def test_only_documented_modules_spawn_processes() -> None:
    """Rule 7: analyzers go through `_runner`; git is `git_tools` and `_backfill`."""
    offenders = [
        path.name
        for path in sorted(PACKAGE.glob("*.py"))
        if path.stem not in ALLOWED_SPAWN
        and re.search(r"\bsubprocess\b", path.read_text(encoding="utf-8"))
    ]

    assert not offenders, (
        "modules outside rule 7 import subprocess: "
        f"{offenders}; add them to the architecture rule or route through "
        f"{sorted(ALLOWED_SPAWN)}"
    )
