"""The tool may not report on code it did not read.

The founding defect of this project, in its most complete form. Every
earlier instance was about a *count* that was absent and read as zero. This
is about the **population itself** being absent: source files that exist,
that the report never opened, and that the score is silent about.

Measured on the validation sample (`tools/validation/sample.json`), all
fourteen repositories, recorded in `tools/validation/results.json`:

- **curl** — lizard measured 20,547 declarations of C. The score was
  computed from 1,041, drawn from curl's Markdown and its Python test
  scripts, and the report printed **4.3**. Its C was never opened by the
  path that produces the number.
- **gson** — lizard measured 9,639 declarations of Java. The score was
  computed from 0 and withheld, with the reason "0 is below the
  calibration floor of 139", which reads as *this repository is too
  small*. It has 9,639 declarations. The truth is *this tool does not
  read Java*, and those two statements send a reader to opposite places.
- **whisper.cpp** — scored 3.5 from 296 declarations in `.js`, `.md`,
  `.html` and `.py`. The C++ the repository exists for was not read.
- **ripgrep, cobra, lapack** — 0 declarations each, same cause.

The root cause is one line of default configuration: `include_extensions`
lists `.py .js .jsx .ts .tsx .html .css .md` and nothing else. Java, Go,
Rust, C, C++, C# and Fortran source is invisible to the scan while being
perfectly visible to the analyzer pool running beside it.

The rule these tests hold:

    A report that has not read the code may not carry a score, and must
    name what it did not read.

Not "should warn". A partial read produces a number about a minority of
the repository and presents it as a number about the repository, which is
a false report — and it is false in the flattering direction, because
Markdown and test scripts are simpler than the code they describe.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from maintainability_audit.config import load_config
from maintainability_audit.renderers import render_markdown
from maintainability_audit.report import build_report


def _repo(root: Path, files: dict[str, str]) -> Path:
    """A git repository containing exactly the files given."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


JAVA = """package a;

public class Thing%(n)d {
    public int compute(int value) {
        int total = 0;
        for (int i = 0; i < value; i++) {
            if (i %% 2 == 0) {
                total += i;
            } else {
                total -= i;
            }
        }
        return total;
    }
}
"""

PYTHON = """def helper_%(n)d(value):
    return value + 1
"""


def _score(root: Path) -> dict:
    return build_report(root, load_config(None))["score"]


def test_a_repository_of_unread_source_gets_no_score(tmp_path: Path) -> None:
    """The gson case, reduced.

    Forty files in a language the scan does not read. Today this reports
    "below the calibration floor", which tells the reader their
    repository is too small when it is nothing of the kind. The status
    may be withheld for any honest reason, but the reason has to be the
    true one, or the remedy the reader reaches for is the wrong remedy.

    Written against gson and Java; Go carries it now, because Java gained
    a detector. The property belongs to any unrecognized language.
    """
    root = _repo(tmp_path / "go", {
        f"src/thing{n}.go": SOURCE_BY_SUFFIX[".go"] % {"n": n} for n in range(40)
    })

    report = build_report(root, load_config(None))
    score = report["score"]

    assert score["maintainability_estimate"] is None, (
        "40 unread Go files must not produce an estimate"
    )
    # Named in the report, and named in what a human reads. Not inside
    # the reason string: a scalar restating `summary.unread_source` can
    # disagree with it, which the evidence model forbids after
    # `history_present` did exactly that.
    assert report["summary"]["unread_source"] == [
        {"suffix": ".go", "language": "Go", "files": 40}
    ]
    rendered = render_markdown(report)
    assert ".go" in rendered and "include_extensions" in rendered, (
        "a reader must be told which extensions went unread and how to fix it"
    )


def test_a_score_is_never_computed_from_a_minority_of_the_source(tmp_path: Path) -> None:
    """The curl case, reduced — and the one that actually produced a number.

    Ninety unread source files beside readable Python ones. The scan sees
    the Python, clears the population floor on it, and reports a score
    for the repository. It is a score for a fraction of the repository,
    and nothing in the output says so. (Curl's unread files were C, which
    1.1.0 reads; the rule is about any unread majority, so these are Rust.)
    """
    files = {f"lib/mod{n}.rs": f"pub fn f{n}(x: i32) -> i32 {{ x + {n} }}\n" for n in range(90)}
    files.update({f"tools/help{n}.py": PYTHON % {"n": n} for n in range(150)})
    root = _repo(tmp_path / "mixed", files)

    score = _score(root)

    assert score["maintainability_estimate"] is None, (
        "a score drawn from 150 of 240 source files, with 90 unread, "
        "describes a different repository than the one audited"
    )


