"""The PATH a scrubbed git fixture must hand its child.

Seven fixtures pinned `PATH=/usr/bin:/bin` to keep a developer's shims
and wrappers out of the child process. On this project's own macOS
development machine that pin *is* a shim: `/usr/bin/git` is Xcode's
stub, and with Command Line Tools unavailable every one of those
fixtures dies with `xcrun: error: invalid active developer path` before
git runs at all.

That is the whole local baseline. 101 failures and 191 errors, diffed
run after run as "known", every one of them this line -- which means a
real regression landing in any of those seven files had 292 places to
hide. The baseline was not evidence of anything about the product.

It also blocks the platform claim. `Operating System :: POSIX` covers
macOS, CI has only ever run Linux, and the reason a macOS runner was
never added is that the suite could not pass on the one macOS machine
anyone tried it on -- for a reason that has nothing to do with macOS.

The environment stays scrubbed: this changes which directory PATH names,
not how much of the environment the child inherits.
"""

from __future__ import annotations

import shutil
from pathlib import Path

_GIT = shutil.which("git")

#: Directory holding the `git` this machine actually runs, or the
#: historical pin when git is not on PATH at all -- in which case the
#: fixture fails on a missing git, which is the honest message.
GIT_PATH = str(Path(_GIT).parent) if _GIT else "/usr/bin:/bin"
