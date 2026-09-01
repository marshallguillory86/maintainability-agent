from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

VERSION = "1.0.1"

PROJECT_URL = "https://github.com/marshallguillory86/maintainability-agent"

# Concern -> competing packages. Empty means "use the shipped list in
# ``idioms.DEFAULT_IDIOM_GROUPS``"; set it to override that list entirely
# with groups meaningful to this repo.
DEFAULT_IDIOM_GROUPS: dict[str, list[str]] = {}

DEFAULT_CONFIG: dict[str, Any] = {
    # Whether the external analyzer pool executes. False here covers
    # only the no-config-file path: unconfigured programmatic callers
    # keep the built-in fallback until D2's first-run setup writes a
    # config. `load_config` flips the default to True the moment a real
    # file loads — a repository that wrote a config chose the product,
    # and ADR 006 says the pool is the product's evidence source.
    "analyzers": {"run": False},
    "paths": {
        "include_extensions": [".py", ".java", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
                               ".html", ".css", ".md"],
        "exclude_patterns": [
            ".git/",
            "node_modules/",
            ".venv/",
            "venv/",
            "dist/",
            "build/",
            "coverage/",
            "__pycache__/",
            # Third-party code the repo did not write. Auditing it
            # measures someone else's decisions and, worse, calibrated
            # references drawn from a corpus containing it describe
            # vendored bundles rather than maintained source. lodash's
            # entry was 41% vendored.
            "vendor/",
            "vendored/",
            "third_party/",
            "third-party/",
            "*.min.js",
            "*.min.css",
            "*.bundle.js",
            # Schema migrations are append-only history. Refactoring one
            # rewrites the past, so a long-but-branchless migration is
            # correct code, not a maintainability finding.
            "migrations/",
            "maintainability-baseline.json",
            "maintainability-report.md",
            "maintainability-remediation-prompt.md",
            "maintainability-pr-comment.md",
            "maintainability.sarif",
        ],
    },
    "thresholds": {
        "max_file_lines": 800,
        "warn_file_lines": 400,
        "max_function_lines": 80,
        "warn_function_lines": 50,
        # Classes are containers, graded on length alone — see
        # ``metrics.class_status``.
        "max_class_lines": 300,
        "warn_class_lines": 200,
        "max_complexity": 15,
        "warn_complexity": 10,
        # Nesting-weighted reading cost. Fitted against 21,300 declarations
        # in the reference corpus: 15 sits near its 94th percentile and 25
        # near its 97th, so these flag the genuinely hard-to-read tail
        # rather than ordinary branching. See ``_cognitive``.
        "max_cognitive_complexity": 25,
        "warn_cognitive_complexity": 15,
        "max_duplicate_blocks": 20,
        "duplicate_block_lines": 8,
    },
    # Hard gates block CI, so every one of them is opt-in. Three used to
    # fire automatically from threshold breaches, which meant a default
    # run failed the gate on every real codebase measured -- 33 to 5,325
    # duplicate blocks against a max of 20, plus file and function
    # breaches. A gate that always fails is not a gate; it is noise that
    # trains people to pass --fail-on-gate and ignore the result.
    "hard_gates": {
        "require_test_command": False,
        "require_readme": True,
        "require_clean_worktree": False,
        # These three previously had no switch and fired whenever a
        # threshold was breached. Default off: a repo opts in to what
        # should block its CI.
        "fail_on_file_failures": False,
        "fail_on_function_failures": False,
        "fail_on_duplicate_blocks": False,
    },
    "expected_files": ["README.md"],
    "expected_commands": {"test": [], "lint": []},
    # Shipped patterns are bug *classes*, each one earned by a defect that
    # actually happened rather than invented from a checklist. The first
    # three come from this project's own failures, which is the only
    # evidence any of them has and is better than none.
    "risk_patterns": [
        {
            "name": "debt-marker",
            "pattern": r"\b(TODO|FIXME|HACK)\b",
            "extensions": [".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
                           ".html", ".css", ".md"],
        },
        {
            # Absence read as a value. `counts.get("x", 0)` cannot
            # distinguish "measured none" from "never measured", and the
            # zero then flows into a rate as though it were evidence.
            #
            # This project shipped that defect at least four times: a
            # repository with one function scored 5.0/A+ because six
            # detectors found nothing; analyzer coverage derived from
            # emitted output made a clean scan read as unexamined; a
            # metric adapter returning no measurements reported success.
            # Every instance was written by someone who knew the rule.
            #
            # Deliberately narrow. `counts.get(k, 0) + 1` is an accumulator
            # and not this defect, and a pattern that flags it produces the
            # nit loop this tool exists to avoid. Matching only a default
            # that is *returned or assigned* dropped the finding count on
            # this repository from 22 to a handful, nearly all real.
            #
            # Still a review prompt rather than a defect assertion, and one
            # of the survivors on this repository is a false positive: a
            # zero used immediately as a skip sentinel. That is the
            # intended precision profile -- the finding says "look here",
            # and looking is cheap.
            "name": "absence-as-zero",
            "pattern": r"(?:return|=)\s*[\w.\[\]\"\']+\.get\([^)]+,\s*0\s*\)\s*$",
            "extensions": [".py"],
        },
        {
            # An assertion that cannot fail. A test built against a path
            # that did not exist compared two identical empty results and
            # passed, which is how a gap survived the test written to
            # catch it. A test that cannot fail is worse than no test: it
            # buys confidence it has not earned.
            "name": "vacuous-assertion",
            "pattern": r"assert\s+(True|1)\s*(?:,|$)|assert\s+(\w+)\s*==\s*\2\b",
            "extensions": [".py"],
        },
        {
            # Output cut without saying so. A reader who believes a
            # truncated list is complete draws conclusions from a
            # fragment. Slicing is fine; silent slicing is not.
            #
            # Only a literal cut on a *returned* collection. Slicing into a
            # local, or with a named limit, is ordinary; silently returning
            # a shortened result to a caller who cannot tell is not.
            "name": "silent-truncation",
            "pattern": r"return\s+[\w.\[\]()]+\[:\s*\d{2,}\s*\]\s*$",
            "extensions": [".py"],
        },
    ],
    "instruction_pack": {
        "project_name": "this repository",
        "strictness": "high",
        "test_policy": "tests for meaningful behavior changes",
        "architecture_notes": [],
    },
}


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
        content = json.loads(path.read_text(encoding="utf-8"))
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
