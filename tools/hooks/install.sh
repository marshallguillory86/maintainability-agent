#!/usr/bin/env bash
# Link this repository's hooks into .git/hooks.
#
# Symlinks rather than copies, so a hook edited here takes effect without
# anyone remembering to reinstall it -- the same class of staleness the
# hooks exist to prevent.
#
# The global pre-commit hook (identity guard + gitleaks) is installed
# separately through `init.templateDir` and is left alone: this script
# only adds what it owns, and refuses to overwrite a hook it did not
# write.

set -eu

repo_root=$(git rev-parse --show-toplevel)
source_dir="$repo_root/tools/hooks"

# Git's own answer, not a guess at where `.git` is. This was
# "$repo_root/.git/hooks", which is wrong in a linked worktree: there
# `.git` is a *file* pointing at the main repository, so the installer
# created a directory that nothing reads and reported success. It also
# ignored `core.hooksPath` entirely, so a machine that had configured
# one got its hooks installed somewhere Git would never look.
#
# `--git-path hooks` honours both, and returns a path relative to the
# worktree when that is what Git means, so resolve it from there.
hooks_dir=$(cd "$repo_root" && cd "$(dirname "$(git rev-parse --git-path hooks)")" \
            && printf '%s/%s' "$(pwd)" "$(basename "$(git rev-parse --git-path hooks)")")

mkdir -p "$hooks_dir"

for hook in commit-msg; do
  target="$hooks_dir/$hook"
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "install.sh: $target exists and is not a symlink; left alone." >&2
    echo "  Move it aside and re-run if you want the repository's version." >&2
    continue
  fi
  ln -sfn "$source_dir/$hook" "$target"
  echo "installed $hook -> tools/hooks/$hook"
done
