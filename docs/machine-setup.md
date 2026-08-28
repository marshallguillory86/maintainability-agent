# Machine setup

**Genre: operational.** What a development machine must have configured
before it commits to this repository. Written 2026-08-28, when a second
machine was needed and the first machine's setup existed only as shell
history.

This is not optional polish. Every item here exists because its absence
already caused a defect.

## Why this page exists

For three days, 37 commits were authored as `mguillory@agilerising.com`
— a work address, on a personal open-source repository, attributing the
work to a company that did not do it. Nobody noticed, because nothing
checked. The address came from `~/.gitconfig`, set months earlier and
never revisited; a repository-local override had been masking it, and
when that override stopped applying the commits silently fell through to
the global value.

Removing it needed a history rewrite, a force-push through two layers of
branch protection, and a support ticket for the objects GitHub retains
after a force-push. The fix cost more than the work it corrected.

The related failure is D100 in the [defect
register](defect-register-chat-surface.md): the package promoted itself
to a 1.0 release candidate, and asked who had decided that, the record
could only guess — every agent here commits under one git identity, so
`git log` settles nothing.

Both are the same shape. **An identity nobody verified is an identity
nobody can trust**, and the check is cheap only before the commits
exist.

## 1. Commit identity

The git identity is the GitHub noreply address. Not a personal address,
not a work address:

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

GitHub then rejects a push carrying any other address. It would have
refused all 37 commits at the first push. It is a UI setting with no API
equivalent, and it is per-account rather than per-machine — but confirm
it, because it is the only control here that cannot fail open.

**Verify rather than assume:**

```bash
git config --global user.email
git -C <this-repo> config user.email
```

Check the second one too. A repository-local override is what hid the
problem last time.

## 2. Commit signing

`main` has `required_signatures` enabled, so an unsigned commit reaching
it is rejected. SSH signing, not GPG — `gpg` is not installed on these
machines and agents do not install tools.

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
git commit --allow-empty -m "chore: signing probe" -m "Agent: marshall"
git log -1 --format='%G?'
git reset --hard HEAD~1
```

`G` is a good signature. `N` means unsigned; `U` means untrusted, most
often a missing `allowed_signers` entry. Do not skip this: unverified
setup is the thing this page exists to prevent.

## 3. Authorship declaration

Every commit carries an `Agent:` trailer naming who wrote it — one of
`claude`, `codex`, `grok`, `marshall`:

```
Agent: claude
```

CI enforces it over every non-merge commit in a pull request, and fails
on an empty range rather than passing on nothing. Every defect-register
entry from D89 forward carries a `*Roles:*` line for the same reason.

**A trailer is a declaration, not a proof.** A commit naming the wrong
agent passes. Signing proves the *key*, and every agent on a machine
shares that machine's key, so together they establish "this machine
asserts claude wrote it" and no more. `RULES.md` states that limit;
do not let a document upgrade it to "provable".

## 4. Toolchain

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

The analyzer pool installs through the checked-in constraints, which are
the Linux-resolved closure the gates run against (D89). A macOS machine
may resolve differently; that is expected, and it is why the constraints
file is generated on a runner rather than on a laptop.

## 5. Before the first push from a new machine

Run the gate as its own command, never chained to a commit:

```bash
python3 -m ruff check src tests tools
python3 -m pytest -q --cov=maintainability_audit --cov-fail-under=92
```

Then confirm the identity actually took effect on a real commit, because
configuration that was set is not the same as configuration that
applied:

```bash
git log -1 --format='%ae | %G? | %(trailers:key=Agent,valueonly)'
```

Expect the noreply address, `G`, and an agent name. Anything else means
one of the sections above did not land on this machine.
