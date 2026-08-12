"""ADR 001 stage 6: invariants over the whole nested evidence model.

Not another collection of missing-field examples. Every case here is
derived by walking the typed model produced by ``build_report`` on a
real repository, so a field added to ``SummaryEvidence`` or
``HistoryEvidence`` is swept the day it is added and nobody has to
remember to extend a list. Six audit rounds were survived by suites that
enumerated the failures already demonstrated.

Two production fixtures, both scoring *complete*:

- ``settled_evidence`` — six commits by different authors, each touching
  the same pair of modules, so every
  scored aspect is measured and the uncertainty range legitimately
  collapses.
- ``young_evidence`` — one commit, which carries a genuine
  ``NotApplicable`` (no file has three commits, so ownership
  concentration has no population) alongside many ``Measured(0)``.

Scoring goes through ``score_evidence``, the production seam, so these
properties are about the shipped scorer rather than a copy of it.

Stage 6 is the model. Human-facing rendering of these states is stage 7
and is deliberately untouched.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from maintainability_audit._formula import rollup
from maintainability_audit._verification import DEFAULT_V1_NOT_REQUIRED, DEFAULT_V1_REQUIRED
from maintainability_audit.config import load_config
from maintainability_audit.evidence import (
    HistoryEvidence,
    Measured,
    NormalizedEvidence,
    NotApplicable,
    SummaryEvidence,
    Unknown,
    normalize_report_evidence,
    walk_evidence,
)
from maintainability_audit.report import build_report
from maintainability_audit.scoring import score_evidence

MODEL_PATHS = tuple(
    [f"summary.{field.name}" for field in SummaryEvidence.__dataclass_fields__.values()]
    + [f"history.{field.name}" for field in HistoryEvidence.__dataclass_fields__.values()]
)

ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "PATH": "/usr/bin:/bin",
}


def _git(root: Path, *args: str, author: str = "t") -> None:
    env = {**ENV, "HOME": str(root), "GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": f"{author}@t"}
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=env)


def _documented(root: Path) -> None:
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text("## 0.1.0\n- start\n", encoding="utf-8")
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "index.md").write_text("# Docs\n", encoding="utf-8")


@pytest.fixture(scope="module")
def settled_evidence(tmp_path_factory) -> NormalizedEvidence:
    """Four commits by four authors: every scored aspect is measurable.

    Ownership needs files with three or more commits before it has a
    population, so a younger repository cannot exercise the fully
    measured case.
    """
    root = tmp_path_factory.mktemp("settled")
    _documented(root)
    _git(root, "init", "-q", ".")
    # Six commits, each touching alpha and beta together, so the pair
    # clears the co-change support threshold and change_coupling scores
    # something other than a perfect 5.0. A fixture where every history
    # aspect is already 5.0 cannot detect a defect that *invents* 5.0.
    for index in range(1, 7):
        (root / "alpha.py").write_text(f"def alpha(value):\n    return value + {index}\n", encoding="utf-8")
        (root / "beta.py").write_text(f"def beta(value):\n    return value * {index}\n", encoding="utf-8")
        (root / "test_alpha.py").write_text(
            "from alpha import alpha\n\n\ndef test_alpha():\n    assert alpha(1)\n", encoding="utf-8"
        )
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", f"change {index}", author=f"author{index}")
    return normalize_report_evidence(build_report(root, load_config(None)))


@pytest.fixture(scope="module")
def young_evidence(tmp_path_factory) -> NormalizedEvidence:
    """One commit: carries a real NotApplicable beside many Measured(0)."""
    root = tmp_path_factory.mktemp("young")
    _documented(root)
    (root / "app.py").write_text("def ok(value):\n    return value + 1\n", encoding="utf-8")
    (root / "test_app.py").write_text(
        "from app import ok\n\n\ndef test_ok():\n    assert ok(1) == 2\n", encoding="utf-8"
    )
    _git(root, "init", "-q", ".")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "start")
    return normalize_report_evidence(build_report(root, load_config(None)))


def state_at(evidence: NormalizedEvidence, path: str):
    section, _, field = path.partition(".")
    return getattr(getattr(evidence, section), field)


def with_state(evidence: NormalizedEvidence, path: str, state) -> NormalizedEvidence:
    """The model with one node replaced, everything else untouched.

    Dataclass replacement rather than rebuilding a raw dictionary: the
    point of the sweep is to vary a *state*, and reconstructing a report
    would go back through normalization and change what is being tested.
    """
    section, _, field = path.partition(".")
    node = getattr(evidence, section)
    return replace(evidence, **{section: replace(node, **{field: state})})


def concealed(evidence: NormalizedEvidence, path: str) -> NormalizedEvidence:
    return with_state(evidence, path, Unknown("withheld by the stage 6 sweep", path))


def resolved_required_paths(evidence: NormalizedEvidence) -> list[str]:
    return sorted(
        path
        for path, state in walk_evidence(evidence)
        if path in DEFAULT_V1_REQUIRED and not isinstance(state, Unknown)
    )


# ---------------------------------------------------------------------------
# 1. Walker completeness
# ---------------------------------------------------------------------------

def test_the_walker_reaches_every_typed_scoring_input(settled_evidence: NormalizedEvidence) -> None:
    walked = {path for path, _ in walk_evidence(settled_evidence)}

    assert walked == set(MODEL_PATHS)
    assert any(path.startswith("summary.") for path in walked)
    assert any(path.startswith("history.") for path in walked), "nested history must be reached"


def test_the_profile_classifies_every_input_exactly_once() -> None:
    assert not (DEFAULT_V1_REQUIRED & DEFAULT_V1_NOT_REQUIRED), "a path cannot be both"
    assert set(MODEL_PATHS) == (DEFAULT_V1_REQUIRED | DEFAULT_V1_NOT_REQUIRED)


def test_both_fixtures_start_complete_and_verified(
    settled_evidence: NormalizedEvidence, young_evidence: NormalizedEvidence
) -> None:
    """The sweeps below are meaningless if the baselines are not complete."""
    for evidence in (settled_evidence, young_evidence):
        score = score_evidence(evidence)
        assert score["evidence_status"]["status"] == "complete"
        assert score["verified_grade"] is not None

    assert any(
        isinstance(state, NotApplicable) for _, state in walk_evidence(young_evidence)
    ), "the young fixture must carry a real NotApplicable"
    assert any(
        isinstance(state, Measured) and state.value == 0
        for _, state in walk_evidence(young_evidence)
    ), "the young fixture must carry a real Measured(0)"


# ---------------------------------------------------------------------------
# 2. Recursive evidence removal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", MODEL_PATHS)
def test_concealing_any_required_node_withholds_verification(
    settled_evidence: NormalizedEvidence, path: str
) -> None:
    """The class, swept: every required node, one at a time.

    Seven assertions per path, including the two that matter most —
    the evidence floor must not rise and the compatibility grade must
    not improve — because "hiding evidence pays" is the defect this
    whole architecture exists to make impossible.
    """
    if path not in DEFAULT_V1_REQUIRED:
        pytest.skip(f"{path} is not required by default-v1")
    baseline = score_evidence(settled_evidence)
    hidden_model = concealed(settled_evidence, path)

    hidden = score_evidence(hidden_model)

    assert hidden["evidence_status"]["status"] == "incomplete"
    assert hidden["verified_grade"] is None
    named = [reason["measurement"] for reason in hidden["evidence_status"]["reasons"]]
    assert named == [path], f"reasons must name exactly {path}, got {named}"
    assert hidden["maintainability_range"][0] <= baseline["maintainability_range"][0], "the evidence floor rose"
    unmeasured = [
        name for name, value in hidden["aspects"].items()
        if value is None and baseline["aspects"][name] is not None
    ]
    if unmeasured:
        # Non-strict comparison alone is vacuous on a fixture already at
        # 5.0: mutation testing showed two real defects — an Unknown
        # read as "zero findings", and an unmeasured history rate read
        # as clean — passing the sweep because the floor merely stayed
        # equal. When concealment does unmeasure an aspect, that aspect
        # prices at zero and the floor must actually move.
        assert hidden["maintainability_range"][0] < baseline["maintainability_range"][0], (
            f"concealing {path} unmeasured {unmeasured} without lowering the floor"
        )
    assert hidden["maintainability_range"][0] <= hidden["maintainability_estimate"] <= hidden["maintainability_range"][1]
    untouched = {
        other: state for other, state in walk_evidence(hidden_model) if other != path
    }
    assert untouched == {
        other: state for other, state in walk_evidence(settled_evidence) if other != path
    }, "concealing one node disturbed another"


@pytest.mark.parametrize("path", MODEL_PATHS)
def test_concealing_a_not_applicable_node_also_withholds_verification(
    young_evidence: NormalizedEvidence, path: str
) -> None:
    """NotApplicable is resolved evidence; removing it is still removal.

    Swept on the young fixture because that is where NotApplicable
    actually occurs — asserting it on a fixture that has none would
    prove nothing.
    """
    if path not in DEFAULT_V1_REQUIRED:
        pytest.skip(f"{path} is not required by default-v1")
    baseline = score_evidence(young_evidence)

    hidden = score_evidence(concealed(young_evidence, path))

    assert hidden["evidence_status"]["status"] == "incomplete"
    assert hidden["verified_grade"] is None
    assert hidden["maintainability_range"][0] <= baseline["maintainability_range"][0]
    assert hidden["verified_grade"] is None


@pytest.mark.parametrize("path", MODEL_PATHS)
def test_an_aspect_that_uses_a_concealed_input_is_unmeasured_not_re_estimated(
    settled_evidence: NormalizedEvidence, path: str
) -> None:
    """If concealing an input moves an aspect, that aspect must go None.

    Dependency is *derived*, not declared: an aspect whose value changes
    when an input is withheld was plainly reading that input, so with the
    input Unknown it must report unmeasured rather than a different
    number. A new number would be an estimate manufactured from evidence
    that no longer exists.

    Mutation testing is why this exists. Seeding "an unmeasured history
    rate reads as clean" left every earlier property passing, because it
    replaced None with a plausible 5.0 and nothing asserted the
    difference between *unmeasured* and *re-estimated*.
    """
    if path not in DEFAULT_V1_REQUIRED:
        pytest.skip(f"{path} is not required by default-v1")
    baseline = score_evidence(settled_evidence)["aspects"]

    hidden = score_evidence(concealed(settled_evidence, path))["aspects"]

    re_estimated = {
        name: (baseline[name], value)
        for name, value in hidden.items()
        if value != baseline[name] and value is not None
    }
    assert not re_estimated, (
        f"concealing {path} re-estimated {re_estimated} instead of reporting them unmeasured"
    )


def test_every_scored_aspect_is_unmeasured_by_concealing_some_required_input(
    settled_evidence: NormalizedEvidence,
) -> None:
    """No aspect may survive the removal of all its evidence.

    The property that caught two seeded defects the per-path sweep let
    through. If an aspect still produces a number when every input it
    depends on is Unknown, it is manufacturing evidence — which is the
    original bug class in its purest form, and is invisible to
    assertions that only check the floor did not rise.

    Coverage is derived by sweeping, not declared, so an aspect added
    later must also be reachable by concealment.
    """
    baseline = score_evidence(settled_evidence)
    survives = set(baseline["aspects"])
    for path in resolved_required_paths(settled_evidence):
        hidden = score_evidence(concealed(settled_evidence, path))
        survives -= {name for name, value in hidden["aspects"].items() if value is None}

    assert not survives, (
        f"aspects that no concealment could unmeasure: {sorted(survives)} — "
        "each is scoring from something other than required evidence"
    )


# ---------------------------------------------------------------------------
# 3. Adding evidence back
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", MODEL_PATHS)
def test_restoring_a_concealed_node_recovers_everything(
    settled_evidence: NormalizedEvidence, path: str
) -> None:
    """Adding evidence may narrow and may verify; it must not rewrite.

    ADR 001 §6: adding evidence must not change the meaning of values
    already measured. Restoring the original state has to return the
    identical model and the identical score, not merely a similar one.
    """
    if path not in DEFAULT_V1_REQUIRED:
        pytest.skip(f"{path} is not required by default-v1")
    original_state = state_at(settled_evidence, path)
    baseline = score_evidence(settled_evidence)
    hidden_model = concealed(settled_evidence, path)
    hidden = score_evidence(hidden_model)

    restored_model = with_state(hidden_model, path, original_state)
    restored = score_evidence(restored_model)

    assert restored_model == settled_evidence, "the original model was not recovered"
    assert state_at(restored_model, path) == original_state, "state, value or provenance changed"
    assert restored["verified_grade"] == baseline["verified_grade"] is not None
    restored_width = restored["maintainability_range"][1] - restored["maintainability_range"][0]
    hidden_width = hidden["maintainability_range"][1] - hidden["maintainability_range"][0]
    assert restored_width <= hidden_width, "adding evidence widened the range"
    assert restored == baseline, "the score did not return to its original result"


# ---------------------------------------------------------------------------
# 4. Complete evidence collapses the range
# ---------------------------------------------------------------------------

def test_fully_measured_evidence_collapses_the_range(settled_evidence: NormalizedEvidence) -> None:
    """The direct case where every aspect is genuinely measured.

    The separate NotApplicable test covers resolved evidence with no
    population; that state also contributes no uncertainty.
    """
    score = score_evidence(settled_evidence)

    assert [name for name, value in score["aspects"].items() if value is None] == []
    assert score["evidence_status"]["status"] == "complete"
    assert score["verified_grade"] is not None
    assert score["maintainability_range"] == [score["maintainability_estimate"], score["maintainability_estimate"]]


def test_not_applicable_is_excluded_instead_of_priced_as_clean_or_unknown() -> None:
    """No population contributes neither score nor uncertainty."""
    scores = {"measured": 2.0, "no_population": None}
    weights = {"measured": 0.5, "no_population": 0.5}
    excluded = frozenset({"no_population"})

    assert rollup(scores, weights, unknown_price=0.0, not_applicable=excluded) == 2.0
    assert rollup(scores, weights, unknown_price=5.0, not_applicable=excluded) == 2.0
    assert rollup(scores, weights, unknown_price=0.0) == 1.0
    assert rollup(scores, weights, unknown_price=5.0) == 3.5


# ---------------------------------------------------------------------------
# 5. The three states survive serialization
# ---------------------------------------------------------------------------

def test_the_three_states_remain_distinguishable_across_a_json_round_trip(tmp_path: Path) -> None:
    """Measured(0), Unknown and NotApplicable must not collapse in JSON.

    Report shapes are round-tripped as a real consumer would, then
    normalized again, because a serializer that erased the distinction
    would defeat the model no matter how careful the scorer is.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _documented(root)
    (root / "app.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    (root / "test_app.py").write_text(
        "from app import ok\n\n\ndef test_ok():\n    assert ok() == 1\n", encoding="utf-8"
    )
    _git(root, "init", "-q", ".")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "start")
    report = build_report(root, load_config(None))
    del report["summary"]["test_file_count"]  # an Unknown to carry through

    revived = normalize_report_evidence(json.loads(json.dumps(report)))

    zero = revived.summary.risk_findings
    unknown = revived.summary.test_file_count
    not_applicable = revived.history.single_author_files
    assert isinstance(zero, Measured) and zero.value == 0
    assert isinstance(unknown, Unknown) and unknown.reason and unknown.provenance
    assert isinstance(not_applicable, NotApplicable) and not_applicable.reason
    assert type(zero) is not type(unknown) is not type(not_applicable)


