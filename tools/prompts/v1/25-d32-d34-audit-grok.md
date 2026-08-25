# Grok — hostile audit of D32, D33, D34

Cycle header: **audit of D32/D33/D34 on PRs #95, #96, #97**, base `main`
at `21fcc13`.

You are Grok. **Report-only.** Do not implement, do not repair, do not
open or merge PRs, do not pull main, do not advance any branch, do not
start the next slice. Check the work against the register entries and
the tests, never against the wrap-up. `.grok/config.toml` records this
seat; note that it is **inert unless the folder is trusted** — the
enforcement lives in the `grok-audit` launcher. Behave as if enforced
either way.

## What to audit

    git fetch origin
    git switch --detach origin/fix/d33-declared-refusals   # D33, merge first
    git switch --detach origin/fix/d34-shipped-skill-carries-the-rule
    git switch --detach origin/fix/d32-call-first-on-every-surface

Three entries were added to `docs/defect-register-chat-surface.md`. Each
claims a closing test. Your job is to break the claims, not confirm them.

## The claims, stated so you can attack them

**D33 — a refusal is declared, not a crash.** `mcp` 2.1.0 distinguishes
an anticipated failure (message reaches the caller) from a crash
(`Error executing tool <name>`, traceback server-side). The allowed-roots
boundary was raised as a bare `PathNotAllowed`, so it was classified as a
crash and its text withheld, deleting D10's requirement that a refusal
name `--allow-root` and `MAINTAINABILITY_MCP_ALLOWED_ROOTS`. Both MCP
seams now declare their refusals; the plain functions still raise the
domain types. **The dependency range was deliberately not narrowed.**

**D34 — the shipped skill is asserted, not assumed.** Two existing tests
read `_skill_data/SKILL.md` from the source checkout, so the copy in the
built distribution was asserted by nothing. The staged build must now
carry it, byte-identical to the reviewed skill, with D21's rule in it.

**D32 — the call-first rule reaches every chat door.** `SERVER_INSTRUCTIONS`
carried no ordering rule and the MCP prompt taught the opposite one.
**This entry was opened on a wrong diagnosis and corrected the same day**
— it is not the cause of the field report that prompted it.

## Specific attacks worth trying

1. **The tuple was broad, and that was a real leak — already fixed, so
   attack the fix instead.** `ANTICIPATED_REFUSALS` began as
   `(ValueError, PathNotAllowed, SetupRequired)`; modules below the
   transport raise bare `ValueError` with internal paths in the message,
   and on 2.1.0 those reached the caller as declared refusals. It is now
   `(InvalidAuditArgument, PathNotAllowed, SetupRequired)`, held by
   `test_a_failure_from_below_the_transport_stays_a_crash`. Find what
   that narrowing missed: a deliberate seam refusal that is now
   *silently* a crash and no longer teaches its remedy (the opposite
   error), or another anticipated type reachable at the transport —
   check `_mcp_grants`, `_mcp_gate`, `_mcp_setup` and the elicitation
   paths, not just `_mcp_audit`. `PathNotAllowed` subclasses
   `ValueError`; confirm nothing else in the tree does and relies on it.
2. **D33's falsifier may be version-lucky.** It excludes
   `UnexpectedResourceError` via a guarded import that degrades to an
   empty tuple on 2.0.0. Show a 2.x where the test passes while a
   refusal still reaches the caller as a crash.
3. **D33 changed two existing assertions.** They asserted
   `pytest.raises(PathNotAllowed)` through `read_resource` and now assert
   `ResourceError` plus message plus `__cause__`. The entry argues this
   is strengthening, not laundering. Test that argument. Is there any
   property the old assertions caught that the new ones do not?
4. **D34's own entry admits one assertion cannot fail.** Removing
   `_skill_data/**/*` from `package-data` leaves the files staged. Verify
   that admission is accurate and find whether the *remaining* two
   assertions are also weaker than claimed — in particular whether
   byte-pinning the staged copy against the source can pass while the
   installed copy on a user's disk differs.
5. **D32's corrected entry.** Confirm the correction is complete: the
   entry, the closing test's docstring, the changelog, and the PR body
   should all now say "found by inspection". Any surviving causation
   claim is the defect.
6. **The register's own rules.** Every closing citation must name a test
   that exists in the file the entry names
   (`test_every_closing_citation_names_a_test_that_exists`). Three new
   entries, three chances to get that wrong.
7. **Cross-entry.** D32 and D34 both touch the skill. Do they contradict
   each other about which surface failed in the field?

## What the fix did to the product's own gate

D33 crossed two thresholds and was split rather than having them raised:
`_audit_tool_for` was carved out of `_bind_audit_tool` at 82 lines, and
the file came back under 500 by cutting *prose*, not code. Check that
the prose that was cut is genuinely redundant with the register entry
and that nothing a reader needs at the seam was lost to make a number.

## Environment — do not report these as defects

This machine is a MacBook Pro that has never cut a release, and its
tooling is stale in ways that will mislead you:

- ~292 tests fail locally with `git init` exit 1. Command Line Tools are
  an empty husk (`/Library/Developer/CommandLineTools` has no
  `usr/bin`) and the fixtures pin `PATH=/usr/bin:/bin`. Identical on
  `main`. **Not a regression. Do not chase it.**
- The analyzer pool is almost entirely missing, so any local audit
  measures the built-in fallback.
- The `maintainability-agent` on `PATH` is a released 0.9.1, not the
  checkout. The `.venv` is editable onto the tree; use it.
- Local `mcp` is 2.0.0; CI resolves 2.1.0. The D33 claim is about both.
  A scratch venv on 2.1.0 is the honest way to check:
  `python3 -m venv /tmp/mcp21 && /tmp/mcp21/bin/pip install "mcp==2.1.0" pytest jsonschema -e .`

Allowed: `python3 -m pytest`, `pytest`, and git's read-only verbs.

## What a finding must carry

A file and line, the property violated, and the command that reproduces
it. "This looks fragile" is not a finding. If you cannot reproduce it,
say so and say what would.

If you defeat a claim I cannot fix, say that too — D31's third defeat is
recorded rather than fixed, and that is the honest outcome when the
check cannot be made mechanical.

Report back with: confirmed defects, attacks that failed (so the next
audit does not repeat them), and anything in the three entries that
claims more than its test proves.
