"""A language's own iteration keyword costs what a counted loop costs (D212).

C#'s primary loop is `foreach`. The C-family complexity pattern matched
`\\bfor\\b`, and that word boundary falls after `for` — so `foreach` does
not match it. Two equivalent methods scored:

    WithForeach   complexity=1  cognitive=0
    WithFor       complexity=2  cognitive=2

The first has a loop. Both metrics read it as straight-line code.

**This is the fourth time.** Fortran's `do` came first — *"six nested
loops once scored complexity 1 because the pattern did not know the
keyword"*. Then Swift's `guard` and `repeat`: *"a function built from
guards reads as having no branches at all, which is the Fortran `do`
defect in another language"*. Then PHP's `elseif` and `foreach`, added
when that language was checked construct-by-construct against a
reference implementation — *"a dispatch chain scored zero"*. Each was
found in one language and fixed in that language. The claim was never
written down, so the fifth instance was already sitting in the pattern
that PHP's note is printed next to.

So the population here is **every language this tool parses**, taken
from `DECLARATION_SUFFIXES`, and every one of them owes a pair of
equivalent loops. A language with no pair fails
`test_every_parsed_language_has_a_loop_pair` rather than being skipped,
which is the mechanism that let this survive three fixes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit.config import load_config
from maintainability_audit.declarations import detect_functions

#: One suffix per language family, and for each a pair of routines that
#: do the same thing — one with the language's idiomatic iteration, one
#: with a counted loop. Keyed by suffix so the population check can ask
#: whether every parsed suffix is represented by its family.
#:
#: `iterate` is written the way the language's own users write it. That
#: is the point: the defect is always a pattern that knows the C spelling
#: and not the local one.
LOOPS: dict[str, tuple[str, str]] = {
    ".cs": (
        "class T {\n  int Idiomatic(int[] xs) {\n    int t = 0;\n"
        "    foreach (var x in xs) { t += x; }\n    return t;\n  }\n}\n",
        "class T {\n  int Counted(int[] xs) {\n    int t = 0;\n"
        "    for (int i = 0; i < xs.Length; i++) { t += xs[i]; }\n    return t;\n  }\n}\n",
    ),
    ".php": (
        "<?php\nfunction idiomatic($xs) {\n  $t = 0;\n"
        "  foreach ($xs as $x) { $t += $x; }\n  return $t;\n}\n",
        "<?php\nfunction counted($xs) {\n  $t = 0;\n"
        "  for ($i = 0; $i < count($xs); $i++) { $t += $xs[$i]; }\n  return $t;\n}\n",
    ),
    ".java": (
        "class T {\n  int idiomatic(int[] xs) {\n    int t = 0;\n"
        "    for (int x : xs) { t += x; }\n    return t;\n  }\n}\n",
        "class T {\n  int counted(int[] xs) {\n    int t = 0;\n"
        "    for (int i = 0; i < xs.length; i++) { t += xs[i]; }\n    return t;\n  }\n}\n",
    ),
    ".py": (
        "def idiomatic(xs):\n    t = 0\n    for x in xs:\n        t += x\n    return t\n",
        "def counted(xs):\n    t = 0\n    i = 0\n    while i < len(xs):\n"
        "        t += xs[i]\n        i += 1\n    return t\n",
    ),
    ".go": (
        "func Idiomatic(xs []int) int {\n\tt := 0\n\tfor _, x := range xs {\n"
        "\t\tt += x\n\t}\n\treturn t\n}\n",
        "func Counted(xs []int) int {\n\tt := 0\n\tfor i := 0; i < len(xs); i++ {\n"
        "\t\tt += xs[i]\n\t}\n\treturn t\n}\n",
    ),
    ".rs": (
        "fn idiomatic(xs: &[i32]) -> i32 {\n    let mut t = 0;\n"
        "    for x in xs { t += x; }\n    t\n}\n",
        "fn counted(xs: &[i32]) -> i32 {\n    let mut t = 0;\n    let mut i = 0;\n"
        "    while i < xs.len() { t += xs[i]; i += 1; }\n    t\n}\n",
    ),
    ".swift": (
        "func idiomatic(_ xs: [Int]) -> Int {\n    var t = 0\n"
        "    for x in xs { t += x }\n    return t\n}\n",
        "func counted(_ xs: [Int]) -> Int {\n    var t = 0\n    var i = 0\n"
        "    while i < xs.count { t += xs[i]; i += 1 }\n    return t\n}\n",
    ),
    ".kt": (
        "fun idiomatic(xs: List<Int>): Int {\n    var t = 0\n"
        "    for (x in xs) { t += x }\n    return t\n}\n",
        "fun counted(xs: List<Int>): Int {\n    var t = 0\n    var i = 0\n"
        "    while (i < xs.size) { t += xs[i]; i += 1 }\n    return t\n}\n",
    ),
    ".sh": (
        "idiomatic() {\n  t=0\n  for x in \"$@\"; do\n    t=$((t + x))\n  done\n"
        "  echo \"$t\"\n}\n",
        "counted() {\n  t=0\n  i=0\n  while [ \"$i\" -lt \"$#\" ]; do\n"
        "    i=$((i + 1))\n  done\n  echo \"$t\"\n}\n",
    ),
    ".rb": (
        "def idiomatic(xs)\n  t = 0\n  for x in xs\n    t += x\n  end\n  t\nend\n",
        "def counted(xs)\n  t = 0\n  i = 0\n  while i < xs.length\n"
        "    t += xs[i]\n    i += 1\n  end\n  t\nend\n",
    ),
    ".js": (
        "function idiomatic(xs) {\n  let t = 0;\n  for (const x of xs) { t += x; }\n"
        "  return t;\n}\n",
        "function counted(xs) {\n  let t = 0;\n  for (let i = 0; i < xs.length; i++) "
        "{ t += xs[i]; }\n  return t;\n}\n",
    ),
    ".c": (
        "int idiomatic(int *xs, int n) {\n  int t = 0;\n  while (n-- > 0) { t += *xs++; }\n"
        "  return t;\n}\n",
        "int counted(int *xs, int n) {\n  int t = 0;\n  for (int i = 0; i < n; i++) "
        "{ t += xs[i]; }\n  return t;\n}\n",
    ),
}


def _measure(tmp_path: Path, suffix: str, source: str) -> tuple[int, int]:
    """The worst complexity and cognitive cost among a file's routines.

    The worst rather than a named routine: the pair differ in name by
    design, and what is compared is what the file costs.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / f"probe{suffix}"
    path.write_text(source, encoding="utf-8")
    found = detect_functions(
        tmp_path, path, source.splitlines(), load_config(None)["thresholds"]
    )
    assert found, f"no declaration detected in a {suffix} file"
    return (
        max(f.complexity for f in found),
        max(getattr(f, "cognitive", 0) or 0 for f in found),
    )
