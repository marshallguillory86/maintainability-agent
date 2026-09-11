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
hooks_dir="$repo_root/.git/hooks"
source_dir="$repo_root/tools/hooks"

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
