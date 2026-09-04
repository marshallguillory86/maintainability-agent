"""The calibration tools may not destroy the evidence they exist to produce.

Two tools write the two files every score in this project derives from:
`verify_corpus.py` writes the pinned corpus, `measure.py` writes the
measurements fitted from it. Both could silently replace those files with
something weaker, and both did.

**The corpus.** `verify_corpus.py` defaulted `--out` to `corpus.json` and
wrote there unconditionally. A run whose stdout was redirected somewhere
else still overwrote the checked-in corpus — 40 repositories pinned to the
commits every stored measurement was taken at, replaced by whatever
candidate file was passed. It was noticed because an unrelated guard failed
on the mismatch, which is luck, not design.

**The measurements.** `--check` was already taught not to rewrite the
evidence it checks against. A plain run could still do it: stored
measurements fitted `--with-analyzers` are the analyzer-primary readings the
shipped constants derive from, and a run without that flag measures the
built-ins only. The tool warned about the difference *after* writing.

Both now refuse, and the measurement one refuses at argument-parse time
rather than after cloning the corpus — a decision available immediately
should not cost an hour of network first.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALIBRATION = ROOT / "tools" / "calibration"
sys.path.insert(0, str(CALIBRATION))

import measure  # noqa: E402
import verify_corpus  # noqa: E402


def test_an_existing_corpus_is_not_overwritten_without_saying_so(tmp_path: Path) -> None:
    """The defect: a pinned corpus replaced by a side effect of `--out`."""
    destination = tmp_path / "corpus.json"
    destination.write_text(json.dumps({"repos": [{"name": "pinned"}] * 40}), encoding="utf-8")

    refused = verify_corpus._refuses_to_clobber(destination, replace=False)

    assert refused, "an existing corpus must not be replaced silently"
    assert json.loads(destination.read_text())["repos"], "the corpus was destroyed anyway"


def test_replacing_a_corpus_is_allowed_when_it_is_the_stated_intent(tmp_path: Path) -> None:
    """Recalibration is a real operation; the guard must not block it."""
    destination = tmp_path / "corpus.json"
    destination.write_text(json.dumps({"repos": [{"name": "pinned"}]}), encoding="utf-8")

    assert verify_corpus._refuses_to_clobber(destination, replace=True) is False


def test_a_fresh_destination_is_never_refused(tmp_path: Path) -> None:
    assert verify_corpus._refuses_to_clobber(tmp_path / "new.json", replace=False) is False


def test_a_built_in_only_run_would_downgrade_analyzer_primary_measurements() -> None:
    """The stored corpus is analyzer-primary; a built-in-only run is weaker.

    Reads the real `measurements.json`, because the property under test is
    about the evidence this repository actually ships.
    """
    stored = measure.stored_measurements()
    assert any(entry.get("analyzer_dimensions") for entry in stored), (
        "the checked-in measurements are no longer analyzer-primary; this guard "
        "and the constants fitted from them both need revisiting"
    )

    assert measure._would_downgrade_stored_evidence(with_analyzers=False) is True
    assert measure._would_downgrade_stored_evidence(with_analyzers=True) is False


def test_the_refusal_happens_before_any_cloning(tmp_path: Path) -> None:
    """Refusing after the work is done is still a bug.

    The first version of this check sat at the write site, so a plain run
    cloned all 112 corpus repositories and *then* refused — an hour of
    network to reach a decision available at argument-parse time. A run that
    would be refused must exit in well under the time a single clone takes.
    """
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(CALIBRATION / "measure.py"), "--cache-dir", str(tmp_path)],
        capture_output=True, text=True, timeout=30, cwd=ROOT,
    )

    assert result.returncode == 2, f"expected a refusal, got {result.returncode}"
    assert "refusing to overwrite" in result.stderr
    assert not any(tmp_path.iterdir()), (
        "the cache directory has contents, so cloning started before the refusal"
    )


def test_the_migration_note_states_the_constants_actually_shipped() -> None:
    """A migration note whose numbers are a placeholder is worse than none.

    2.0.0 re-grades every repository that has ever been scored, so the
    note's whole job is to say by how much. It was written before the
    recalibration finished, with the constants section left as an empty
    marked block — exactly the shape that ships unfilled if nothing checks.

    So the shipped values are read from `_calibration.py` and required to
    appear between the markers. The note cannot claim a scale the package
    does not implement, and it cannot be left blank.
    """
    from maintainability_audit._calibration import CALIBRATION_C, DIMENSION_REFERENCES

    note = (ROOT / "docs" / "migration-2.0.md").read_text(encoding="utf-8")
    body = note.split("<!-- constants:begin -->", 1)[1].split("<!-- constants:end -->", 1)[0]

    assert body.strip(), "the constants section of the migration note is empty"
    assert str(CALIBRATION_C) in body, (
        f"the migration note does not state the shipped CALIBRATION_C ({CALIBRATION_C})"
    )
    missing = [name for name in DIMENSION_REFERENCES if name not in body]
    assert not missing, f"the migration note does not name the references {missing}"
    for name, value in DIMENSION_REFERENCES.items():
        assert str(value) in body, (
            f"the migration note does not state the shipped {name} reference ({value})"
        )
