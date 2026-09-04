"""Reading a test command out of a repository's build files.

`expected_commands.test` was hand-typed on every tree, with `pytest` as the
prompt's example, so the question was hardest to answer exactly where this
tool had just learned to parse the language — a Swift package states
`swift test` in its manifest as plainly as anything is stated.

What is worth testing here is not that `Package.swift` maps to
`swift test`. It is the four judgments underneath:

- a suggestion is a **default**, never a decision, because the hard gate
  reads "a *documented* test command";
- a command that cannot run is worse than no suggestion, which is why
  `xcodebuild test` is deliberately absent;
- evidence is a manifest, never a directory name or a file extension;
- the order is fixed, because a tree with two manifests must get the same
  answer twice (P1).
"""

from __future__ import annotations

from pathlib import Path

from maintainability_audit._test_commands import (
    detect_test_commands,
    suggested_test_command,
)


def _tree(root: Path, files: dict[str, str], dirs: tuple[str, ...] = ()) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    for name in dirs:
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def _command(root: Path) -> list[str] | None:
    found = suggested_test_command(root)
    return found.command if found is not None else None


# ---------------------------------------------------------------------------
# Swift, the case this was built for
# ---------------------------------------------------------------------------

def test_a_swift_package_with_tests_names_swift_test(tmp_path: Path) -> None:
    root = _tree(
        tmp_path / "pkg",
        {"Package.swift": "// swift-tools-version:5.9\n"},
        dirs=("Tests",),
    )

    found = suggested_test_command(root)

    assert found is not None
    assert found.command == ["swift", "test"]
    assert found.evidence == "Package.swift", (
        "the suggestion must carry the file that proposed it, so the "
        "question can say why and the operator can disagree with a reason"
    )


def test_a_test_target_counts_when_the_tests_live_elsewhere(tmp_path: Path) -> None:
    """`Tests/` is the convention, not the requirement."""
    root = _tree(tmp_path / "pkg", {
        "Package.swift": 'targets: [.testTarget(name: "T", path: "Spec")]\n',
    })

    assert _command(root) == ["swift", "test"]


def test_a_swift_package_with_no_tests_suggests_nothing(tmp_path: Path) -> None:
    """`swift test` on a package with no test target exits non-zero.

    Suggesting it would hand the operator a command that fails on first
    use, which teaches them that suggestions are noise.
    """
    root = _tree(tmp_path / "pkg", {"Package.swift": "// swift-tools-version:5.9\n"})

    assert suggested_test_command(root) is None


def test_an_xcode_project_alone_suggests_nothing(tmp_path: Path) -> None:
    """The roadmap named `xcodebuild test`; it is deliberately not shipped.

    Bare `xcodebuild test` needs `-scheme`, and usually `-destination` too.
    Neither is derivable from the tree with any confidence, so every
    suggestion this would produce is a command that fails. Refusing is the
    same call `_ranges_swift` makes about an Allman-braced declaration:
    the cheaper error.
    """
    root = _tree(tmp_path / "app", {"App.xcodeproj/project.pbxproj": "// x\n"})

    assert suggested_test_command(root) is None


# ---------------------------------------------------------------------------
# The other manifests, and what each one refuses
# ---------------------------------------------------------------------------

def test_the_npm_placeholder_is_not_a_test_command(tmp_path: Path) -> None:
    """`npm init` writes a `scripts.test` that exists in order not to work."""
    root = _tree(tmp_path / "js", {
        "package.json": '{"scripts": {"test": '
                        '"echo \\"Error: no test specified\\" && exit 1"}}',
    })

    assert suggested_test_command(root) is None


def test_a_real_npm_script_is_a_test_command(tmp_path: Path) -> None:
    root = _tree(tmp_path / "js", {"package.json": '{"scripts": {"test": "vitest"}}'})

    assert _command(root) == ["npm", "test"]


def test_malformed_json_suggests_nothing_rather_than_raising(tmp_path: Path) -> None:
    """A setup question must not be the thing that crashes on a bad file."""
    root = _tree(tmp_path / "js", {"package.json": "{not json"})

    assert suggested_test_command(root) is None


