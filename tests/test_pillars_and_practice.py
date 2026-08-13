"""Five pillars, and two values per pillar that are never averaged — ADR 007.

The decision this implements answers a specific failure. A repository with
no linter, no CI and no gates, whose single function happens to be clean,
scored 5.0/A+. Every number in that report was arithmetically correct. What
was missing is that **nothing was preventing the second function from being
terrible** — and a scan of the source can never see that, because the
evidence for it lives in configuration, not code.

So each pillar carries two independent values:

- **practice level (1-5)** — detectable evidence of *enforcement*, read from
  configuration and CI, never from source. Is there a linter config, is it
  wired into CI, is there a coverage gate, are complexity thresholds set,
  is duplication checked, are decisions recorded.
- **condition** — what the analyzers found in the source, normalized over
  population, which is what the tool already scores.

They answer different questions and the matrix of the two is the finding:

|                    | poor condition            | good condition                |
|--------------------|---------------------------|-------------------------------|
| **high practice**  | known debt, managed       | healthy                       |
| **low practice**   | unmanaged debt            | **unverified** — nothing holds |

The hello-world sits bottom-right. Calling that A+ is the defect; calling
it *"practice level 1, condition unmeasured"* is the truth. **Averaging the
two would reinstate the defect**, so the code may not contain a function
that returns their mean, and a test asserts it structurally rather than
trusting review.

Two pillars are permanently out of scope and say so. Silence reads as
"fine", which is the same lie in a different place: efficiency needs
profiling and load testing this tool does not do, and security belongs to
`secure-code-agent`. Both report `NotApplicable` **naming the reason**, so
a reader never mistakes an absent section for a clean one.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._pillars import (
    PILLARS,
    Scope,
    pillar_report,
)
from maintainability_audit._practice import MAX_WITHOUT_CI, practice_level


def _repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


WORKFLOW = """name: ci
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: %s
"""


# --------------------------------------------------------------------
# The taxonomy, and its declared scope
# --------------------------------------------------------------------


def test_every_pillar_declares_its_scope() -> None:
    """Five pillars, each stating what this tool can and cannot say."""
    assert [p.name for p in PILLARS] == [
        "readability", "maintainability", "efficiency", "security", "testability",
    ]
    assert {p.name: p.scope for p in PILLARS} == {
        "readability": Scope.PARTIAL,
        "maintainability": Scope.OWNED,
        "efficiency": Scope.OUT_OF_SCOPE,
        "security": Scope.DELEGATED,
        "testability": Scope.PARTIAL,
    }


def test_an_out_of_scope_pillar_reports_why_rather_than_vanishing(tmp_path: Path) -> None:
    """Silence reads as "fine", which is the defect wearing a different hat.

    Efficiency needs profiling and load testing this tool does not do.
    Security belongs to `secure-code-agent`. Both are stated, and the
    security entry names the other tool so nobody reads an empty section
    as a clean bill of health.
    """
    _repo(tmp_path / "r", {"a.py": "def f():\n    return 1\n"})
    report = pillar_report({}, {"level": 1})
    by_name = {entry["pillar"]: entry for entry in report}

    assert by_name["efficiency"]["condition"] is None
    assert by_name["efficiency"]["scope"] == Scope.OUT_OF_SCOPE
    assert "profiling" in by_name["efficiency"]["reason"].lower()

    assert by_name["security"]["condition"] is None
    assert "secure-code-agent" in by_name["security"]["reason"]


def test_practice_and_condition_are_never_averaged() -> None:
    """Asserted structurally, because review cannot hold this.

    The two values answer different questions, and one number made from
    both would be exactly the summary that called a hello-world A+. No
    function in the pillar or practice modules may combine them.
    """
    import ast

    for module in ("_pillars", "_practice"):
        source = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"
        tree = ast.parse((source / f"{module}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.BinOp):
                continue
            operands = ast.dump(node)
            assert not ("practice" in operands and "condition" in operands), (
                f"{module} combines practice and condition arithmetically"
            )


# --------------------------------------------------------------------
# Practice level: evidence of enforcement, never source
# --------------------------------------------------------------------


def test_a_repository_with_nothing_is_practice_level_one(tmp_path: Path) -> None:
    """The hello-world. Clean source, and nothing holding it that way."""
    root = _repo(tmp_path / "bare", {"a.py": "def f():\n    return 1\n"})

    level = practice_level(root)

    assert level.level == 1
    assert level.signals == []
    assert "no enforcement" in level.summary.lower()


def test_configuration_without_ci_cannot_exceed_level_two(tmp_path: Path) -> None:
    """A linter nobody runs is a preference, not an enforcement.

    ADR 007's rule, and the one that keeps practice honest: config on
    disk shows intent, CI shows the intent is binding. A repository can
    hold every config file there is and still not stop a bad merge.
    """
    root = _repo(tmp_path / "configured", {
        "a.py": "def f():\n    return 1\n",
        ".pre-commit-config.yaml": "repos: []\n",
        "ruff.toml": "line-length = 100\n",
        "mypy.ini": "[mypy]\nstrict = true\n",
        ".jscpd.json": "{}\n",
        "docs/adr-001-thing.md": "# ADR\n",
    })

    level = practice_level(root)

    assert level.level == MAX_WITHOUT_CI == 2, (
        f"five config files and no CI reached level {level.level}"
    )
    assert any("no ci" in reason.lower() for reason in level.caps)


def test_ci_running_a_linter_reaches_level_three(tmp_path: Path) -> None:
    """Enforcement exists: something fails a build."""
    root = _repo(tmp_path / "ci", {
        "a.py": "def f():\n    return 1\n",
        "ruff.toml": "line-length = 100\n",
        ".github/workflows/ci.yml": WORKFLOW % "ruff check .",
    })

    level = practice_level(root)

    assert level.level >= 3
    assert any(signal["signal"] == "lint-in-ci" for signal in level.signals)


def test_gates_in_ci_reach_the_top_levels(tmp_path: Path) -> None:
    """Coverage and complexity thresholds are the difference between
    running a tool and holding a line."""
    root = _repo(tmp_path / "gated", {
        "a.py": "def f():\n    return 1\n",
        "ruff.toml": "line-length = 100\n",
        ".jscpd.json": "{}\n",
        "docs/adr-001-thing.md": "# ADR\n",
        "pyproject.toml": '[tool.coverage.report]\nfail_under = 92\n',
        ".github/workflows/ci.yml": WORKFLOW % "ruff check . && pytest --cov --cov-fail-under=92",
    })

    level = practice_level(root)

    assert level.level >= 4
    kinds = {signal["signal"] for signal in level.signals}
    assert "coverage-gate" in kinds


def test_practice_reads_configuration_and_never_source(tmp_path: Path) -> None:
    """Enforced structurally: source content must not move the level.

    The whole point of practice is that it measures something a source
    scan cannot see. A practice level that drifted with code quality
    would be the condition score wearing a second name, and the matrix
    that makes the pair useful would collapse.
    """
    shared = {
        "ruff.toml": "line-length = 100\n",
        ".github/workflows/ci.yml": WORKFLOW % "ruff check .",
    }
    tidy = _repo(tmp_path / "tidy", {**shared, "a.py": "def f():\n    return 1\n"})
    awful = _repo(tmp_path / "awful", {
        **shared,
        "a.py": "def f(a,b,c,d,e,f,g,h):\n" + "".join(
            f"    if a == {n}:\n        return {n}\n" for n in range(60)),
    })

    assert practice_level(tidy).level == practice_level(awful).level, (
        "practice level moved with source quality; it must read configuration only"
    )


def test_every_signal_names_the_file_that_proves_it(tmp_path: Path) -> None:
    """A maturity level nobody can check is a grade with no marking scheme."""
    root = _repo(tmp_path / "evidenced", {
        "a.py": "def f():\n    return 1\n",
        "ruff.toml": "line-length = 100\n",
        ".github/workflows/ci.yml": WORKFLOW % "ruff check .",
    })

    level = practice_level(root)

    assert level.signals
    for signal in level.signals:
        assert signal["evidence"], f"{signal['signal']} claimed with no evidence"
        assert (root / signal["evidence"].split(":")[0]).exists(), (
            f"{signal['signal']} cites {signal['evidence']}, which does not exist"
        )


@pytest.mark.parametrize("ci_path", [
    ".github/workflows/build.yml",
    ".gitlab-ci.yml",
    ".circleci/config.yml",
    "Jenkinsfile",
])
def test_ci_is_recognised_wherever_it_lives(tmp_path: Path, ci_path: str) -> None:
    """Four ecosystems, one question: is anything enforced on merge.

    Recognising only GitHub Actions would score every GitLab shop at
    level 2 for using a different host, which is a statement about this
    tool rather than about them.
    """
    root = _repo(tmp_path / ci_path.replace("/", "_"), {
        "a.py": "def f():\n    return 1\n",
        "ruff.toml": "line-length = 100\n",
        ci_path: WORKFLOW % "ruff check ." if ci_path.endswith((".yml", ".yaml"))
        else "pipeline { stages { stage('lint') { steps { sh 'ruff check .' } } } }",
    })

    level = practice_level(root)

    assert level.level >= 3, f"{ci_path} was not recognised as CI"


# --------------------------------------------------------------------
# How the pair lands in a report
# --------------------------------------------------------------------


def test_a_clean_scan_without_enforcement_reads_as_unverified(tmp_path: Path) -> None:
    """The bottom-right cell, and the sentence the whole ADR exists for.

    Good condition with no practice is not health. It is a clean scan
    with nothing preventing tomorrow's regression, and the report has to
    say which of the two it is looking at.
    """
    from maintainability_audit._pillars import posture

    assert posture(level=1, condition=4.6) == "unverified"
    assert posture(level=5, condition=4.6) == "healthy"
    assert posture(level=5, condition=2.1) == "managed debt"
    assert posture(level=1, condition=2.1) == "unmanaged debt"
    assert posture(level=1, condition=None) == "unverified"


def test_the_report_carries_both_values_separately(tmp_path: Path) -> None:
    """Two fields, never one. A consumer must be able to read either."""
    root = _repo(tmp_path / "both", {
        "a.py": "def f():\n    return 1\n",
        "ruff.toml": "line-length = 100\n",
        ".github/workflows/ci.yml": WORKFLOW % "ruff check .",
    })
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    report = build_report(root, load_config(None))
    pillars = report["pillars"]

    assert {entry["pillar"] for entry in pillars} == {p.name for p in PILLARS}
    for entry in pillars:
        assert "practice" in entry and "condition" in entry
        assert "combined" not in entry and "overall" not in entry
    assert report["practice"]["level"] >= 3
    assert json.dumps(report["pillars"]), "the pillar block must serialise"


def test_the_rendered_report_shows_both_axes_and_never_their_mean(tmp_path: Path) -> None:
    """A reader must see which of the four cells they are in.

    The number that mattered in the hello-world report was never printed:
    "practice level 1" would have said everything the 5.0/A+ concealed.
    Rendering condition alone repeats the omission in a new format.
    """
    from maintainability_audit.config import load_config
    from maintainability_audit.renderers import render_markdown
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / "rendered", {
        "a.py": "def f():\n    return 1\n",
        "ruff.toml": "line-length = 100\n",
        ".github/workflows/ci.yml": WORKFLOW % "ruff check .",
    })
    rendered = render_markdown(build_report(root, load_config(None)))

    assert "## Pillars" in rendered
    assert "Practice" in rendered and "Condition" in rendered
    assert "secure-code-agent" in rendered, "the delegated pillar names its owner"
    assert "profiling" in rendered, "the out-of-scope pillar states why"


def test_a_clean_scan_without_ci_is_rendered_as_unverified(tmp_path: Path) -> None:
    """The sentence the whole decision exists to produce."""
    from maintainability_audit.config import load_config
    from maintainability_audit.renderers import render_markdown
    from maintainability_audit.report import build_report

    root = _repo(tmp_path / "helloworld", {"a.py": "def f():\n    return 1\n"})
    rendered = render_markdown(build_report(root, load_config(None)))

    assert "unverified" in rendered
    assert "no enforcement detected" in rendered


def test_an_out_of_scope_pillar_has_no_posture_at_all(tmp_path: Path) -> None:
    """"healthy" for a pillar nobody measured is the original defect.

    The first rendering of this feature printed *"efficiency — healthy:
    enforced, and the code reflects it"* for a pillar whose whole entry
    says profiling is out of scope. Practice level alone had carried it
    into the healthy cell.

    The matrix has two axes and applies only where both exist. Where the
    condition axis is permanently absent, the honest reading is that
    there is no reading.
    """
    report = pillar_report({}, {"level": 5, "summary": "gated", "signals": [], "caps": []})
    by_name = {entry["pillar"]: entry for entry in report}

    assert by_name["efficiency"]["posture"] is None
    assert by_name["security"]["posture"] is None
    # An in-scope pillar with nothing measured yet is different: it could
    # be measured, so it stays unverified rather than becoming nothing.
    assert by_name["readability"]["posture"] is not None


def test_every_in_scope_pillar_names_aspects_the_scorer_emits() -> None:
    """A pillar wired to aspect names nothing produces reports `—` forever.

    `maintainability` was declared over `analyzability`, `modularity`,
    `modifiability` and `reusability` — ISO category names, not the
    aspect names the rubric actually emits — so the owned pillar showed
    an empty condition on every repository. Two vocabularies again, and
    the third time today.
    """
    from maintainability_audit._formula import CATEGORY_ASPECTS

    emitted = {name for aspects in CATEGORY_ASPECTS.values() for name in aspects}
    declared = {name for pillar in PILLARS for name in pillar.aspects}
    unknown = sorted(declared - emitted)

    assert not unknown, (
        f"pillars reference aspects the scorer never emits: {unknown}; "
        f"available: {sorted(emitted)}"
    )