def test_the_report_names_every_unread_source_language(tmp_path: Path) -> None:
    """Naming it is the difference between a gap and a silence.

    A reader who is told "3,000 .java files were not read" can act: widen
    `include_extensions`, or accept that this is a Python-only audit. A
    reader who is told nothing assumes the score covered their code,
    because that is what a score is for.
    """
    root = _repo(tmp_path / "poly", {
        # Read by default now, so it must be absent from the unread list.
        **{f"src/Thing{n}.java": JAVA % {"n": n} for n in range(5)},
        **{f"cmd/main{n}.go": f"func f{n}() int {{ return {n} }}\n" for n in range(3)},
        **{f"lib/mod{n}.rs": f"pub fn f{n}() -> i32 {{ {n} }}\n" for n in range(4)},
        **{f"lib/mod{n}.py": PYTHON % {"n": n} for n in range(200)},
    })

    report = build_report(root, load_config(None))
    unread = report["summary"]["unread_source"]

    assert {entry["suffix"] for entry in unread} == {".go", ".rs"}
    assert {entry["suffix"]: entry["files"] for entry in unread} == {".go": 3, ".rs": 4}
    assert report["summary"]["declarations_scanned"] > 0, (
        "the Java and Python in this tree are read, so they must count"
    )


def test_a_fully_read_repository_is_not_penalised(tmp_path: Path) -> None:
    """The check must not fire on the case it does not describe.

    A Python repository with no unread source has read everything there
    is to read, and must score exactly as it did before this rule
    existed. A safety check that withholds scores from repositories it
    fully understands is worse than the defect it prevents.
    """
    root = _repo(tmp_path / "pure", {f"pkg/mod{n}.py": PYTHON % {"n": n} for n in range(200)})

    report = build_report(root, load_config(None))

    assert report["summary"]["unread_source"] == []
    assert report["score"]["maintainability_estimate"] is not None


# `.java` and `.c` are deliberately absent: each has a detector now (`.c`
# as of 1.1.0), so adding either to `include_extensions` produces a real
# population rather than the false "too small" sentence. Still in the gap:
SOURCE_BY_SUFFIX: dict[str, str] = {
    ".go": "package a\n\nfunc Compute%(n)d(v int) int {\n\tif v > 0 {\n\t\treturn v\n\t}\n\treturn -v\n}\n",
    ".rs": "pub fn compute_%(n)d(v: i32) -> i32 {\n    if v > 0 { v } else { -v }\n}\n",
}


@pytest.mark.parametrize("suffix", sorted(SOURCE_BY_SUFFIX))
def test_following_the_remedy_does_not_produce_a_smaller_lie(
    tmp_path: Path, suffix: str, real_population_floors: dict,
) -> None:
    """The named remedy has to be true after it is followed.

    Default Go is honest: the files are unread, `unread_source` names
    `.go`, and the remedy says add it to `include_extensions`. Doing
    exactly that produced a *different* false statement — the files are
    now read for length, duplication and risk, but nothing extracts
    declarations from them, so `declarations_scanned` is 0, the
    calibration floor fires, and the reader is told:

        "This repository is smaller than anything the scale was
         calibrated on, and no re-scan will change that."

    The repository is not small. It has forty files and no declaration
    detector for its language. Walking a reader into that sentence by
    following our own advice is P7's failure — a withhold reason that is
    a consequence of not looking while claiming something else.

    Parametrized over suffixes that are in `include_extensions` once the
    test adds them and are absent from `DECLARATION_SUFFIXES`, because
    this is a property of that gap and not a fact about any one language.
    Java left the gap when it got a detector; Go, C and Rust have not.

    Takes `real_population_floors` because the shipped floor is what
    produces the false sentence; with the suite's lifted floors the
    repository would score and the defect would be invisible.
    """
    body = SOURCE_BY_SUFFIX[suffix]
    root = _repo(tmp_path / f"widened{suffix.lstrip('.')}",
                 {f"src/Thing{n}{suffix}": body % {"n": n} for n in range(40)})
    config = load_config(None)
    config["paths"]["include_extensions"] = [*config["paths"]["include_extensions"], suffix]

    report = build_report(root, config)
    summary, score = report["summary"], report["score"]

    # The file half of the remedy did work, and that is the trap: it
    # looks like success.
    assert summary["unread_source"] == []
    assert summary["files_scanned"] >= 40
    assert summary["declarations_scanned"] == 0

    assert score["maintainability_estimate"] is None
    reasons = " ".join(item["reason"] for item in score["evidence_status"]["reasons"])
    assert "declaration" in reasons.lower(), (
        f"the withhold must name the missing detector; said: {reasons!r}"
    )
    assert "calibration floor" not in reasons, (
        "the floor is a symptom here, not the cause: there are 40 files and "
        "no parser, not too few files"
    )

    rendered = render_markdown(report)
    assert "smaller than anything the scale was calibrated on" not in rendered, (
        "the report told a 40-file repository it was too small"
    )
    assert suffix in rendered, "the report names the extension it cannot parse"