@pytest.mark.parametrize("suffix", sorted(LOOPS))
def test_an_idiomatic_loop_costs_what_a_counted_loop_costs(
    suffix: str, tmp_path: Path
) -> None:
    """The claim, per language, over routines that do the same work.

    Equality rather than a threshold: the two routines are the same
    computation written twice, so any gap is the pattern not knowing one
    of the spellings. C# read 1/0 against 2/2 before this change.
    """
    idiomatic, counted = LOOPS[suffix]
    idiomatic_score = _measure(tmp_path / "a", suffix, idiomatic)
    counted_score = _measure(tmp_path / "b", suffix, counted)

    assert idiomatic_score == counted_score, (
        f"{suffix}: the idiomatic loop scores {idiomatic_score} and the "
        f"counted loop {counted_score} (complexity, cognitive) — the pattern "
        "does not know one of the two spellings"
    )


@pytest.mark.parametrize("suffix", sorted(LOOPS))
def test_a_loop_is_never_free(suffix: str, tmp_path: Path) -> None:
    """Neither spelling may read as straight-line code.

    Equality alone is satisfied by a pattern that knows *neither*
    keyword, which would be the Fortran `do` defect passing its own
    test: both sides score 1 and agree.
    """
    for index, source in enumerate(LOOPS[suffix]):
        # Numbered rather than hashed: `hash` is salted per interpreter,
        # and a path that changes between runs is not what this project
        # means by a deterministic test.
        complexity, _cognitive = _measure(tmp_path / str(index), suffix, source)

        assert complexity > 1, (
            f"{suffix}: a routine containing a loop scored complexity "
            f"{complexity}, which is what a routine with no branches scores"
        )