def test_cmake_without_registered_tests_suggests_nothing(tmp_path: Path) -> None:
    """`ctest` reports "No tests were found" and exits non-zero."""
    bare = _tree(tmp_path / "c", {"CMakeLists.txt": "project(thing)\n"})
    assert suggested_test_command(bare) is None

    with_tests = _tree(tmp_path / "c2", {
        "CMakeLists.txt": "project(thing)\nenable_testing()\nadd_test(NAME a COMMAND a)\n",
    })
    assert _command(with_tests) == ["ctest"]


def test_go_tests_the_whole_module_not_just_its_root(tmp_path: Path) -> None:
    """A bare `go test` tests only the root package and exits zero.

    Silently testing almost nothing, successfully, is the worst available
    outcome for a command whose job is to fail.
    """
    root = _tree(tmp_path / "go", {"go.mod": "module example.com/m\n"})

    assert _command(root) == ["go", "test", "./..."]


def test_the_gradle_wrapper_wins_when_the_repository_ships_one(tmp_path: Path) -> None:
    """A checked-in `gradlew` pins the version the build expects."""
    bare = _tree(tmp_path / "j", {"build.gradle": "plugins { id 'java' }\n"})
    assert _command(bare) == ["gradle", "test"]

    wrapped = _tree(tmp_path / "j2", {
        "build.gradle": "plugins { id 'java' }\n", "gradlew": "#!/bin/sh\n",
    })
    assert _command(wrapped) == ["./gradlew", "test"]


def test_a_tests_directory_alone_is_not_evidence(tmp_path: Path) -> None:
    """A folder named `tests` says nothing about which runner reads it.

    Every rule here is anchored to a manifest for this reason: the
    directory is a convention, and conventions are what a tool guesses
    with when it has no evidence.
    """
    root = _tree(tmp_path / "py", {"README.md": "# thing\n"}, dirs=("tests",))

    assert suggested_test_command(root) is None


def test_pytest_is_read_from_a_declaration_not_a_directory(tmp_path: Path) -> None:
    for name, body in (
        ("pyproject.toml", "[tool.pytest.ini_options]\ntestpaths = ['tests']\n"),
        ("setup.cfg", "[tool:pytest]\ntestpaths = tests\n"),
        ("tox.ini", "[pytest]\ntestpaths = tests\n"),
    ):
        root = _tree(tmp_path / name.replace(".", "_"), {name: body})
        found = suggested_test_command(root)
        assert found is not None and found.command == ["pytest"], name
        assert found.evidence == name


def test_a_pyproject_without_a_pytest_section_suggests_nothing(tmp_path: Path) -> None:
    root = _tree(tmp_path / "py", {"pyproject.toml": '[project]\nname = "x"\n'})

    assert suggested_test_command(root) is None


# ---------------------------------------------------------------------------
# The contract the callers depend on
# ---------------------------------------------------------------------------

def test_two_manifests_give_one_answer_and_the_same_one_twice(tmp_path: Path) -> None:
    """Determinism is P1, and a mixed tree is the case that tests it.

    A Swift package whose docs site carries a `package.json` is an ordinary
    repository, not a malformed one. Both are reported; the *first* is
    fixed by `_DETECTORS` order rather than by whichever the filesystem
    happened to yield first.
    """
    root = _tree(
        tmp_path / "mixed",
        {"Package.swift": "// x\n", "package.json": '{"scripts": {"test": "vitest"}}'},
        dirs=("Tests",),
    )

    every = detect_test_commands(root)

    assert [item.command for item in every] == [["swift", "test"], ["npm", "test"]]
    assert detect_test_commands(root) == every
    assert _command(root) == ["swift", "test"]