# ---------------------------------------------------------------------------
# 6. Invalid structures fail closed
#
# Covered by tests/test_evidence_invariants.py, which iterates the same
# SUMMARY_SUBSETS / SUMMARY_SUMS / HISTORY_SUBSETS tables and asserts the
# *specific* validator fired via `match=`. A version lived here briefly
# and was removed: it set `first_part=99, whole=1` for every rule, which
# trips an ordinary subset check before the sum check is ever reached —
# so the sum cases raised for the wrong reason while the architecture
# doc claimed they proved every declared invariant. Two tests over one
# table, one of them passing on the wrong invariant, is worse than one
# correct test.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 7. Determinism
# ---------------------------------------------------------------------------

def test_the_whole_sweep_is_deterministic(settled_evidence: NormalizedEvidence) -> None:
    """Same evidence in, byte-identical documents out, twice.

    Includes reason ordering: a report diffed against another must not
    show spurious reordering of the measurements it is missing.
    """
    def sweep() -> str:
        results = {
            path: score_evidence(concealed(settled_evidence, path))
            for path in resolved_required_paths(settled_evidence)
        }
        results["__baseline__"] = score_evidence(settled_evidence)
        return json.dumps(results, sort_keys=True, default=str)

    assert sweep() == sweep()


def test_the_sweep_covers_both_summary_and_nested_history(
    settled_evidence: NormalizedEvidence,
) -> None:
    """Guards the harness itself.

    If the walker or the profile stopped reaching history, every sweep
    above would still pass while silently testing half the model.
    """
    swept = resolved_required_paths(settled_evidence)

    assert len([p for p in swept if p.startswith("summary.")]) == 23
    assert len([p for p in swept if p.startswith("history.")]) == 5
    assert len(swept) == len(DEFAULT_V1_REQUIRED)
