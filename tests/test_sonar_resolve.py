"""The resolver reaches the finding it is asked about.

`sonar-resolve.yml` exists so a dismissal is auditable: a justification
posted before the transition, in a run log, with a name attached. The
script behind it could not reach a finding raised on a **pull request**,
because `api/issues/search` without `pullRequest` searches the branch and
returns nothing — reported as "no issue …; check the key", which reads
as a wrong key rather than a missing parameter.

That was load-bearing rather than untidy. The quality gate blocks the
merge on a new finding, so the finding has to be dismissable *before*
merging; without the parameter the only path was merge-then-dismiss,
which is the wrong way round for a control whose purpose is reviewing a
finding before it lands.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import sonar_resolve  # noqa: E402


def _capture(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record the URLs the resolver asks for, answering with one issue."""
    asked: list[str] = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self):
            return json.dumps({"issues": [{"key": "K", "status": "OPEN"}]}).encode()

    def _urlopen(request, timeout=0):  # noqa: ANN001, ARG001
        asked.append(request.full_url)
        return _Response()

    monkeypatch.setattr(sonar_resolve.urllib.request, "urlopen", _urlopen)
    return asked


def test_a_pull_request_finding_is_searched_in_its_pull_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The parameter that makes a PR-scoped issue findable at all."""
    asked = _capture(monkeypatch)

    sonar_resolve._current("K", "token", "192")

    assert any("pullRequest=192" in url for url in asked), (
        f"the search did not name the pull request: {asked}"
    )
    # `pullRequest` alone returns an empty list rather than an error, so
    # the project has to accompany it or the key reads as unknown.
    # Measured against the live API before this was written:
    #   issues=KEY&pullRequest=192                    -> 0
    #   issues=KEY&pullRequest=192&componentKeys=PROJ -> 1
    assert any("componentKeys=" in url for url in asked), (
        "the search named the pull request and not the project, which "
        f"SonarCloud answers with an empty list: {asked}"
    )


def test_the_project_key_comes_from_the_scanner_s_own_file() -> None:
    """Covers existing behaviour: one declaration of the project key.

    Read from `sonar-project.properties` rather than repeated in the
    script — a second copy is a second thing to keep true, which is the
    failure mode this repository spent the day closing in prose.
    """
    properties = (
        Path(__file__).resolve().parents[1] / "sonar-project.properties"
    ).read_text(encoding="utf-8")

    assert f"sonar.projectKey={sonar_resolve._project_key()}" in properties


def test_a_branch_finding_is_searched_without_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Covers existing behaviour: a branch finding was always reachable.

    Passes at the base deliberately — the guard that the new parameter
    did not become mandatory. `main`'s own findings must still resolve
    with no pull request to name.
    """
    asked = _capture(monkeypatch)

    sonar_resolve._current("K", "token")

    assert asked and "pullRequest" not in asked[0], (
        f"a branch search should name no pull request: {asked}"
    )


def test_an_unreachable_issue_still_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Covers existing behaviour: an empty result is still a clean exit.

    The message is what a reader acts on, and "no issue" must not start
    meaning "wrong parameter" — which is exactly how the missing
    `pullRequest` presented for the whole time it was absent.
    """
    class _Empty:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self):
            return b'{"issues": []}'

    monkeypatch.setattr(sonar_resolve.urllib.request, "urlopen",
                        lambda request, timeout=0: _Empty())  # noqa: ARG005

    with pytest.raises(SystemExit, match="no issue"):
        sonar_resolve._current("K", "token", "192")
