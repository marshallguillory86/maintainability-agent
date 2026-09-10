"""TDD-shaped structure: path pairing and constructs.

Not chronology and not quality. A production file is paired when a
test-shaped file shares its subject stem. Constructs are counts of
known test APIs in those files. Effectiveness stays unscored unless
the operator opted into suite execution.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from ._metrics_types import FileMetric, FunctionMetric, is_test_path
from .source import SourceIndex, index_or_new

# HTML/CSS/Markdown are not "a page with no test" in the TS/Python sense.
#
# Fortran joins in 1.4.0 *with* the conventions below. Claiming a
# language here without teaching `subject_stem` and `is_test_path` how
# its tests are named reports every repository in it as having untested
# production code — a confident finding, wrong on every project, of
# exactly the kind this tool exists to prevent. `.pf` is excluded: a
# pFUnit file is always a test, never a thing needing one.
PAIRABLE = frozenset({".py", ".java", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
                      ".f90", ".f95", ".f03", ".f08",
                      ".F90", ".F95", ".F03", ".F08"})

_STEM_SUFFIXES = (".test", ".spec", "_test")
# Fortran module files are conventionally named `foo_mod.f90`, and the
# pFUnit convention pairs that with `testFoo_mod.F90`. Dropping `_mod`
# from both sides is what makes the two stems meet.
_MODULE_STEM_SUFFIXES = ("_mod", "_module")
_CONSTRUCTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pytest", re.compile(r"\bpytest\b|def test_")),
    ("unittest", re.compile(r"\bunittest\b")),
    ("describe_it", re.compile(r"\b(?:describe|it|test)\s*\(")),
    ("parametrize", re.compile(r"pytest\.mark\.parametrize")),
    ("given_when_then", re.compile(r"(?:#|//)\s*(?:given|when|then)\b", re.I)),
)


def subject_stem(rel: str) -> str:
    """The production name a test file claims to cover, or the file's own stem."""
    stem = Path(rel.replace("\\", "/")).name.rsplit(".", 1)[0].lower()
    for suffix in _STEM_SUFFIXES:
        if stem.endswith(suffix):
            return _without_module_suffix(stem[: -len(suffix)])
    if stem.startswith("test_"):
        return _without_module_suffix(stem[5:])
    if stem.startswith("test."):
        return _without_module_suffix(stem[5:])
    # pFUnit's camelCase convention: `testFooBar_mod.F90` covers
    # `fooBar_mod.F90`. Lowercased above, so the boundary the capital
    # marked is gone and the prefix is all that is left to strip.
    if stem.startswith("test") and len(stem) > 4:
        stripped = _without_module_suffix(stem[4:])
        if stripped:
            return stripped
    return _without_module_suffix(stem)


def _without_module_suffix(stem: str) -> str:
    """`gravity_mod` and `gravity` are the same subject."""
    for suffix in _MODULE_STEM_SUFFIXES:
        if stem.endswith(suffix) and len(stem) > len(suffix):
            return stem[: -len(suffix)]
    return stem


# What a test file references, per language. Stem-based rather than a
# full module resolver, deliberately: the question is "does a test name
# this unit", and a resolver would need each language's search path,
# packaging and aliasing to answer a question that a name already
# answers. Under-matching is the safe direction — it reports a paired
# file as unpaired, which is the state this rule already had.
_IMPORT_REFERENCES: tuple[re.Pattern[str], ...] = (
    # Python: `from pkg.mod import x`, `import pkg.mod`
    re.compile(r"^\s*from\s+([\w.]+)\s+import\b", re.M),
    # `(?!\s+from)` keeps JavaScript's `import y from './report'` out of
    # the Python branch: without it the *binding name* `y` is collected
    # as a subject, and a production file happening to be named `y`
    # pairs against a test that never mentions it. False pairing
    # under-reports real work, which is the direction that flatters.
    re.compile(r"^\s*import\s+(?!static\b)([\w.]+)(?!\s+from)", re.M),
    # JS/TS: `from './foo'`, `require('../foo')`, `import('./foo')`
    re.compile(r"""from\s+['"]([^'"]+)['"]"""),
    re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]"""),
    re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]"""),
    # Java: `import com.example.Thing;`
    re.compile(r"^\s*import\s+([\w.]+)\s*;", re.M),
    # Java static import names a *member* of the class it is testing:
    # `import static com.example.Helper.thing;` is evidence about
    # `Helper`, not about `thing`. The subject is the penultimate
    # segment, so it needs its own pattern rather than a shared one —
    # taking the last segment here credits a production file named for
    # the method instead of the class.
    re.compile(r"^\s*import\s+static\s+([\w.]+)\.\w+\s*;", re.M),
    # Fortran: `use gravity_mod`
    re.compile(r"^\s*use\s+([\w]+)", re.M | re.I),
)


