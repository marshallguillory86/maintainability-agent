"""No rate without a population that supports it — ADR 005.

A repository holding one production function and one test scored **5.0 / A+,
evidence complete, verified**. Every finding count was genuinely zero, so the
arithmetic was right and the number was empty: `dead_code 5.0` said only that
one declaration was not dead, and `test_presence 5.0` said one of two
declarations was a test.

Two floors, because one cannot do the job alone:

* **root** — if the tree is smaller than anything the scale was calibrated on,
  nothing drawn from it means anything, *including* the history rates, which
  describe the same tiny codebase;
* **per aspect** — inside a scorable repository, an aspect whose own
  denominator is thin is withheld on its own, so a config-heavy tree with many
  files and few declarations keeps its file-based rates.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._aspects import undersupported_aspects
from maintainability_audit._formula import (
    ASPECT_POPULATIONS,
    CATEGORY_ASPECTS,
    POPULATION_FLOORS,
    ROOT_POPULATIONS,
)
from maintainability_audit.config import load_config
from maintainability_audit.evidence import normalize_report_evidence
from maintainability_audit.report import build_report
from maintainability_audit.scoring import score_report

# Every test here is *about* the floors, so the suite-wide lift in
# conftest must not apply. Declared once for the module rather than
# threaded through each signature.
pytestmark = pytest.mark.usefixtures("real_population_floors")

CORPUS = Path(__file__).resolve().parent.parent / "tools" / "calibration" / "corpus.json"


def test_the_shipped_floors_are_the_corpus_minima() -> None:
    """The suite lifts the floors; this pins what it lifted.

    Without it, a floor could be raised above a calibration member's
    population and no test would notice, because every other test runs
    with the floors disabled.

    It lived in `conftest.py` and was therefore never collected — pytest
    loads a conftest as a plugin, not as a test module — so for as long as
    it existed it asserted nothing. It is compared against
    `conftest.SHIPPED_FLOORS`, captured at import before any fixture
    touches the table, rather than against the live module attribute this
    file's own `real_population_floors` fixture restores.

    Covers existing behaviour: the floors and the corpus it checks them
    against are both older than this change, which only moves the
    assertion somewhere pytest will run it. It cannot fail at the base
    for the plainest possible reason — at the base it is not collected,
    so there is nothing there to fail.
    """
    from conftest import SHIPPED_FLOORS

    repos = json.loads(CORPUS.read_text(encoding="utf-8"))["repos"]
    assert SHIPPED_FLOORS["files_scanned"] <= min(r["source_files"] for r in repos)
    assert SHIPPED_FLOORS["declarations_scanned"] <= min(r["declarations"] for r in repos)
    assert all(value > 0 for value in SHIPPED_FLOORS.values()), (
        "a zero floor ships nothing; the hello-world A+ comes straight back"
    )


def _repo(tmp_path: Path, files: int, decls_per_file: int = 1) -> Path:
    root = tmp_path / "r"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for i in range(files):
        body = "\n".join(f"def f{i}_{j}():\n    return {j}\n" for j in range(decls_per_file))
        (root / f"m{i}.py").write_text(body, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "x"],
        check=True,
    )
    return root


def test_no_calibration_member_is_unscoreable_by_the_scale_it_calibrates() -> None:
    """The floor may never exceed the corpus minimum.

    An earlier draft set the file floor at 39 from memory. The measured
    minimum is 32, so lodash — a calibration member — would have been
    refused a score by the scale it helps define. This is the guard that
    would have caught it, and it recomputes from the corpus rather than
    trusting a number in a comment.
    """
    repos = json.loads(CORPUS.read_text(encoding="utf-8"))["repos"]
    assert repos, "corpus fixture is empty; this test would pass vacuously"

    unscoreable = [
        r["name"] for r in repos
        if r["source_files"] < POPULATION_FLOORS["files_scanned"]
        or r["declarations"] < POPULATION_FLOORS["declarations_scanned"]
    ]
    assert not unscoreable, (
        f"{unscoreable} calibrate the scale but fall below its floors; "
        "a floor above the corpus minimum is not a floor, it is a contradiction"
    )


def test_a_repository_below_the_root_floor_gets_no_score(tmp_path: Path) -> None:
    """P7: a population this small supports no rate, so the score is withheld.

    Three files is below the calibration floor. Publishing a number from
    it would be the absurd figure P7 forbids — a reader with the
    repository in front of them can see there is nothing to judge.
    """
    score = score_report(build_report(_repo(tmp_path, files=3), load_config(None)))

    assert score["maintainability_estimate"] is None
    assert score["maintainability_range"] is None
    assert score["verified_grade"] is None
    assert score["evidence_status"]["status"] == "insufficient"


def test_the_reason_names_the_population_and_the_floor(tmp_path: Path) -> None:
    """"Too small" without numbers leaves the reader unable to act."""
    score = score_report(build_report(_repo(tmp_path, files=3), load_config(None)))
    reasons = score["evidence_status"]["reasons"]

    assert reasons
    joined = " ".join(r["reason"] for r in reasons)
    assert str(POPULATION_FLOORS["declarations_scanned"]) in joined
    assert any(r["measurement"].startswith("summary.") for r in reasons)


def test_findings_survive_an_unscoreable_repository(tmp_path: Path) -> None:
    """Only rates are withheld. A 300-line function is still a fact."""
    root = _repo(tmp_path, files=2)
    body = "\n".join(f"    x{i} = {i}" for i in range(120))
    (root / "big.py").write_text(f"def huge():\n{body}\n    return 0\n", encoding="utf-8")
    report = build_report(root, load_config(None))
    report["score"] = score_report(report)

    assert report["score"]["maintainability_estimate"] is None
    assert any(f["status"] == "fail" for f in report["function_hotspots"]), (
        "withholding a score must not withhold the audit"
    )


def test_every_floored_aspect_names_a_population_that_has_a_floor() -> None:
    """A mapping to a population with no floor would silently do nothing."""
    for aspect, population in ASPECT_POPULATIONS.items():
        assert population in POPULATION_FLOORS, (
            f"{aspect} maps to {population}, which declares no floor"
        )


def test_every_floored_aspect_is_a_real_scored_aspect() -> None:
    """Guards against a typo quietly disabling a floor."""
    scored = {a for weights in CATEGORY_ASPECTS.values() for a in weights}
    unknown = set(ASPECT_POPULATIONS) - scored
    assert not unknown, f"{sorted(unknown)} are floored but not scored anywhere"


@pytest.mark.parametrize("population", ROOT_POPULATIONS)
def test_each_root_population_gates_the_score_on_its_own(
    tmp_path: Path, population: str
) -> None:
    """Swept over the root populations, not pinned to one.

    A root population added later fails here rather than silently
    becoming decorative.
    """
    report = build_report(_repo(tmp_path, files=60, decls_per_file=4), load_config(None))
    assert score_report(report)["maintainability_estimate"] is not None, (
        "fixture must be scoreable before the population is lowered"
    )

    report["summary"][population] = POPULATION_FLOORS[population] - 1
    # Subset relations still have to hold, so pull the dependants down too.
    ceiling = report["summary"][population]
    related = population.replace("_scanned", "")
    for key, value in list(report["summary"].items()):
        dependant = key.endswith(related) or key.startswith("production_")
        if isinstance(value, int) and value > ceiling and dependant:
            report["summary"][key] = min(value, ceiling)
    try:
        scored = score_report(report)
    except Exception:  # noqa: BLE001 - relation guards may reject the doctored summary
        pytest.skip(f"{population} cannot be lowered in isolation without breaking a relation")
    assert scored["maintainability_estimate"] is None


def test_a_scorable_repository_with_one_thin_denominator_keeps_its_other_rates(
    tmp_path: Path,
) -> None:
    """The per-aspect floor exists for exactly this case.

    Plenty of files, few production declarations: the file-based rates
    are supported and must survive, while the declaration-based ones are
    withheld individually.
    """
    report = build_report(_repo(tmp_path, files=60, decls_per_file=4), load_config(None))
    summary = report["summary"]
    summary["production_declarations_scanned"] = 5
    summary["production_function_warnings"] = 0
    summary["production_function_failures"] = 0

    evidence = normalize_report_evidence(report)
    thin = undersupported_aspects(evidence.summary)

    assert "dead_code" in thin, "a rate over five declarations is not evidence"
    assert "file_size" not in thin, "sixty files is ample for a file-based rate"
    assert thin["dead_code"] == (5, POPULATION_FLOORS["production_declarations_scanned"])


def test_a_large_repository_is_unaffected(tmp_path: Path) -> None:
    """The floors must cost a real repository nothing."""
    score = score_report(build_report(_repo(tmp_path, files=60, decls_per_file=4),
                                      load_config(None)))

    assert isinstance(score["maintainability_estimate"], float)
    assert score["evidence_status"]["status"] != "insufficient"


def test_a_withheld_score_names_the_path_out(tmp_path: Path) -> None:
    """"Insufficient" alone leaves the reader with nowhere to go.

    ADR 005 names three situations and they are not workarounds for each
    other, so the message has to say which one this is.
    """
    from maintainability_audit._evidence_view import (
        TAKE_THE_FINDINGS,
        WIDEN_THE_SCAN,
        remedy,
        status_sentence,
    )

    tiny = score_report(build_report(_repo(tmp_path, files=3), load_config(None)))
    assert remedy(tiny) == TAKE_THE_FINDINGS, (
        "no re-scan enlarges a genuinely small repository; telling the reader "
        "to widen the scan would send them in a circle"
    )
    assert "complete" in status_sentence(tiny), (
        "the audit is complete even when the score is withheld, and a reader "
        "who thinks the run failed will not read the findings"
    )

    scoped = build_report(_repo(tmp_path / "b", files=40, decls_per_file=4), load_config(None))
    scoped["mode"] = "changed-only"
    assert remedy(score_report(scoped)) == WIDEN_THE_SCAN


def test_a_reason_follows_the_floor_it_reports(tmp_path: Path, monkeypatch) -> None:
    """Reasons are generated from the table, never written out in prose.

    An earlier version spelled the corpus minima into the sentence and
    went stale the moment a floor was corrected — it kept saying 39 after
    the value became 32. Checking the *text* for a stale number cannot
    catch that in general, so this varies the floor and asserts the
    sentence follows it.
    """
    from maintainability_audit import _formula

    root = _repo(tmp_path, files=3)
    monkeypatch.setattr(
        _formula, "POPULATION_FLOORS", {**POPULATION_FLOORS, "files_scanned": 999}
    )
    reasons = score_report(build_report(root, load_config(None)))["evidence_status"]["reasons"]
    files_reason = next(r for r in reasons if r["measurement"] == "summary.files_scanned")

    assert "999" in files_reason["reason"], "the sentence did not follow the table"


def test_a_hello_world_repository_is_never_scored_whatever_the_floors_say(
    tmp_path: Path, real_population_floors: object,
) -> None:
    """D80: the floors are bounded from below by what they must refuse.

    `test_no_calibration_member_is_unscoreable_by_the_scale_it_calibrates`
    bounds the floors from *above* -- a floor may not exceed the corpus
    minimum. An audit pointed out that nothing bounds them from below.
    Set `files_scanned` to 1 and every check in this file stays green
    while a one-file repository collects a verified A+, which is the
    exact result ADR 005 was written to prevent and the one P7 names:
    a score issued as a consequence of not looking.

    So the property is asserted directly, against the behaviour rather
    than the constant. One file, one declaration, and no score --
    however the table is edited.
    """
    root = _repo(tmp_path, files=1, decls_per_file=1)
    scored = score_report(build_report(root, load_config(None)))

    assert scored["maintainability_estimate"] is None, (
        "a repository holding one file and one function was given a "
        f"score of {scored['maintainability_estimate']}; the floors are "
        "low enough to be no floor at all"
    )
    assert scored["evidence_status"]["status"] == "insufficient", (
        scored["evidence_status"]
    )


def test_the_floors_are_bounded_from_below_as_well_as_above(
    real_population_floors: object,
) -> None:
    """The table itself, so the reason is visible without running a scan.

    The companion above proves the behaviour; this states the invariant
    the behaviour rests on, so someone editing the table sees why it has
    two sides. A floor of 1 admits everything; a floor above the corpus
    minimum refuses the repositories that define the scale.
    """
    repos = json.loads(CORPUS.read_text(encoding="utf-8"))["repos"]
    assert repos, "corpus fixture is empty; this test would pass vacuously"

    smallest_files = min(r["source_files"] for r in repos)
    smallest_decls = min(r["declarations"] for r in repos)
    # Half the smallest calibration member is the loosest bound that
    # still excludes a toy repository. It is a bound, not a
    # recommendation: the shipped values sit at the corpus minima.
    assert POPULATION_FLOORS["files_scanned"] > smallest_files // 2, (
        f"the file floor is {POPULATION_FLOORS['files_scanned']} against a "
        f"corpus minimum of {smallest_files}; a floor that low scores "
        "repositories nobody could form a judgment about"
    )
    assert POPULATION_FLOORS["declarations_scanned"] > smallest_decls // 2, (
        f"the declaration floor is {POPULATION_FLOORS['declarations_scanned']} "
        f"against a corpus minimum of {smallest_decls}"
    )
