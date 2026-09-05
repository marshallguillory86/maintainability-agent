from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

from ._config_defaults import DEFAULT_CONFIG, DEFAULT_IDIOM_GROUPS

# Re-exported: the defaults live in `_config_defaults`, this module is
# still the door every caller comes through.
__all__ = ["DEFAULT_CONFIG", "DEFAULT_IDIOM_GROUPS", "PROJECT_URL", "VERSION"]

VERSION = "2.8.1"

PROJECT_URL = "https://github.com/marshallguillory86/maintainability-agent"



class ConfigUnreadable(ValueError):
    """A configuration file exists but cannot be understood.

    Distinct from absence on purpose: absent means "ask the setup
    questions", unreadable means "a person has to look at this file".
    Conflating them would either re-ask someone who has already
    answered, or silently audit against defaults they did not choose.
    """


class PathNotAllowed(ValueError):
    """A configured path escaped the repository it belongs to.

    The boundary is not advisory: `paths.history` and its siblings come
    from a file inside the repository under audit, so a traversal, an
    absolute path, or a symlink pointing outward is a repository asking
    this tool to write somewhere it was never authorized to touch. An
    audit reproduced exactly that through the MCP seam (D20).
    """


def repository_path(root: Path, configured: str | None, default: str) -> Path:
    """A configured repository-scoped path, resolved and bounded.

    Every read, existence check, mkdir and append of a configured path
    goes through here. `resolve()` follows symlinks and collapses `..`
    first, so traversal and symlink escapes are one comparison.
    """
    root = Path(root).resolve()
    candidate = Path(configured or default).expanduser()
    base = candidate if candidate.is_absolute() else root / candidate
    target = base.resolve()
    if target != root and not target.is_relative_to(root):
        # The configured spelling, never what it resolved to: a symlinked
        # `history.jsonl` once published its target to the chat host.
        # Fifth in the D72/D82/D91 family (D96).
        raise PathNotAllowed(
            f"configured path {configured or default!r} resolves outside "
            "the repository it configures"
        )
    # An inward `.maintainability -> src` link passes the boundary check on
    # the resolved path; it shows only on the lexical route (D34).
    _refuse_symlinked_route(root, base)
    return target


def _refuse_symlinked_route(root: Path, base: Path) -> None:
    """No component between root and target may be a symlink, on the
    lexical path (D34). The stop compares *real* paths so a ``/var`` root
    against a ``/private/var`` target does not skip the walk (63ab820).
    """
    root_real = os.path.realpath(root)
    current = Path(os.path.normpath(base))
    while os.path.realpath(current) != root_real:
        if current.is_symlink():
            raise PathNotAllowed(
                f"{current} is a symlink; the audited tree cannot redirect "
                "where this agent reads or writes.")
        if current.parent == current:
            return  # filesystem root reached without meeting the grant
        current = current.parent