def test_both_surfaces_offer_the_same_detected_default(
    tmp_path: Path, monkeypatch,
) -> None:
    """One setup across surfaces: a per-surface difference is drift.

    The MCP question carries the command in its `default` field, where a
    host pre-fills it. The CLI cannot pre-fill an `input()` by itself, so
    it inserts the same string into the line buffer through `readline` —
    different mechanisms, one value, and the same keystroke meaning on
    both: Enter accepts, clearing the line cancels.
    """
    import maintainability_audit._first_run as first_run
    from maintainability_audit._mcp_setup import test_command_questions

    root = _tree(tmp_path / "pkg", {"Package.swift": "// x\n"}, dirs=("Tests",))

    chat = test_command_questions(root)[0]
    assert chat["default"] == "swift test"
    assert "Package.swift" in chat["prompt"], (
        "the question must say which file proposed the command"
    )

    seen: dict[str, str] = {}

    def _capture(prompt: str, default: str) -> str:
        seen["prompt"], seen["default"] = prompt, default
        return default

    monkeypatch.setattr(first_run, "_input_with_default", _capture)
    monkeypatch.setattr(first_run, "_stdin_is_a_tty", lambda: True)
    config = {
        "test_execution": {"requested": True},
        "expected_commands": {},
        "analyzers": {"prompt_when_interactive": True},
    }
    first_run.maybe_prompt_test_command(root, config)

    assert seen["default"] == chat["default"], (
        f"the CLI offered {seen['default']!r} where chat offered "
        f"{chat['default']!r}; one setup means one default"
    )
    assert config["expected_commands"]["test"] == ["swift", "test"], (
        "accepting the offered default must store it"
    )


def test_a_cleared_line_still_cancels_the_opt_in(tmp_path: Path, monkeypatch) -> None:
    """The pre-filled default must not cost the cancellation.

    Blank has always meant "cancel running the suite". Offering a default
    would break that if Enter were the only way to submit — hence an
    *editable* pre-fill rather than a "press Enter to accept" prompt.
    """
    import maintainability_audit._first_run as first_run

    root = _tree(tmp_path / "pkg", {"Package.swift": "// x\n"}, dirs=("Tests",))
    config = {
        "test_execution": {"requested": True},
        "expected_commands": {},
        "analyzers": {"prompt_when_interactive": True},
    }

    monkeypatch.setattr(first_run, "_input_with_default", lambda *_: "")
    monkeypatch.setattr(first_run, "_stdin_is_a_tty", lambda: True)
    first_run.maybe_prompt_test_command(root, config)

    assert config["test_execution"]["requested"] is False
    assert not config["expected_commands"].get("test")


def test_the_prefill_hook_is_always_removed(monkeypatch) -> None:
    """A startup hook left installed edits the *next* prompt in the session.

    `readline`'s hook is global state, so the `finally` is the whole point
    of the helper; without it, the following question in a setup run would
    arrive with a stale test command typed into it.
    """
    import readline

    from maintainability_audit._first_run import _input_with_default

    # `readline` exposes no getter for the hook, so the setter is spied on:
    # the last call decides what the next prompt inherits.
    calls: list[object] = []
    monkeypatch.setattr(readline, "set_startup_hook", lambda hook=None: calls.append(hook))
    monkeypatch.setattr("builtins.input", lambda _prompt: "typed")

    assert _input_with_default("q: ", "swift test") == "typed"

    assert calls, "the default was never offered to readline at all"
    assert calls[-1] is None, (
        f"a readline startup hook survived the prompt: {calls[-1]!r}; the "
        "next question in this setup would arrive pre-typed"
    )


def test_an_unrecognised_tree_suggests_nothing_and_says_so(tmp_path: Path) -> None:
    """`None` is the common answer, and the question is asked as it was."""
    root = _tree(tmp_path / "plain", {"README.md": "# thing\n", "main.pl": "print 1;\n"})

    assert detect_test_commands(root) == []
    assert suggested_test_command(root) is None


def test_detection_never_writes_the_command_into_the_configuration(tmp_path: Path) -> None:
    """The hard gate reads "a *documented* test command".

    A command this module wrote into the config unasked would satisfy
    `require_test_command` while nobody had documented anything — a gate
    passing on evidence the tool invented about itself. Detection reaches
    exactly one place, the setup question's default, and a human still
    answers it.
    """
    from maintainability_audit.metrics import hard_gate_failures

    root = _tree(tmp_path / "pkg", {"Package.swift": "// x\n"}, dirs=("Tests",))
    config = {
        "thresholds": {},
        "expected_commands": {"test": []},
        "hard_gates": {"require_test_command": True},
    }

    assert suggested_test_command(root) is not None, "precondition: it is detectable"

    failures = hard_gate_failures(root, config, None, [], [], 0)

    assert any("documented test command" in failure for failure in failures), (
        "a detectable command silenced the gate; detection may propose a "
        "default, never satisfy a gate that asks whether a human documented it"
    )
    assert not (root / "maintainability-agent.json").exists(), (
        "detection wrote configuration; it may only propose a default"
    )
