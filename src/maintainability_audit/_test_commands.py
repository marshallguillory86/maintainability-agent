"""The command that runs a repository's tests, read from its build files.

`expected_commands.test` has always been hand-typed. The prompt's example
was `pytest`, so on every non-Python tree the operator was asked a question
the repository could already answer: a `Package.swift` beside a `Tests/`
directory says `swift test` as plainly as a manifest says anything.

**This suggests; it never decides.** The `require_test_command` hard gate
reads "a *documented* test command", and a command this module wrote into
the config unasked would satisfy that gate while nobody had documented
anything — a gate passing on evidence it invented. So detection reaches
exactly one place: the default offered in the setup question, on every
surface. A human still answers it, and their answer is what gets stored.

**Every rule is anchored to a manifest**, never to a directory name alone
or a file extension. `go.mod` means the tree is a Go module; a stray
`.go` file means someone vendored something. The manifest is recorded as
`evidence` and travels with the suggestion, so the question can say *why*
it is proposing this and the operator can disagree with a reason.

**What it refuses to guess**, because a command that cannot run is worse
than no suggestion:

- **An Xcode project with no `Package.swift`.** `xcodebuild test` needs
  `-scheme`, and usually `-destination` as well; neither is derivable from
  the tree with any confidence. The roadmap named `xcodebuild test` as a
  target and it is deliberately not shipped: bare `xcodebuild test` fails
  on every project it would be offered for, and a suggestion that always
  fails teaches the operator to ignore suggestions.
- **`npm test` where `scripts.test` is the placeholder** npm generates
  (`echo "Error: no test specified" && exit 1`). It is a script that
  exists in order not to be a test command.
- **A package with no tests.** `swift test` on a package with no test
  target is an error, so `Tests/` or a `.testTarget` in the manifest is
  required, not just `Package.swift`.

Nothing here runs anything. Detection is file reading, and whether the
suite may be *executed* remains the Class 5 opt-in, default off.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

#: Bounded like `_practice._read`: a manifest is small, and a multi-megabyte
#: `package.json` is not a reason to read a multi-megabyte file.
_READ_LIMIT = 200_000

#: The npm placeholder, written by `npm init` so that `scripts.test` exists.
#: Matching it loosely on purpose — the wording has changed across npm
#: versions and the shape has not.
_NPM_PLACEHOLDER = re.compile(r"no test specified", re.IGNORECASE)

_CMAKE_TESTS = re.compile(r"^\s*(?:enable_testing\s*\(|add_test\s*\()", re.MULTILINE)
_SWIFT_TEST_TARGET = re.compile(r"\.testTarget\s*\(")
_PYTEST_DECLARED = re.compile(
    r"^\s*\[(?:tool\.pytest[.\]]|pytest\]|tool:pytest\])", re.MULTILINE
)


@dataclass(frozen=True)
class TestCommand:
    """A suggested command and the file that suggested it."""

    command: list[str]
    evidence: str


def _read(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(_READ_LIMIT)
    except OSError:
        return ""


def _swift(root: Path) -> TestCommand | None:
    """SwiftPM, and only where a test target exists to run.

    `swift test` on a package without one exits non-zero, so `Package.swift`
    alone is not enough. Either spelling of "there are tests here" counts:
    the conventional `Tests/` directory, or a `.testTarget` the manifest
    declares somewhere else.
    """
    manifest = root / "Package.swift"
    if not manifest.is_file():
        return None
    has_tests = (root / "Tests").is_dir() or bool(
        _SWIFT_TEST_TARGET.search(_read(manifest))
    )
    return TestCommand(["swift", "test"], "Package.swift") if has_tests else None


def _fortran(root: Path) -> TestCommand | None:
    """`fpm.toml` is the Fortran Package Manager's manifest.

    `_practice` already reads this file for fortitude's lint settings, so
    the tree shape is one this tool understood before it could name the
    command that tests it.
    """
    return (
        TestCommand(["fpm", "test"], "fpm.toml")
        if (root / "fpm.toml").is_file()
        else None
    )


def _rust(root: Path) -> TestCommand | None:
    return (
        TestCommand(["cargo", "test"], "Cargo.toml")
        if (root / "Cargo.toml").is_file()
        else None
    )


def _go(root: Path) -> TestCommand | None:
    """`./...` because a bare `go test` tests only the root package.

    The difference matters in a module with any structure at all: the bare
    form silently tests almost nothing and exits zero, which is the worst
    available outcome for a command whose job is to fail.
    """
    return (
        TestCommand(["go", "test", "./..."], "go.mod")
        if (root / "go.mod").is_file()
        else None
    )


def _cmake(root: Path) -> TestCommand | None:
    """`ctest`, but only where the project actually registered tests.

    A `CMakeLists.txt` without `enable_testing()` or `add_test()` builds
    something that has no tests to run, and `ctest` there reports "No tests
    were found" and exits non-zero.
    """
    manifest = root / "CMakeLists.txt"
    if not manifest.is_file() or not _CMAKE_TESTS.search(_read(manifest)):
        return None
    return TestCommand(["ctest"], "CMakeLists.txt")


def _node(root: Path) -> TestCommand | None:
    """`npm test`, unless the script is npm's own placeholder."""
    manifest = root / "package.json"
    if not manifest.is_file():
        return None
    try:
        parsed = json.loads(_read(manifest))
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    script = (parsed.get("scripts") or {}).get("test")
    if not isinstance(script, str) or not script.strip():
        return None
    if _NPM_PLACEHOLDER.search(script):
        return None
    return TestCommand(["npm", "test"], "package.json")


