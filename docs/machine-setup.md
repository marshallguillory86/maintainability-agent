# Machine setup

**Genre: operational.** What a development machine must have configured
before it commits to this repository. Written 2026-08-28, when a second
machine was needed and the first machine's setup existed only as shell
history.

This is not optional polish. Every item here exists because its absence
already caused a defect.

## Why this page exists

A commit identity set once in `~/.gitconfig` and never revisited can
silently take over when a repository-local override stops applying.
Nothing errors, and a wrong identity that reaches a protected branch
cannot be corrected without a history rewrite and a force-push.

**An identity nobody verified is an identity nobody can trust**, and the
check is cheap only before the commits exist.

## 1. Commit identity

The git identity is the GitHub noreply address:

```bash
git config --global user.name  "Marshall Guillory"
git config --global user.email "152444602+marshallguillory86@users.noreply.github.com"
```

The noreply address is verified by construction, keeps a real address
out of public commit metadata, and is already what GitHub stamps on
squash merges here. Any other address is a decision that needs
justifying.

**Then turn on the control that makes this unnecessary to remember:**

> GitHub → Settings → Emails → **Block command line pushes that expose my email**

GitHub then rejects a push carrying any other address. It is a UI setting
with no API equivalent, and it is per-account rather than per-machine — but confirm
it, because it is the only control here that cannot fail open.

**Verify rather than assume:**

```bash
git config --global user.email
git -C <this-repo> config user.email
```

Check the second one too. A repository-local override can hide a wrong
global value.

## 2. Commit signing

`main` has `required_signatures` enabled, so an unsigned commit reaching
it is rejected. SSH signing, not GPG — `gpg` is not installed on these
machines.

```bash
ssh-keygen -t ed25519 -C "signing key (marshall)" -f ~/.ssh/id_ed25519_signing
ssh-add --apple-use-keychain ~/.ssh/id_ed25519_signing

git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519_signing.pub
git config --global commit.gpgsign true
git config --global tag.gpgsign true
```

Choose a passphrase and store it in the password manager before
confirming it. The Keychain holds it afterwards, so it is typed once per
machine.

**Local verification needs an allowed-signers file**, or `git log`
reports `N` on a perfectly good signature:

```bash
printf '%s %s\n' "152444602+marshallguillory86@users.noreply.github.com" \
  "$(cat ~/.ssh/id_ed25519_signing.pub)" >> ~/.ssh/allowed_signers
git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
```

**Survive a reboot.** Without this the key leaves the agent on restart
and the next commit blocks on a passphrase prompt — which, with
`commit.gpgsign` on, means every commit on the machine:

```bash
cat >> ~/.ssh/config <<'EOF'

Host *
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519_signing
EOF
chmod 600 ~/.ssh/config
```

**Register the key on GitHub as a *signing* key.** A signing key and an
authentication key are different objects, and the wrong type verifies
nothing:

```bash
gh auth refresh -h github.com -s admin:ssh_signing_key
gh ssh-key add ~/.ssh/id_ed25519_signing.pub --type signing --title "<machine> signing key"
```

Give each machine its own key and its own title. One key copied between
machines cannot tell you which machine signed.

**Prove it before relying on it:**

```bash
git commit --allow-empty -m "chore: signing probe"
git log -1 --format='%G?'
git reset --hard HEAD~1
```

`G` is a good signature. `N` means unsigned; `U` means untrusted, most
often a missing `allowed_signers` entry. Do not skip this: unverified
setup is the thing this page exists to prevent.

## 3. Toolchain

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

Install `secure-code-agent` alongside — it is not a dependency of this
package, and every audit runs it for the security pillar (D177):

```bash
python3 -m pip install 'secure-code-agent>=0.12.2'
```

Check the published release first (`gh release list --repo
marshallguillory86/secure-code-agent`); this project's CI pin is not the
source of truth for what is current. What it measures depends on the scanners it can find.
With none of them installed it runs only its built-in rules, reports coverage
as partial, and the pillar reads `unverified: not graded`. See what it can
resolve with:

```bash
secure-code-agent --preflight .
```

and install what it names. On macOS:

```bash
python3 -m pip install bandit
brew install gitleaks osv-scanner trivy semgrep checkov
```

**Do not install secure-code-agent's scanner extras into this environment**
(`secure-code-agent[required-scanners]` or `[python-scanners]`). They pull in
semgrep, and njsscan pulls it in too; semgrep pins `mcp<2`, and pip replaces
this package's `mcp` 2.x to satisfy it. The chat door then fails to start
(D178). `pip check` does not warn, because this package's `mcp` requirement
lives in an optional extra it never inspects. semgrep from Homebrew has its
own environment and no such conflict. njsscan has no Homebrew formula and
cannot share this environment; give it one of its own, and link its command
onto a directory every host's `PATH` includes.

The same applies to **secure-code-agent's own `[mcp]` extra**: it pins
`mcp>=1.0,<2`, and this package's chat door needs `mcp>=2,<3`, so the two MCP
servers cannot share one environment. Install `secure-code-agent` here without
extras; it runs as a child of the audit and needs none.

Two things decide whether a scanner resolves, both found setting up the
second machine. **semgrep and checkov have no `python -m` fallback**, so they
must be on the `PATH` the host launches the audit with — an MCP host such as
the ChatGPT app may not include a virtualenv's `bin`, which is why they come
from Homebrew here rather than pip. And **secure-code-agent refuses an
executable inside the tree it is auditing**, so a virtualenv inside a
repository cannot supply scanners for that repository's own audit.

The analyzer pool installs through the checked-in constraints, which are
the Linux-resolved closure the gates run against (D89). A macOS machine
may resolve differently; that is expected, and it is why the constraints
file is generated on a runner rather than on a laptop.

## 4. Before the first push from a new machine

Run the gate as its own command, never chained to a commit:

```bash
python3 -m ruff check src tests tools
python3 -m pytest -q --cov=maintainability_audit --cov-fail-under=92
```

Then confirm the identity actually took effect on a real commit, because
configuration that was set is not the same as configuration that
applied:

```bash
git log -1 --format='%ae | %G?'
```

Expect the noreply address and `G`. Anything else means
one of the sections above did not land on this machine.
