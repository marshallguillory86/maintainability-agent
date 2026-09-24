"""The ways a finished tool ages, each made to speak rather than wait to be read.

The roadmap names three: the pinned analyzer pool stops resolving, the
calibration describes one year's code, and CI pins one Python while the
package claims three. Each already had a partial answer that depended on
somebody noticing — a scheduled job that went red weekly for any upstream
release, a corpus pinned to commits with no date a reader could see, a
classifier list nothing checked. A signal nobody reads is the same as no
signal; this file is the difference.

* A weekly check that fails opens — or updates — one GitHub issue, and
  closes it again when the check passes, so a failure is a standing item
  rather than a red run in a list.
* The corpus carries the date it was measured, bound to the commit that
  last changed it, disclosed in every report, and checked for age weekly.
* Every Python version the package claims is exercised by some CI job.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _tool(name: str):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------
# the corpus says when it was measured
# --------------------------------------------------------------------

def test_the_corpus_date_is_the_last_change_to_the_corpus() -> None:
    """Bound to history, so re-measuring without re-dating fails here."""
    from maintainability_audit._calibration import CORPUS_MEASURED

    last = subprocess.run(
        ["git", "-C", str(ROOT), "log", "-1", "--format=%cs", "--", "tools/calibration/corpus.json"],
        capture_output=True, text=True, check=True).stdout.strip()
    assert last, "no commit touches the corpus; this reads nothing"

    assert last == CORPUS_MEASURED


def test_every_report_discloses_when_its_reference_was_measured() -> None:
    from maintainability_audit._calibration import CORPUS_MEASURED
    from maintainability_audit.scoring import _reference_block

    block = _reference_block()

    assert block["corpus_measured"] == CORPUS_MEASURED
    assert CORPUS_MEASURED in block["corpus_note"]


def test_a_corpus_within_its_age_limit_passes() -> None:
    age = _tool("check_corpus_age")
    assert age.verdict("2026-09-08", dt.date(2027, 9, 1), max_days=365) is None


def test_a_corpus_past_its_age_limit_says_so_and_what_to_do() -> None:
    age = _tool("check_corpus_age")

    complaint = age.verdict("2026-09-08", dt.date(2027, 9, 9), max_days=365)

    assert complaint is not None
    assert "2026-09-08" in complaint
    assert "recalibrat" in complaint.lower()


# --------------------------------------------------------------------
# a failing weekly check becomes one standing issue
# --------------------------------------------------------------------

def test_a_first_failure_opens_an_issue() -> None:
    issue = _tool("scheduled_issue")
    assert issue.plan(existing=None, failed=True) == "create"


def test_a_repeat_failure_updates_the_same_issue_rather_than_opening_another() -> None:
    """One standing item per check, not a new issue every Monday."""
    issue = _tool("scheduled_issue")
    assert issue.plan(existing=41, failed=True) == "update"


def test_a_passing_check_closes_its_issue() -> None:
    issue = _tool("scheduled_issue")
    assert issue.plan(existing=41, failed=False) == "close"


def test_a_passing_check_with_no_issue_does_nothing() -> None:
    issue = _tool("scheduled_issue")
    assert issue.plan(existing=None, failed=False) == "none"


def test_each_weekly_check_reports_through_the_issue_tool() -> None:
    """A scheduled check with no reporter is the red run nobody reads."""
    gates = (WORKFLOWS / "quality-gates.yml").read_text(encoding="utf-8")
    drift = gates.split("\n  analyzer-drift:", 1)[1].split("\n  audit:", 1)[0]
    maintenance = (WORKFLOWS / "maintenance.yml").read_text(encoding="utf-8")

    assert "tools/scheduled_issue.py" in drift
    for job in ("python-compat", "corpus-age"):
        assert f"\n  {job}:" in maintenance, f"maintenance.yml has no {job} job"
    assert maintenance.count("tools/scheduled_issue.py") >= 2
    assert "issues: write" in maintenance and "issues: write" in drift


# --------------------------------------------------------------------
# every claimed Python is exercised
# --------------------------------------------------------------------

def _claimed_pythons() -> set[str]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return set(re.findall(r"Programming Language :: Python :: (3\.\d+)", text))


def _exercised_pythons() -> set[str]:
    found: set[str] = set()
    for workflow in WORKFLOWS.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        found |= set(re.findall(r'PYTHON_VERSION:\s*"(3\.\d+)"', text))
        found |= set(re.findall(r'python-version:\s*"(3\.\d+)"', text))
        for matrix in re.findall(r"python:\s*\[([^\]]*)\]", text):
            found |= set(re.findall(r"3\.\d+", matrix))
    return found


def test_every_python_the_package_claims_is_exercised_by_ci() -> None:
    """The classifiers said 3.11, 3.12 and 3.13; CI ran only 3.12."""
    claimed = _claimed_pythons()
    assert len(claimed) >= 2, "no version classifiers found; this checks nothing"

    missing = sorted(claimed - _exercised_pythons())

    assert not missing, f"pyproject claims Python {missing} and no CI job runs it"


def test_the_minimum_supported_python_is_one_of_those_exercised() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    floor = re.search(r'requires-python\s*=\s*">=\s*(3\.\d+)"', text).group(1)

    assert floor in _exercised_pythons()
