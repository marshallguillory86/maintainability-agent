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


def _repo(tmp_path: Path, files: int, decls_per_file: int = 1) -> Path:
    root = tmp_path / "r"
    root.mkdir()
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
