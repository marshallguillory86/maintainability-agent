"""Claim 3, broadened: the adapter population cannot read empty as clean.

The runner seam (`test_empty_output_not_clean.py`) makes a findings-exit
with an empty body ``NOT_WORKING``. This is the other half: every adapter
that parses output with a silent empty default -- ``json.loads(x or "[]"
/ "{}")`` on stdout, or jscpd's report file -- must turn a not-usable run
into a ``parse_error``, never zero findings.

The population is derived by AST from the adapter source, not hand-listed:
any adapter whose ``_read`` contains ``json.loads(<x> or <literal>)``.

Unnamed member: **jscpd**. It reads a report *file*, not stdout, so the
runner's empty-body guard never sees it; a missing report file used to
default to ``{}`` and report zero duplicates. Delete the raw-empty guard
in `JscpdAdapter._read` and the jscpd case below fails, though no other
adapter names the file path.
"""

from __future__ import annotations

import ast
from pathlib import Path

import maintainability_audit._jvm_adapters as jvm
import maintainability_audit._metric_adapters as metric
import maintainability_audit._verdict_adapters as verdict
from maintainability_audit._metric_adapters import JscpdAdapter
from maintainability_audit._runner import Outcome, ToolResult

_MODULES = {"_metric_adapters": metric, "_jvm_adapters": jvm, "_verdict_adapters": verdict}
SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"


def _silent_default_adapters() -> list[type]:
    classes: list[type] = []
    for mod_name, module in _MODULES.items():
        tree = ast.parse((SRC / f"{mod_name}.py").read_text(encoding="utf-8"))
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            for node in ast.walk(cls):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "loads"
                        and any(isinstance(a, ast.BoolOp) and isinstance(a.op, ast.Or)
                                for a in node.args)):
                    classes.append(getattr(module, cls.name))
                    break
    return classes


def _not_working() -> ToolResult:
    """What run() now returns for a findings-exit with an empty body."""
    return ToolResult(slug="x", outcome=Outcome.NOT_WORKING, exit_code=1,
                      stdout="", stderr="", detail="findings exit, no output")


def test_the_silent_default_population_is_derived_and_not_empty() -> None:
    classes = _silent_default_adapters()
    assert len(classes) >= 3, f"expected several silent-default adapters, found {classes}"


def test_no_silent_default_adapter_reads_a_not_working_run_as_zero() -> None:
    """A not-usable run is a parse_error for every silent-default adapter,
    never an empty parse that prices as zero findings."""
    for cls in _silent_default_adapters():
        adapter = cls()
        extraction = adapter.parse(_not_working())
        assert extraction.parse_error, (
            f"{cls.__name__} read a NOT_WORKING run as {extraction.measurements} "
            f"measurements / {extraction.findings} findings instead of a parse_error"
        )


def test_jscpd_with_no_report_and_no_output_is_a_parse_error() -> None:
    """jscpd reads a file, so the runner's empty-body guard never sees it;
    a missing report with empty stdout must not read as zero duplicates."""
    adapter = JscpdAdapter()  # its report dir is a fresh empty tempdir
    ran_but_silent = ToolResult(slug="jscpd", outcome=Outcome.RAN, exit_code=0,
                                stdout="", stderr="")
    extraction = adapter.parse(ran_but_silent)
    assert extraction.parse_error, (
        "jscpd produced no report file and no output but was read as "
        f"{extraction.measurements} measurements / {extraction.findings} findings"
    )
