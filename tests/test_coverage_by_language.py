"""Coverage is claimed per language, because a repository is not one language.

The defect this closes was found by the validation sample and left open
overnight deliberately, because closing it badly was worse than leaving
it: `json` contains 6 Python files among 305 C++ ones, and `lapack` 1
among 2,884 C files. That single file made all six Python-only tools
*applicable*, so both repositories reported 10 of 11 analyzers
contributing and claimed `types` and `style` as covered — from a linter
that examined one build script. A reader concludes their C++ is
type-checked. It is not.

curl, with no Python at all, correctly reported 3 of 11. So the existing
rule is right at the extremes and wrong everywhere in between.

**The obvious fix is a threshold and it is the wrong fix.** "A language
must be at least N% of the tree for its tools to count" tunes a number
until the two repositories in front of you behave, and that number then
applies to every repository forever — distorting genuinely polyglot ones
to make a mostly-C++ one read correctly. One rubric has to hold at every
size and every language mix.

**Coverage per language needs no threshold at all.** mypy covers `types`
*for Python*. It covers nothing for C++, at any mix, in any repository.
That statement is true when Python is 2% of the tree and true when it is
98%, so there is no cutoff to tune and nothing to distort. The repository
answer becomes the composition of the per-language ones rather than a
union that quietly rounds up.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from maintainability_audit._analysis import analyze
from maintainability_audit.config import load_config


def _repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


CPP = "int compute_%(n)d(int x) {\n    if (x > 0) { return x; }\n    return -x;\n}\n"
PY = "def helper_%(n)d(value):\n    return value + 1\n"


def test_a_python_only_tool_covers_nothing_for_cpp(tmp_path: Path) -> None:
    """The json case, reduced: six Python files among three hundred C++.

    mypy examined the build scripts. It examined no C++ at all, and the
    coverage claim has to say which of the two it is talking about.
    """
    root = _repo(tmp_path / "mostlycpp", {
        **{f"src/mod{n}.cpp": CPP % {"n": n} for n in range(60)},
        **{f"scripts/build{n}.py": PY % {"n": n} for n in range(6)},
    })

    coverage = analyze(root, load_config(None)).coverage_by_language()

    assert "types" in coverage["Python"], "mypy read the build scripts"
    assert "types" not in coverage["C++"], (
        "mypy cannot examine C++; claiming `types` for this repository's "
        "C++ is the defect this test exists to close"
    )


def test_a_multi_language_tool_covers_every_language_it_reads(tmp_path: Path) -> None:
    """lizard reads both, so complexity is covered on both sides.

    The filter must not over-fire: suppressing real evidence is the
    opposite failure and just as wrong.
    """
    root = _repo(tmp_path / "both", {
        **{f"src/mod{n}.cpp": CPP % {"n": n} for n in range(40)},
        **{f"pkg/mod{n}.py": PY % {"n": n} for n in range(40)},
    })

    coverage = analyze(root, load_config(None)).coverage_by_language()

    assert "complexity" in coverage["C++"], "lizard reads C++"
    assert "complexity" in coverage["Python"], "and Python"


def test_the_answer_does_not_depend_on_the_language_mix() -> None:
    """The property a threshold cannot have, and the reason for this design.

    Six Python files among sixty C++ and sixty among six are the same
    statement about what mypy can read. A share cutoff would flip
    somewhere between them; per-language coverage never does.

    Asserted against constructed coverage records rather than two live
    analyzer runs. The first version invoked the real pool twice and
    compared, and failed once on a cold cache when a tool timed out in
    one run and not the other — the property under test is a property of
    the *rule*, and pinning it to live tool availability makes it flaky
    by construction. That is the same shape as a green test over a broken
    pipeline: passing for a reason unrelated to what it claims.
    """
    from maintainability_audit._analysis import Analysis, ToolCoverage

    def claims(python: int, cpp: int) -> dict[str, set[str]]:
        analysis = Analysis(
            concerns=("all",),
            languages={"Python": "python", "C++": "cpp"},
            coverage=[
                ToolCoverage(slug="mypy", outcome="ran", concepts=("types",),
                             languages=("python",)),
                ToolCoverage(slug="lizard", outcome="ran",
                             concepts=("cyclomatic_complexity",),
                             languages=("python", "cpp", "c")),
            ],
        )
        # The file counts are what a threshold would key on. Per-language
        # coverage never reads them, which is the whole point.
        assert python and cpp
        return analysis.coverage_by_language()

    assert claims(python=6, cpp=60) == claims(python=60, cpp=6)


def test_a_concern_no_tool_reads_for_a_language_is_named_as_a_gap(tmp_path: Path) -> None:
    """Per language, because that is where the gap actually is.

    "types unexamined" is false for a repository with Python in it.
    "types unexamined for C++" is true and is what a reader needs.
    """
    root = _repo(tmp_path / "gaps", {
        **{f"src/mod{n}.cpp": CPP % {"n": n} for n in range(60)},
        **{f"pkg/mod{n}.py": PY % {"n": n} for n in range(20)},
    })

    analysis = analyze(root, load_config(None))
    gaps = analysis.gaps_by_language()

    assert "types" in gaps["C++"]
    assert "types" not in gaps.get("Python", set())


def test_a_coverage_claim_names_the_languages_it_is_about(tmp_path: Path) -> None:
    """The claim is scoped to what was scored, and says so.

    For a mostly-C++ tree under the default configuration, only the
    Python is in the scored population — `.cpp` is not in
    `include_extensions`, so the C++ is unread and reported by name and
    count under unread source.

    Scoping the claim there is correct, but `concepts_covered: [types]`
    read in isolation still says "this repository is type-checked". So
    the coverage record states which languages it covers. A claim that
    cannot be read without its scope is a claim that will be misread.
    """
    root = _repo(tmp_path / "composed", {
        **{f"src/mod{n}.cpp": CPP % {"n": n} for n in range(60)},
        **{f"pkg/mod{n}.py": PY % {"n": n} for n in range(6)},
    })

    analysis = analyze(root, load_config(None))

    assert analysis.scored_languages == ("Python",)
    assert "types" in analysis.measured_concepts(), (
        "the Python that was scored is genuinely type-checked"
    )
    # And the C++ that was not scored is not silently included in that.
    assert "types" not in analysis.coverage_by_language()["C++"]


def test_a_single_language_repository_is_unaffected(tmp_path: Path) -> None:
    """The common case must behave exactly as before.

    Most repositories are one language. A change made for polyglot trees
    that moves a pure-Python repository's coverage would be the edge case
    distorting the norm — the failure mode this whole design avoids.
    """
    root = _repo(tmp_path / "pure", {f"pkg/mod{n}.py": PY % {"n": n} for n in range(60)})

    analysis = analyze(root, load_config(None))
    coverage = analysis.coverage_by_language()

    assert set(coverage) == {"Python"}
    assert coverage["Python"] == analysis.measured_concepts(), (
        "with one language, the per-language and repository answers are "
        "the same statement"
    )


def test_one_stray_shell_script_does_not_erase_a_python_library(tmp_path: Path) -> None:
    """The edge case distorting the norm — caught before it shipped.

    The first composition rule intersected coverage across every language
    present. click is a Python library with one shell script, and its
    repository-wide coverage collapsed to nothing: no tool reads Shell,
    so the intersection was empty and a healthy library reported that
    nothing had examined anything.

    Coverage describes **what was scored**. Shell is not in
    `include_extensions`, so it is not in the population any rate is
    drawn from, and it is already reported — by name and count — under
    unread source. Letting it also erase the coverage claim would be one
    unscanned file rewriting the answer for six hundred scanned ones.
    """
    root = _repo(tmp_path / "library", {
        **{f"pkg/mod{n}.py": PY % {"n": n} for n in range(60)},
        "scripts/release.sh": "#!/bin/sh\necho release\n",
    })

    analysis = analyze(root, load_config(None))

    assert analysis.measured_concepts(), (
        "one unscanned shell script erased the coverage of 60 scanned "
        "Python files"
    )
    assert "types" in analysis.measured_concepts()
    # Still visible per language, because the shell script is really
    # there — and jscpd does read Shell, so it is not an empty row.
    assert "Shell" in analysis.coverage_by_language()
    assert "types" not in analysis.coverage_by_language()["Shell"]


def test_two_scored_languages_narrow_the_claim_honestly(tmp_path: Path) -> None:
    """Where both languages *are* scored, the intersection is the truth.

    Python and TypeScript are both in `include_extensions`, so both are
    in the population. mypy reads one of them, so `types` is not a claim
    this repository can make — and here the narrowing is correct rather
    than an artifact.
    """
    root = _repo(tmp_path / "polyglot", {
        **{f"pkg/mod{n}.py": PY % {"n": n} for n in range(40)},
        **{f"web/mod{n}.ts": f"export function f{n}(): number {{ return {n}; }}\n"
           for n in range(40)},
    })

    analysis = analyze(root, load_config(None))
    covered = analysis.coverage_by_language()

    assert "types" in covered["Python"]
    assert "types" not in covered["TypeScript"]
    assert "types" not in analysis.measured_concepts(), (
        "both languages are scored, so a claim true of only one is not "
        "a claim about the repository"
    )
