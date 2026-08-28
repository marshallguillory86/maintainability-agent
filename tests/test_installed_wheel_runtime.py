"""D23 at the installed-artifact boundary, not a checkout staging tree."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_INSTALLED_PROBE = r"""
import asyncio
import json
import sys
from pathlib import Path

import maintainability_audit
from maintainability_audit._catalog import load_catalog
from maintainability_audit.mcp_server import audit_repository, create_server

source_root = Path(sys.argv[1]).resolve()
venv_root = Path(sys.argv[2]).resolve()
fixture = Path(sys.argv[3]).resolve()

resolved_path = []
for entry in sys.path:
    if not entry:
        entry = "."
    resolved_path.append(Path(entry).resolve())
assert not any(
    candidate == source_root or candidate.is_relative_to(source_root)
    for candidate in resolved_path
), f"source checkout leaked onto sys.path: {resolved_path}"

package_file = Path(maintainability_audit.__file__).resolve()
assert package_file.is_relative_to(venv_root), package_file

catalog = load_catalog()
assert catalog, "installed catalog contains no tools"

# The assets themselves, read out of the installed package. This is
# D23 stated exactly: the files the code cannot work without, present
# in the copy a user actually gets.
assets = Path(maintainability_audit.__file__).resolve().parent / "_assets"
standard = (assets / "standard.md").read_text(encoding="utf-8")
catalog_text = (assets / "analyzer-catalog.json").read_text(encoding="utf-8")
assert standard.strip(), "installed standard.md is empty"
assert json.loads(catalog_text)["tools"], "installed analyzer-catalog.json is empty"

# The optional MCP extra is deliberately installed into this isolated
# environment. Resource import or serving failures are therefore test
# failures, not an excuse to omit one of D23's published contracts.
server = create_server(roots=(fixture.parent.resolve(),))

async def resource_text(uri):
    contents = await server.read_resource(uri)
    return "".join(item.content for item in contents)

assert asyncio.run(resource_text("maintainability://standard")).strip()
assert json.loads(asyncio.run(resource_text("maintainability://catalog")))["tools"]

result = audit_repository(
    str(fixture),
    run_analyzers=False,
    record_history=False,
    action="run",
    roots=(fixture.parent.resolve(),),
)
assert result["audit_ran"] is True, result
assert "setup_needed" not in result, result
print(json.dumps({
    "package": str(package_file),
    "tools": len(catalog),
    "audit_ran": result["audit_ran"],
    "resources": "checked",
}))
"""


def _clean_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["XDG_CONFIG_HOME"] = str(tmp_path / "xdg-config")
    env["XDG_STATE_HOME"] = str(tmp_path / "xdg-state")
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return env


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the actual PEP 517 wheel; backend failure is a test failure."""
    work = tmp_path_factory.mktemp("installed-wheel-build")
    result = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            str(work),
            str(ROOT),
        ],
        cwd=work,
        env=_clean_env(work),
    )
    if result.returncode != 0:
        pytest.fail(f"wheel build failed:\n{result.stdout}\n{result.stderr}")
    wheels = list(work.glob("maintainability_agent-*.whl"))
    assert len(wheels) == 1, f"expected one wheel, found {wheels}"
    return wheels[0]


def _venv_python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _install_in_venv(tmp_path: Path, wheel: Path) -> tuple[Path, Path]:
    environment = tmp_path / "venv"
    try:
        # Isolated, not system-site. Inheriting the outer environment is how CI
        # can drag an editable source checkout onto the subprocess path. The
        # MCP extra is installed below so its resource contract is mandatory.
        venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
    except Exception as error:  # pragma: no cover - depends on host Python packaging
        pytest.fail(f"cannot build the throwaway virtualenv: {error}")

    python = _venv_python(environment)
    result = _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--ignore-installed",
            f"{wheel}[mcp]",
        ],
        cwd=tmp_path,
        env=_clean_env(tmp_path),
    )
    if result.returncode != 0:
        pytest.fail(f"wheel install failed:\n{result.stdout}\n{result.stderr}")
    return environment, python


def _configured_fixture(root: Path) -> Path:
    fixture = root / "fixture-repository"
    fixture.mkdir()
    (fixture / "README.md").write_text("# installed wheel fixture\n", encoding="utf-8")
    (fixture / "app.py").write_text("def answer():\n    return 42\n", encoding="utf-8")
    config = {
        "version": 1,
        "analyzers": {"run": False},
        "history": {"record": False},
    }
    (fixture / "maintainability-agent.json").write_text(
        json.dumps(config) + "\n", encoding="utf-8"
    )
    return fixture


def _probe(
    python: Path,
    environment: Path,
    fixture: Path,
    work: Path,
) -> subprocess.CompletedProcess[str]:
    return _run(
        [
            str(python),
            "-c",
            _INSTALLED_PROBE,
            str(ROOT),
            str(environment),
            str(fixture),
        ],
        cwd=work,
        env=_clean_env(work),
    )


def _installed_package(python: Path, work: Path) -> Path:
    result = _run(
        [
            str(python),
            "-c",
            "import maintainability_audit; print(maintainability_audit.__path__[0])",
        ],
        cwd=work,
        env=_clean_env(work),
    )
    assert result.returncode == 0, result.stderr
    return Path(result.stdout.strip()).resolve()


def test_an_actually_installed_wheel_serves_assets_and_audits(
    tmp_path: Path,
    built_wheel: Path,
) -> None:
    environment, python = _install_in_venv(tmp_path, built_wheel)
    fixture = _configured_fixture(tmp_path)

    result = _probe(python, environment, fixture, tmp_path)

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    outcome = json.loads(result.stdout.strip().splitlines()[-1])
    assert outcome["tools"] > 0
    assert outcome["audit_ran"] is True
    assert outcome["resources"] == "checked"


@pytest.mark.parametrize(
    "asset, expected_error",
    [
        ("analyzer-catalog.json", "analyzer catalog missing"),
        ("standard.md", "standard.md"),
    ],
)
def test_the_installed_probe_goes_red_when_a_runtime_asset_is_absent(
    tmp_path: Path,
    built_wheel: Path,
    asset: str,
    expected_error: str,
) -> None:
    environment, python = _install_in_venv(tmp_path, built_wheel)
    fixture = _configured_fixture(tmp_path)
    packaged_asset = _installed_package(python, tmp_path) / "_assets" / asset
    packaged_asset.unlink()

    result = _probe(python, environment, fixture, tmp_path)

    assert result.returncode != 0, (
        f"installed-artifact probe passed without {asset}; it is vacuous"
    )
    assert expected_error in result.stderr