def _python_references(text: str) -> set[str] | None:
    """Real import statements, from the parse tree. `None` if it will not parse.

    Regex over raw text cannot tell an import from a *mention* of one, and
    a test fixture holding source as a string is an ordinary thing for
    this tool's own suite to contain:

        fixture = '''
        import payment_gateway
        '''

    That paired a real `payment_gateway.py` against a test that never
    imported it — a phantom pairing, and in the flattering direction this
    module's own docstring says it must not err. Masking does not help:
    it blanks the quotes and leaves the line between them.

    The parse tree has no such ambiguity. A string is a string, and only
    `import`/`from` statements are import nodes. `None` when the file
    does not parse, so the caller falls back rather than reporting a
    Python test file as importing nothing.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.rsplit(".", 1)[-1])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module.rsplit(".", 1)[-1])
            # `from . import scoring` and `from .pkg import scoring` both
            # name the module. The first has no `module` at all, so a
            # reader that only looked there saw nothing — a real sibling
            # import going unpaired, the opposite error and just as wrong.
            for alias in node.names:
                found.add(alias.name.rsplit(".", 1)[-1])
    return {_without_module_suffix(name.lower()) for name in found if name}


def referenced_subjects(text: str) -> set[str]:
    """Every subject stem this test file names in an import.

    A test that imports `maintainability_audit._generic` is evidence
    about `_generic.py` that no filename convention can supply, and it
    is the evidence a maintainer actually follows when they ask "where
    are the tests for this".

    Pairing was filename-only before this, so a suite organised by
    behaviour rather than by module read as untested production code —
    58 such findings on this repository, 52 of them imported by a test
    (D149, which carries the measurement and the reasoning).

    Stems, not resolved modules: `../scoring`, `pkg.scoring` and
    `./scoring.js` all name `scoring`. Two same-named files in different
    packages both pair, which over-credits — the previous rule had the
    identical collision through stems, so it is not new, and it errs
    toward reporting less work rather than inventing it.
    """
    parsed = _python_references(text or "")
    if parsed is not None:
        return parsed
    # Not Python, or not parseable Python. The regex path stays for the
    # other four languages; it cannot tell an import from a mention, so
    # it is the fallback rather than the rule.
    found: set[str] = set()
    for pattern in _IMPORT_REFERENCES:
        for raw in pattern.findall(text or ""):
            stem = _reference_stem(str(raw))
            if stem:
                found.add(_without_module_suffix(stem))
    return found


def _reference_stem(reference: str) -> str:
    """The subject a single import reference names.

    A dot means two different things and the order here is what keeps
    them apart. In `pkg.scoring` it separates *module* segments and the
    subject is the last one; in `./scoring.js` it introduces a *file
    extension* and the subject is what precedes it. Stripping the
    extension first, then taking the last dotted segment, reads both —
    the other order turns `./scoring.js` into `js`, which pairs every
    JavaScript file in the tree against any test that imports one.
    """
    segment = reference.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].strip()
    for extension in PAIRABLE:
        if segment.lower().endswith(extension):
            segment = segment[: -len(extension)]
            break
    return segment.rsplit(".", 1)[-1].strip().lower()


def _suffix(rel: str) -> str:
    return Path(rel.replace("\\", "/")).suffix.lower()


def _partition_files(
    file_metrics: list[FileMetric],
) -> tuple[set[str], list[str], list[FileMetric]]:
    """Test subject stems and paths, and the pairable production files."""
    test_stems: set[str] = set()
    test_paths: list[str] = []
    production: list[FileMetric] = []
    for metric in file_metrics:
        if is_test_path(metric.path):
            test_stems.add(subject_stem(metric.path))
            test_paths.append(metric.path)
        elif _suffix(metric.path) in PAIRABLE:
            production.append(metric)
    return test_stems, test_paths, production


def _read_test_files(
    root: Path, test_paths: list[str], index: SourceIndex
) -> tuple[dict[str, int], set[str]]:
    """Construct counts and every subject the tests import, in one pass.

    One read per test file. Both answers come from the same text, and
    reading the suite twice to ask two questions about it would be the
    kind of cost a scan cannot afford on a large tree.
    """
    constructs = {name: 0 for name, _pattern in _CONSTRUCTS}
    referenced: set[str] = set()
    for rel in test_paths:
        text = "\n".join(index.lines(root / rel))
        for name, pattern in _CONSTRUCTS:
            if pattern.search(text):
                constructs[name] += 1
        referenced |= referenced_subjects(text)
    return constructs, referenced


def _unpaired_fail_band(
    function_metrics: list[FunctionMetric],
    production: list[FileMetric],
    unpaired_paths: set[str],
) -> list[dict[str, Any]]:
    """Fail-band units in unpaired production: the failing declarations
    first, then any warn/fail whole file not already named by one of them."""
    fail_band: list[dict[str, Any]] = []
    seen: set[str] = set()
    for fn in function_metrics:
        if fn.status != "fail" or is_test_path(fn.path) or fn.path not in unpaired_paths:
            continue
        fail_band.append({
            "kind": "declaration", "path": fn.path, "name": fn.name,
            "line": fn.start_line, "lines": fn.lines,
        })
        seen.add(fn.path)
    for metric in production:
        if metric.status not in {"warn", "fail"} or metric.path in seen:
            continue
        if metric.path not in unpaired_paths:
            continue
        fail_band.append({
            "kind": "file", "path": metric.path, "name": Path(metric.path).name,
            "line": None, "lines": metric.lines,
        })
    return fail_band


def describe_tdd(
    root: Path,
    file_metrics: list[FileMetric],
    function_metrics: list[FunctionMetric],
    source: SourceIndex | None = None,
) -> dict[str, Any]:
    """Pairing, constructs, and fail-band production units with no pair."""
    index = index_or_new(source)
    test_stems, test_paths, production = _partition_files(file_metrics)
    constructs, referenced = _read_test_files(root, test_paths, index)
    # Two kinds of evidence that a unit is tested, and either counts: a
    # test file *named* for it, or a test file that *imports* it. The
    # first is a convention; the second is a fact (D149).
    covered = test_stems | referenced
    paired = [m for m in production if subject_stem(m.path) in covered]
    unpaired_paths = {m.path for m in production if subject_stem(m.path) not in covered}
    return {
        "production_files": len(production),
        "paired_production_files": len(paired),
        "detected": len(paired) > 0 or any(constructs.values()),
        "constructs": constructs,
        "unpaired_fail_band": _unpaired_fail_band(function_metrics, production, unpaired_paths),
    }