def deep_update(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value


CONFIG_FILENAME = "maintainability-agent.json"


def discovered_config(root: Path) -> str | None:
    """The repository's own config, when a caller did not name one.

    A tool that sits next to its configuration and silently ignores it is
    a trap: this project audited itself for a session against built-in
    defaults rather than its own exclusions, and the difference was 422
    findings versus 162 -- most of the excess from a generated data file
    the config had excluded all along.

    Lives here rather than in `cli` because every entry point needs it.
    Fixed in the CLI first, and the MCP server then returned 405 findings
    where the CLI returned 162 on the same repository, which is what a
    fix living in one caller looks like from the outside.
    """
    candidate = root / CONFIG_FILENAME
    # Refuse a symlink: `is_file()` follows one out of the grant (D36/e88b429).
    if candidate.is_symlink() or not candidate.is_file():
        return None
    return str(candidate)


def acquisition_permitted() -> bool:
    """Whether *this user* has enabled tool acquisition (D35).

    Read from the XDG user tier alone, never from the merged config,
    and that is the whole point. `load_config` states that a repository
    always beats a person, which is right for thresholds and
    exclusions — the repository knows its own code. It is exactly wrong
    for acquisition: `product-intent.md` P1 says a **user** enables
    `analyzers.acquire_tools`, and an audit showed that four words in a
    pull request otherwise make the host run `npx --yes` on an unpinned
    package, honouring the tree's own `.npmrc`.

    License policy already works this way — deny wins, and no
    repository can override an organisation's prohibition. Acquisition
    is the same shape of decision and was the only one taking the
    audited tree's word for it.

    A repository that sets the key is ignored rather than refused: it
    is a preference the tool declines to act on, not an attack worth
    failing a scan over, and the environment work order already tells
    the user which tools are missing and how to install them.
    """
    from ._user_config import user_config_answers

    answers = user_config_answers() or {}
    analyzers = answers.get("analyzers")
    if not isinstance(analyzers, dict):
        return False
    return bool(analyzers.get("acquire_tools", False))


def analyzers_run_default(config: dict[str, Any]) -> bool:
    """The repository's standing pool decision — one reading, every seam.

    `build_report`, the CLI and the MCP server all resolve their
    tri-state through this, so "the config decides" cannot quietly mean
    three different things (D1).
    """
    return bool((config.get("analyzers") or {}).get("run", False))


def load_config(path: str | None) -> dict[str, Any]:
    """Defaults, then the user tier, then the repository file (D13).

    Later tiers win through `deep_update`: a repository always beats a
    person, a person always beats the shipped defaults. Any loaded tier
    defaults the pool on (D1 — whoever wrote a config chose the
    product), set before the merges so an explicit ``"run": false`` at
    the winning tier still wins.
    """
    from ._user_config import user_config_answers

    config = json.loads(json.dumps(DEFAULT_CONFIG))
    # Grant-only user configs read as absent: a standing D10 root grant
    # is not a setup answer and must not flip the pool default on.
    user_tier = user_config_answers()
    if user_tier is None and not path:
        return config
    config["analyzers"]["run"] = True
    if user_tier is not None:
        deep_update(config, user_tier)
    if path:
        deep_update(config, _configured(Path(path)))
    return config


def _shaped_like_the_defaults(candidate: dict[str, Any], where: str) -> None:
    """Refuse a known key whose value is the wrong shape.

    Syntax was the only thing checked: a file could parse, have an
    object root, and still say `"thresholds": "nope"`. That merged
    cleanly and surfaced later as a raw `TypeError: string indices must
    be integers` from somewhere in scoring, and `"hard_gates": []` as an
    `AttributeError` on a list — two stack traces for one broken file,
    neither of them naming it.

    Derived from `DEFAULT_CONFIG` rather than a hand-written table, so a
    key added there is checked the day it is added. Unknown keys are
    still permitted: this is a shape check, not a schema, and refusing
    what it does not recognise would break every config written against
    a newer version of this tool.
    """
    for key, default in DEFAULT_CONFIG.items():
        if key not in candidate:
            continue
        value = candidate[key]
        if isinstance(default, dict) and not isinstance(value, dict):
            raise ConfigUnreadable(
                f"{where}: {key!r} must be an object, not "
                f"{type(value).__name__}. Repair or delete it."
            )
        if isinstance(default, list) and not isinstance(value, list):
            raise ConfigUnreadable(
                f"{where}: {key!r} must be a list, not "
                f"{type(value).__name__}. Repair or delete it."
            )
        _shaped_inside(key, default, value, where)


def _kinds_for(fallback: Any) -> tuple[type, ...]:
    """What a nested value must be, read off the shipped default.

    Empty when the default is something this check has no opinion about,
    which the caller treats as "leave it alone" -- a shape check, not a
    schema. `bool` is listed before the numbers deliberately: it is a
    subclass of `int`, so order decides whether `true` passes for a
    threshold, and the caller re-checks it for that reason.
    """
    if isinstance(fallback, bool):
        return (bool,)
    if isinstance(fallback, (int, float)):
        return (int, float)
    for kind in (str, list, dict):
        if isinstance(fallback, kind):
            return (kind,)
    return ()


def _shaped_members(
    key: str, default: dict[str, Any], value: dict[str, Any], where: str
) -> None:
    """Each known nested key, by the type its default carries."""
    for name, fallback in default.items():
        if name not in value or name == "_doc":
            continue
        expected = _kinds_for(fallback)
        if not expected:
            continue
        actual = value[name]
        # `bool` is a subclass of `int`, so a bare isinstance check would
        # accept `true` for a threshold that wants a number.
        wrong_bool = isinstance(actual, bool) and bool not in expected
        if wrong_bool or not isinstance(actual, expected):
            raise ConfigUnreadable(
                f"{where}: {key}.{name} must be "
                f"{' or '.join(kind.__name__ for kind in expected)}, not "
                f"{type(actual).__name__}. Repair or delete it."
            )
        # And the members, not only the container: the list branch in
        # `_shaped_inside` only ever ran for a *top-level* list, so
        # `{"paths": {"include_extensions": [1]}}` was accepted and the
        # audit reported a clean scan of nothing (D84).
        _shaped_inside(f"{key}.{name}", fallback, actual, where)


def _shaped_inside(
    key: str, default: Any, value: Any, where: str
) -> None:
    """The same check one level down, where the crashes actually were.

    The first version stopped at the top level, so `{"thresholds":
    "nope"}` was refused while `{"thresholds": {"max_file_lines": "a"}}`
    reached scoring and raised a raw `TypeError`, `{"expected_files":
    [1]}` raised one from the path join, and
    `{"hard_gates": {"require_readme": []}}` was accepted and *silently
    disabled the gate*, because an empty list is falsy. That last one is
    the worst of the three: no error, and a required check quietly
    stopped being required.

    Types come from `DEFAULT_CONFIG` again rather than a table. Unknown
    nested keys stay permitted for the same reason unknown top-level
    keys are: this is a shape check, not a schema.
    """
    if isinstance(default, dict) and isinstance(value, dict):
        _shaped_members(key, default, value, where)
    elif isinstance(default, list) and isinstance(value, list):
        kinds = {type(item) for item in default} or {str}
        for index, item in enumerate(value):
            if not isinstance(item, tuple(kinds)):
                raise ConfigUnreadable(
                    f"{where}: {key}[{index}] must be "
                    f"{' or '.join(kind.__name__ for kind in kinds)}, not "
                    f"{type(item).__name__}. Repair or delete it."
                )


#: An operator-named file is still read into memory, so its size is
#: bounded. Generous by two orders of magnitude for a config or a
#: baseline; the point is that *some* number exists.
MAX_OPERATOR_FILE_BYTES = 8 * 1024 * 1024


def read_operator_file(path: Path) -> str:
    """Read a file the operator named, after checking it is one.

    `--config` and `--baseline` take a path from the command line and
    read it. Every other path in this project goes through
    `repository_path`, which bounds it to the audited tree — but these
    two legitimately point outside it, so bounding is the wrong control
    and *no* control was the shipped answer (SonarCloud S8707, found
    2026-09-05: "LLMs running this code with faulty CLI arguments can
    escape file system restrictions").

    What is checked is what a path cannot promise on its own:

    - **It is a regular file.** `read_text` on a FIFO blocks forever and
      on `/dev/zero` consumes memory until the process dies. An agent
      driving this CLI with an attacker-influenced argument is the case
      the rule names, and "denial-of-service via crafted config files" is
      in this project's own published scope.
    - **It is not larger than `MAX_OPERATOR_FILE_BYTES`.** A regular file
      can still be enormous.

    Deliberately *not* checked: whether the path is a symlink. The
    operator named it and controls it, and a symlinked config is an
    ordinary setup. The audited tree's own default path is a different
    question and `discovered_config` already refuses a symlink there.
    """
    import stat as stat_module

    # Opened once, then checked and read **through that handle** — the
    # same discipline `_safe_write` uses for writes, and for the same
    # reason. Checking `os.stat(path)` and then calling `path.read_text()`
    # resolves the name twice, so what was measured and what is read can
    # differ: the classic time-of-check/time-of-use gap.
    #
    # `O_NONBLOCK` is what makes the check possible at all. Opening a FIFO
    # for reading otherwise blocks until a writer appears, so the process
    # would hang *before* reaching any validation — the very failure this
    # function exists to prevent.
    handle = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        info = os.fstat(handle)
        if not stat_module.S_ISREG(info.st_mode):
            raise PathNotAllowed(
                f"{path} is not a regular file. This reads configuration "
                "and baselines; a device, socket or FIFO named here would "
                "block or exhaust memory rather than parse."
            )
        if info.st_size > MAX_OPERATOR_FILE_BYTES:
            raise PathNotAllowed(
                f"{path} is {info.st_size} bytes, over the "
                f"{MAX_OPERATOR_FILE_BYTES}-byte limit for a file named on "
                "the command line."
            )
        with os.fdopen(handle, "r", encoding="utf-8", closefd=False) as opened:
            return opened.read(MAX_OPERATOR_FILE_BYTES + 1)
    finally:
        os.close(handle)


def _configured(path: Path) -> dict[str, Any]:
    """The repository's own file, or a refusal that names it.

    Every door loads through here, so every door answers a broken
    config the same way. An audit found three answers to one state: the
    MCP tool and resource refused by name, while the CLI and any caller
    passing `config_path` let a raw `JSONDecodeError` out — the latter
    bypassing the setup gate entirely, since supplying a config is how
    a caller says the question is already answered (D32).
    """
    try:
        content = json.loads(read_operator_file(path))
    except (OSError, ValueError) as unreadable:
        # `strerror` for an OSError, never `str(unreadable)`: the latter
        # appends the OS filename, and when `read_text` followed a
        # symlink that filename is the *target* — a path outside the
        # repository, which the caller never named, travelling inside a
        # declared MCP refusal. A JSONDecodeError carries only a
        # position, so its text is safe to pass on.
        detail = getattr(unreadable, "strerror", None) or (
            str(unreadable) if isinstance(unreadable, ValueError) else
            type(unreadable).__name__
        )
        raise ConfigUnreadable(
            f"{path} cannot be read as JSON ({detail}). Repair or "
            "delete it; the audit cannot tell how this repository is "
            "configured."
        ) from unreadable
    if not isinstance(content, dict):
        raise ConfigUnreadable(
            f"{path} is not a JSON object; a configuration cannot be "
            f"read from {type(content).__name__}."
        )
    _shaped_like_the_defaults(content, str(path))
    _repository_relative(content, str(path))
    return content


def _repository_relative(candidate: dict[str, Any], where: str) -> None:
    """`expected_files` names files in the repository, not on the host.

    `paths.history` was bounded by D20 and this was not, so a config
    could say `/etc/passwd` or `../outside` and the audit would report
    whether that existed — a repository-controlled probe of the machine
    running it, answered in the report.
    """
    entries = candidate.get("expected_files")
    if not isinstance(entries, list):
        return
    for entry in entries:
        text = str(entry)
        if PurePosixPath(text).is_absolute() or Path(text).is_absolute():
            raise ConfigUnreadable(
                f"{where}: expected_files entry {text!r} is absolute; "
                "these name files inside the repository."
            )
        if ".." in Path(text).parts:
            raise ConfigUnreadable(
                f"{where}: expected_files entry {text!r} leaves the "
                "repository; these name files inside it."
            )
