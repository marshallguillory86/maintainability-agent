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
after `;`, `&`, `|`, `(`, `{`, `!` or a backtick, or after `then`, `do` or `else`
when that word is itself in command position — so `echo do for it` counts
nothing.
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

No second implementation in the pinned analyzer pool reads shell
complexity: lizard 1.24.0 has no shell reader, and nothing adapted in the
analyzer catalog measures it. One exists upstream — `shellmetrics`, a
single script computing a per-function CCN — and it cannot be adopted on
this project's terms: checked 2026-09-27, it has no release and no tag, no
package on Homebrew, pip or npm, and no change since 2023, so it could not be
pinned the way every analyzer in the pool is. That is the honest gap: not "no
tool exists", but "none this project can pin".

So the branch reader is checked against the grammar instead: the list
operators of POSIX XCU 2.9.3 (AND-OR, sequential and asynchronous), the
compound commands of 2.9.4, and the constructs the Bash Reference Manual
adds in 3.2.5, including the `;&` and `;;&` case terminators — one specimen
each in `tests/test_shell_metrics.py`. The list is typed from the
standard's section headings, and the test checks the specimens against
that list, not against the standard itself: a construct left off the list
would go unnoticed, which is why the list is short enough to read.

For the same reason **Shell has no external complexity reading.** The
built-in reader is the only one, and the language is named in the
analyzer-floor exemption beside COBOL rather than counted as covered.

## Anchored, thinly

Shell is **in the reference corpus since 4.0.0**, beside Kotlin, and its
grade is no longer provisional. It entered thin: of sixteen candidates at
the standard 3,000-star bar, ten were collections, configuration or too
small to be codebases, and six cleared verification — ohmyzsh, pi-hole,
powerlevel10k, acme.sh, pyenv and iTerm2-Color-Schemes. That is disclosed
rather than padded by hand-picking. The medians are shared across
languages, so six Shell repositories add to one reference rather than
defining their own.

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

Some lines over-count, all through the `case`-arm pattern, which reads
one line at a time and cannot see whether a `case` is open: a line in a
multi-line array ending in `)` (`  last)` or `  "last")`), a one-word
subshell (`(cleanup)`), and the last line of a multi-line command
substitution (`  --bar)`). Each reads as one arm. They are named here so a
reader who meets one knows it was known.

Fixed after 3.9.0 shipped, both found by an audit: `<<` inside `$(( … ))`
or `(( … ))` was read as a heredoc, which blanked every function after it —
a population lost, not under-reported — and a keyword after `do` in an
argument list (`echo do for it`) counted as a branch.
