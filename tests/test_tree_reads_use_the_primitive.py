"""Repository-controlled reads must use the regular-file primitive (D145)."""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"


def _tree_reads() -> list[str]:
    """Direct path reads outside the two primitives and package assets."""
    reads = []
    for path in PACKAGE.rglob("*.py"):
        if path.name == "_operator_reads.py" or "_assets" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            direct = (
                isinstance(func, ast.Attribute) and func.attr in {"read_text", "open"}
            ) or (isinstance(func, ast.Name) and func.id == "open")
            if direct:
                reads.append(f"{path.relative_to(PACKAGE)}:{node.lineno}")
    return reads


def _metadata_names() -> set[str]:
    """Literal repository metadata names used by direct tree readers."""
    names = set()
    tree = ast.parse((PACKAGE / "_discovery.py").read_text(encoding="utf-8"))
    for function in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
        if not any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "read_text"
            for call in ast.walk(function)
        ):
            continue
        for node in ast.walk(function):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "rglob" and node.args and isinstance(node.args[0], ast.Constant):
                    names.add(str(node.args[0].value))
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                if isinstance(node.right, ast.Constant) and isinstance(node.right.value, str):
                    names.add(node.right.value)
    return names


def test_every_tree_read_uses_a_regular_file_primitive() -> None:
    reads = _tree_reads()
    assert reads, "the AST walk found no tree reads; this population proves nothing"
    assert not reads, (
        "repository-controlled reads bypass the regular-file primitive and can "
        "hang on FIFOs or silently skip content:\n" + "\n".join(reads)
    )


@pytest.mark.parametrize("name", sorted(_metadata_names()))
def test_discovery_refuses_metadata_fifos_without_blocking(tmp_path: Path, name: str) -> None:
    """Every discovered metadata name is safe when it is a FIFO, not a file."""
    if "/" in name:
        pytest.skip("not a root metadata file read by discovery")
    fifo = tmp_path / name
    os.mkfifo(fifo)
    probe = (
        "import sys; sys.path.insert(0, {src!r}); from pathlib import Path; "
        "from maintainability_audit._discovery import discover; "
        "from maintainability_audit.config import load_config; "
        "from maintainability_audit._operator_reads import PathNotAllowed;\n"
        "try:\n discover(Path({root!r}), load_config(None))\n"
        "except PathNotAllowed:\n print('refused')\n"
        "else:\n print('returned')\n"
    ).format(src=str(ROOT / "src"), root=str(tmp_path))
    try:
        finished = subprocess.run(
            [sys.executable, "-c", probe], capture_output=True, text=True, timeout=5, check=False
        )
    except subprocess.TimeoutExpired as error:
        pytest.fail(f"metadata FIFO {name!r} blocked discovery for {error.timeout}s")
    assert "refused" in finished.stdout or "returned" in finished.stdout, (
        f"metadata FIFO {name!r} blocked discovery: {finished.stderr[-400:]}"
    )