def test_a_genuinely_small_repository_still_gets_take_the_findings(
    tmp_path: Path, real_population_floors: dict,
) -> None:
    """The path that must not break.

    A tiny Python tree really is below the scale, no re-scan changes
    that, and "take the findings" is the correct and only honest advice.
    A fix for the missing-detector case that swallowed this one would
    trade a false statement for a vaguer one.
    """
    from maintainability_audit._evidence_view import TAKE_THE_FINDINGS, remedy

    root = _repo(tmp_path / "tiny", {"pkg/mod.py": PYTHON % {"n": 0}})

    report = build_report(root, load_config(None))
    reasons = " ".join(
        item["reason"] for item in report["score"]["evidence_status"]["reasons"])

    assert report["score"]["maintainability_estimate"] is None
    assert "calibration floor" in reasons, "this one genuinely is below the floor"
    assert remedy(report["score"]) == TAKE_THE_FINDINGS


@pytest.mark.parametrize("name", ["curl", "gson", "whisper.cpp", "ripgrep"])
def test_the_validation_sample_findings_do_not_recur(name: str) -> None:
    """The four repositories that produced false or misdirected reports.

    Held against the recorded run rather than re-cloning: the point is
    that these exact trees, whose shape is now known, cannot come back.
    Skipped rather than failed when the sample has not been run, because
    a missing artifact is not evidence of correctness either way.
    """
    results = Path(__file__).resolve().parents[1] / "tools" / "validation" / "results.json"
    if not results.exists():
        pytest.skip("validation sample has not been run; see tools/validation/run_sample.py")

    runs = {r["repo"]: r for r in json.loads(results.read_text(encoding="utf-8"))["runs"]}
    run = runs.get(name)
    if run is None or "audit_error" in run or "clone_error" in run:
        pytest.skip(f"{name} was not audited in the recorded run")

    assert run.get("unread_source"), (
        f"{name} is a {run['language']} repository whose source the scan cannot read; "
        "the run must record what it did not read"
    )
    assert run["estimate"] is None, (
        f"{name} reported estimate {run['estimate']} from "
        f"{run['declarations_scanned']} declarations while its source went unread"
    )


def test_es_module_javascript_is_read_like_every_other_javascript(tmp_path: Path) -> None:
    """`.mjs` and `.cjs` are the same language the scanner already parses.

    Found by the validation sample: babel carried 1,503 unread `.mjs` and
    `.cjs` files — 8.5% of its source — while its `.js` was read normally.
    Nothing about those files is different; the extensions were simply
    missing from the default include list, so the scan skipped code it
    was entirely capable of reading.

    Both halves matter. The files must enter the population, and their
    declarations must be *detected* — adding an extension the declaration
    scanner cannot parse would trade unread code for a file counted at
    zero declarations, which is the same lie with better paperwork.
    """
    body = "export function compute(value) {\n  return value + 1;\n}\n"
    root = _repo(tmp_path / "esm", {
        **{f"src/mod{n}.mjs": body for n in range(20)},
        **{f"lib/legacy{n}.cjs": body for n in range(20)},
    })

    report = build_report(root, load_config(None))

    assert report["summary"]["unread_source"] == []
    assert report["summary"]["files_scanned"] >= 40
    assert report["summary"]["declarations_scanned"] >= 40, (
        "an extension in the include list whose declarations are never "
        "detected is unread code wearing a read label"
    )
