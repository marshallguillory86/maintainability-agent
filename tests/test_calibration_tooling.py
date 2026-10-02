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

import contextlib
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


def test_a_candidate_the_scanner_refuses_is_rejected_and_named_not_fatal(tmp_path: Path, monkeypatch) -> None:
    """One unmeasurable candidate used to end the whole verification run.

    Magisk holds an in-tree symlink into a submodule a shallow clone does
    not fetch; the scan refuses it, and the traceback discarded every
    candidate after it. The refusal is a verdict on that candidate.
    """
    from maintainability_audit._operator_reads import PathNotAllowed

    candidates = tmp_path / "candidates.json"
    candidates.write_text(json.dumps({"query": {}, "candidates": [
        {"name": n, "full_name": f"o/{n}", "url": "u", "stars": 1, "created": "2020-01-01", "language": "kotlin"}
        for n in ("refused", "fine")]}), encoding="utf-8")

    def fake_profile(path: Path) -> tuple[int, int]:
        if path.name == "refused":
            raise PathNotAllowed("x.h has a source extension but is not a regular file")
        return 50, 500

    monkeypatch.setattr(verify_corpus, "clone", lambda entry, cache: tmp_path / entry["name"])
    monkeypatch.setattr(verify_corpus, "profile", fake_profile)
    monkeypatch.setattr(verify_corpus, "head_commit", lambda path: "abc")
    out = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", ["verify", str(candidates), "--cache-dir", str(tmp_path), "--out", str(out)])

    assert verify_corpus.main() == 0
    written = json.loads(out.read_text())
    assert [r["name"] for r in written["repos"]] == ["fine"]
    rejected = written["verification"]["rejected"]
    assert rejected[0]["full_name"] == "o/refused" and "not a regular file" in rejected[0]["reason"]


def _fake_measuring(monkeypatch, tmp_path: Path, measured: list[str]) -> None:
    def fake_measure(path: Path, repo: dict, *, with_analyzers: bool = False) -> dict:
        measured.append(repo["name"])
        return {"repo": repo["name"], "pinned_commit": repo["commit"],
                "scanner_fingerprint": measure.scanner_fingerprint(),
                "files": 1, "dimensions": {}, "analyzer_dimensions": {"x": 1.0}}

    monkeypatch.setattr(measure, "clone", lambda repo, cache: tmp_path / repo["name"])
    monkeypatch.setattr(measure, "measure", fake_measure)


def test_a_restarted_run_resumes_from_its_checkpoint(tmp_path: Path, monkeypatch) -> None:
    """A full corpus run is hours long and wrote nothing until the end.

    One interruption cost every row measured so far, and the 4.0.0 run had
    to be restarted to escape a two-hour limit it would have hit at row 100.
    Each row is now appended to a checkpoint in the cache directory as it is
    measured, and a restarted run takes back the rows that still match.
    """
    manifest = {"repos": [{"name": n, "commit": "c"} for n in ("a", "b", "c")]}
    args = measure._parser().parse_args(["--with-analyzers", "--cache-dir", str(tmp_path)])
    measured: list[str] = []
    _fake_measuring(monkeypatch, tmp_path, measured)

    # The first run is interrupted after "a" and "b".
    calls = {"n": 0}
    real = measure.measure

    def interrupted(path, repo, **kwargs):
        calls["n"] += 1
        if calls["n"] == 3:
            raise KeyboardInterrupt
        return real(path, repo, **kwargs)

    monkeypatch.setattr(measure, "measure", interrupted)
    with contextlib.suppress(KeyboardInterrupt):
        measure._collect(manifest, tmp_path, args)

    measured.clear()
    monkeypatch.setattr(measure, "measure", real)
    rows, resumed = measure._collect(manifest, tmp_path, args)

    assert measured == ["c"]
    assert [r["repo"] for r in rows] == ["a", "b", "c"] and resumed == 2


def test_a_checkpoint_from_another_scanner_is_measured_again(tmp_path: Path, monkeypatch) -> None:
    manifest = {"repos": [{"name": "a", "commit": "c"}]}
    args = measure._parser().parse_args(["--with-analyzers", "--cache-dir", str(tmp_path)])
    (tmp_path / measure.CHECKPOINT).write_text(json.dumps(
        {"repo": "a", "pinned_commit": "c", "scanner_fingerprint": "stale",
         "analyzer_dimensions": {"x": 1.0}}) + "\n", encoding="utf-8")
    measured: list[str] = []
    _fake_measuring(monkeypatch, tmp_path, measured)

    rows, resumed = measure._collect(manifest, tmp_path, args)

    assert measured == ["a"] and resumed == 0


def test_measuring_in_parallel_gives_the_same_rows_in_corpus_order(tmp_path: Path, monkeypatch) -> None:
    """A full corpus run took five hours on one core of sixteen.

    The repositories are independent, so `--jobs N` measures N at once.
    What it may not change is the result: the same rows as one at a time,
    in the manifest's order whatever order they finish in, each saved to
    the checkpoint as it lands.
    """
    import time
    from concurrent.futures import ThreadPoolExecutor

    manifest = {"repos": [{"name": n, "commit": "c"} for n in ("slow", "b", "c", "d")]}
    measured: list[str] = []
    _fake_measuring(monkeypatch, tmp_path, measured)
    real = measure.measure

    def uneven(path, repo, **kwargs):
        if repo["name"] == "slow":
            time.sleep(0.2)  # finishes last, listed first
        return real(path, repo, **kwargs)

    monkeypatch.setattr(measure, "measure", uneven)
    serial_args = measure._parser().parse_args(["--with-analyzers", "--cache-dir", str(tmp_path / "s")])
    parallel_args = measure._parser().parse_args(
        ["--with-analyzers", "--cache-dir", str(tmp_path / "p"), "--jobs", "4"])
    (tmp_path / "s").mkdir()
    (tmp_path / "p").mkdir()

    serial, _ = measure._collect(manifest, tmp_path / "s", serial_args)
    parallel, _ = measure._collect(manifest, tmp_path / "p", parallel_args, pool=ThreadPoolExecutor)

    assert parallel == serial
    assert [r["repo"] for r in parallel] == ["slow", "b", "c", "d"]
    assert len(measure._checkpointed(tmp_path / "p")) == 4
