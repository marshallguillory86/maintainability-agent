"""P3: omitting band evidence must not improve a graded score."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from _git_path import GIT_PATH

from maintainability_audit.config import load_config
from maintainability_audit.evidence import Unknown, normalize_report_evidence
from maintainability_audit.report import build_report
from maintainability_audit.scoring import _BANDS, score_evidence


BAND_FIELDS = (
    "declaration_band_pressure",
    "production_declaration_band_pressure",
    "file_band_pressure",
    "production_file_band_pressure",
)

_GRADE_RANK = {
    grade: rank
    for rank, (_floor, grade) in enumerate(reversed(_BANDS), start=1)
}


def _git(root: Path, *args: str, author: str) -> None:
    env = {
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": f"{author}@example.test",
        "GIT_COMMITTER_NAME": author,
        "GIT_COMMITTER_EMAIL": f"{author}@example.test",
        "HOME": str(root),
        "PATH": GIT_PATH,
    }
    subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, env=env,
    )


def _elevated_module(prefix: str, count: int = 75) -> str:
    """Functions that warn once, but carry elevated band pressure.

    Eleven branches make each declaration's complexity 12: above the
    warning threshold (10) but below the failure threshold (15). The old
    fallback prices each as a 0.3 warning; the band matrix records 0.5.
    """
    branches = "\n".join(
        f"    if value == {branch}:\n        return {branch}"
        for branch in range(11)
    )
    elevated = "\n\n".join(
        f"def {prefix}_{number}(value):\n{branches}\n    return value"
        for number in range(20)
    )
    clean = "\n\n".join(
        f"def {prefix}_clean_{number}(value):\n    return value"
        for number in range(count - 20)
    )
    return f"{elevated}\n\n{clean}\n"


@pytest.fixture
def elevated_evidence(tmp_path: Path):
    """A live report whose four band values exceed the count fallbacks."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text("## 0.1.0\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "index.md").write_text("# Docs\n", encoding="utf-8")
    modules = [root / f"module_{index}.py" for index in range(4)]
    for index, module in enumerate(modules):
        module.write_text(_elevated_module(f"f{index}"), encoding="utf-8")
    (root / "test_module.py").write_text(
        "\n\n".join(
            f"def test_fixture_{number}():\n    assert True"
            for number in range(20)
        ),
        encoding="utf-8",
    )

    _git(root, "init", "-q", ".", author="author0")
    for revision in range(6):
        module = modules[revision % len(modules)]
        module.write_text(
            module.read_text(encoding="utf-8") + f"# revision {revision}\n",
            encoding="utf-8",
        )
        _git(root, "add", "-A", author=f"author{revision}")
        _git(root, "commit", "-qm", f"revision {revision}", author=f"author{revision}")

    config = load_config(None)
    config["thresholds"].update({"warn_file_lines": 1_000, "max_file_lines": 2_000})
    return normalize_report_evidence(build_report(root, config))


def _concealed(evidence, field: str):
    return replace(
        evidence,
        summary=replace(
            evidence.summary,
            **{field: Unknown("withheld P3 band evidence", f"summary.{field}")},
        ),
    )


def _grade_rank(grade: str | None) -> int:
    return 0 if grade is None else _GRADE_RANK[grade]


@pytest.mark.parametrize("field", BAND_FIELDS)
def test_concealing_band_evidence_cannot_improve_a_graded_field(
    elevated_evidence, field: str,
) -> None:
    """P3 through the shipped report and evidence-scoring seams.

    The baseline has the elevated band measurement produced by
    ``build_report``. Concealment selects `_banded`'s lower count-rate
    fallback. Every field is independently material: both the numerical
    estimate and its verified letter must therefore stay no better.
    """
    visible = score_evidence(elevated_evidence)
    concealed = score_evidence(_concealed(elevated_evidence, field))

    assert visible["verified_grade"] is not None
    assert visible["maintainability_estimate"] is not None
    assert concealed["maintainability_estimate"] <= visible["maintainability_estimate"], (
        f"concealing summary.{field} improved the estimate: "
        f"{visible['maintainability_estimate']} -> "
        f"{concealed['maintainability_estimate']}"
    )
    assert _grade_rank(concealed["verified_grade"]) <= _grade_rank(
        visible["verified_grade"],
    ), (
        f"concealing summary.{field} improved the grade: "
        f"{visible['verified_grade']} -> {concealed['verified_grade']}"
    )
    assert concealed["evidence_status"]["status"] == "incomplete", (
        f"summary.{field} is score-bearing evidence, but withholding it "
        "left the report verified"
    )
