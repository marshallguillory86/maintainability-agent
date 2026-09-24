# Shell

Functions, in the three forms scripts actually use: POSIX `name() {`,
and bash's `function name {` and `function name() {`. The body may open
on the next line — the brace-on-its-own-line style older scripts favour
— and may be a subshell `name() ( … )` rather than a brace group. Names
are read whole, including the `lib::log` package form the Google style
guide recommends and the hyphens bash allows. `.sh`, `.bash` and `.zsh`
are read; POSIX sh, bash and zsh share the definition and control syntax
this scanner reads.

**Shell is parsed by default, and that is a decision, not a default
left in place.** Shell is in nearly every repository, so turning it on
changes something for most users: their scripts join the graded
population, and the report's list of concerns an independent analyzer
examined narrows, because only jscpd reads shell. Both are the true
statement. The alternative — parse it only on request — would have kept
a scanner written for the file type most repositories contain switched
off for all of them. Decided 2026-09-24.

**Shell is braced, and its text is not what the C-family masker
thinks it is.** The walk is the one C, Java and Swift share; the masker
is shell's own, and it is most of the module.

- **`#` starts a comment only at the start of a word.** `$#` is the
  argument count, `${#list[@]}` a length, `${path#prefix}` a trim.
  Blanking from any of them to the end of the line would hide the `if`
  that tests it.
- **`//` and `/*` are not comments.** `rm -rf "$dir"/*` is ordinary
  shell, and the C masker blanks the rest of that line — or of the file,
  waiting for a `*/`.
- **A heredoc body is text.** Usage messages, generated config and
  embedded scripts contain braces, `fi` and function-shaped lines.
  `<<-` strips leading tabs, so an indented terminator still closes one.
- **A double-quoted string may span lines**, as usage text does.

Quote characters survive masking with their contents blanked, because a
`case` arm is written `"start"|"stop")` and a pattern that could not see
the quotes could not tell an arm from a subshell.

## What counts as a decision

`if`, `elif`, `while`, `until`, `for`, `select`, each `case` arm, `&&`
and `||`. Not counted: the `case` header, whose arms carry it; the `*)`
default arm, as Go declines `default`; `else`; a pipe `|`.

**A keyword counts only in command position** — at the start of a line,
after `;`, `&`, `|`, `(`, `{` or `!`, or after `then`, `do` or `else`.
Shell scripts are full of unquoted prose, and `echo waiting for the
server` has a `for` in it that is an argument, not a loop.

**An AND-OR list decides.** `cmd || exit 1` is the guard clause most
scripts are built from, and `[[ -n $a && -n $b ]]` is a compound
condition. Both operators are counted everywhere.

**Nesting is read from `fi`, `done` and `esac`**, because shell's
control structures have no braces. The brace reader would score a
deeply nested script as flat — Fortran's defect before 1.4.0 in another
language. A construct written on one line, `if [ -f x ]; then rm x;
fi`, opens and closes on that line and leaks no depth. A `case` is
charged once for cognitive complexity, like Kotlin's `when`.

## How it is verified

No second implementation reads shell complexity offline: lizard 1.24.0
has no shell reader, and nothing adapted in the analyzer catalog
measures it. So the branch reader is checked against the grammar itself
— every compound command and list operator in POSIX XCU 2.9.3 and
2.9.4, and the constructs the Bash Reference Manual adds in 3.2.5, one
specimen each in `tests/test_shell_metrics.py`, with a test that fails
if a construct on that list has none. `shellmetrics` computes a
per-function CCN for shell and is the candidate second opinion; it is a
single upstream script outside the pinned pool, and is not installed.

For the same reason **Shell has no external complexity reading.** The
built-in reader is the only one, and the language is named in the
analyzer-floor exemption beside COBOL rather than counted as covered.

## Not anchored

Shell is outside the calibration corpus, so a Shell repository is graded
against medians drawn from other languages and every report says so. It
anchors at the next recalibration, as Kotlin does.

## What it misses

Each of these under-reports rather than invents:

- **A body that is some other compound command** (`f() if …; fi`) is
  legal POSIX and almost never written. It is read as one line.
- **A nested definition is part of its parent**, as a local function is
  in every other language here.
- **Code inside a double-quoted `"$(…)"`** is masked with the string, so
  a decision written inside a quoted command substitution is not counted.
- **A `case` written on one line** counts no arms; the pattern has to
  lead its line.
- **A ternary inside `$(( … ))`** is not counted.
- **A script with no suffix** — known only by its `#!` line — is not
  opened, as with every language here.

One construct over-counts: a line in a multi-line array that ends in
`)` (`  last)`) reads as a `case` arm. It is rare, and it is named here
so a reader who meets it knows it was known.
