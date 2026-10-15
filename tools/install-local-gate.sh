#!/usr/bin/env bash
# Install tools/local-gate.sh as this repository's pre-push hook. Run once
# per clone. A pre-push hook this script did not write is left alone and
# reported, never replaced.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

MARK="# maintainability-agent local gate (tools/install-local-gate.sh)"
hooks="$(git rev-parse --git-path hooks)"
mkdir -p "$hooks"
hook="$hooks/pre-push"

if [[ -e "$hook" ]] && ! grep -qF "$MARK" "$hook"; then
  echo "install-local-gate: $hook exists and was not written by this script; add 'tools/local-gate.sh' to it yourself" >&2
  exit 1
fi

cat > "$hook" <<EOF
#!/usr/bin/env bash
$MARK
set -euo pipefail
exec "\$(git rev-parse --show-toplevel)/tools/local-gate.sh"
EOF
chmod +x "$hook"
echo "installed $hook"