def _python(root: Path) -> TestCommand | None:
    """pytest where a file declares it, not where a `tests/` folder exists.

    A directory named `tests` says nothing about the runner. A
    `[tool.pytest.ini_options]`, `[pytest]` or `[tool:pytest]` section is a
    repository stating which runner it uses, which is the only thing worth
    reading it for.
    """
    if (root / "pytest.ini").is_file():
        return TestCommand(["pytest"], "pytest.ini")
    for name in ("pyproject.toml", "tox.ini", "setup.cfg"):
        manifest = root / name
        if manifest.is_file() and _PYTEST_DECLARED.search(_read(manifest)):
            return TestCommand(["pytest"], name)
    return None


def _maven(root: Path) -> TestCommand | None:
    return (
        TestCommand(["mvn", "test"], "pom.xml")
        if (root / "pom.xml").is_file()
        else None
    )


def _gradle(root: Path) -> TestCommand | None:
    """The wrapper when the repository ships one, because that is the point.

    A checked-in `gradlew` pins the Gradle version the build expects;
    calling bare `gradle` uses whatever the machine happens to have, which
    is the thing the wrapper exists to prevent.
    """
    for name in ("build.gradle", "build.gradle.kts"):
        if (root / name).is_file():
            wrapper = (root / "gradlew").is_file()
            return TestCommand(["./gradlew" if wrapper else "gradle", "test"], name)
    return None


def _dotnet(root: Path) -> TestCommand | None:
    for pattern in ("*.sln", "*.slnx"):
        found = sorted(root.glob(pattern))
        if found:
            return TestCommand(["dotnet", "test"], found[0].name)
    projects = sorted(root.glob("*.csproj"))
    return TestCommand(["dotnet", "test"], projects[0].name) if projects else None


#: Order is the tie-break and is therefore part of the contract: a tree with
#: both a `Package.swift` and a `package.json` gets one answer, the same one
#: every time (P1). Ecosystems whose manifest is unambiguous come first;
#: `package.json` is late because it is the file most often present in a
#: repository whose real subject is something else.
_DETECTORS = (
    _swift,
    _fortran,
    _rust,
    _go,
    _cmake,
    _maven,
    _gradle,
    _dotnet,
    _python,
    _node,
)


def detect_test_commands(root: Path) -> list[TestCommand]:
    """Every command this tree's manifests support, in a fixed order.

    Plural because a repository may honestly have more than one — a Swift
    package with a Node-based docs site is not a malformed tree — and
    reporting only the first would hide that from anyone deciding.
    """
    root = Path(root)
    found = [detector(root) for detector in _DETECTORS]
    return [item for item in found if item is not None]


def suggested_test_command(root: Path) -> TestCommand | None:
    """The one command to offer as the setup question's default, or `None`.

    `None` is a real answer and the common one: most trees this tool audits
    will not carry a manifest it recognises, and the question is then asked
    exactly as it always was.
    """
    found = detect_test_commands(root)
    return found[0] if found else None
