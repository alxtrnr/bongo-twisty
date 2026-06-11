# BongoTwisty — Development Workflow

A reference for day-to-day blog work across two machines.

---

## Machines

| Machine | Hostname | SSH key for Codeberg |
|---|---|---|
| Primary laptop | `entroware-proteus` | `~/.ssh/woodpecker_pages` (CI deploy key) |
| Second laptop | `xps13` | `~/.ssh/id_ed25519_codeberg` |

Both machines use `~/.ssh/id_ed25519` for GitHub.

---

## Remotes

`origin` is configured with **one fetch URL and two push URLs**:

```
fetch  → git@github.com:alxtrnr/bongo-twisty.git
push   → git@github.com:alxtrnr/bongo-twisty.git
push   → git@codeberg.org:BongoTwisty/bongo-twisty.git
```

A single `git push` sends commits to **both** GitHub and Codeberg.

To verify on either machine:

```bash
git remote -v
git config --get-all remote.origin.pushurl
```

To rebuild these remotes from scratch on a new machine:

```bash
git remote set-url --add --push origin git@github.com:alxtrnr/bongo-twisty.git
git remote set-url --add --push origin git@codeberg.org:BongoTwisty/bongo-twisty.git
```

---

## SSH config (~/.ssh/config)

### entroware-proteus

```sshconfig
Host codeberg.org
  HostName codeberg.org
  User git
  IdentityFile ~/.ssh/woodpecker_pages
  IdentitiesOnly yes
```

### xps13

```sshconfig
Host codeberg.org
  HostName codeberg.org
  User git
  IdentityFile ~/.ssh/id_ed25519_codeberg
  IdentitiesOnly yes
```

Test SSH auth at any time with:

```bash
ssh -T git@codeberg.org
# Expected: Hi there, BongoTwisty! You've successfully authenticated ...
```

---

## Day-to-day workflow

```bash
# 1. Start — always pull first to avoid diverging branches
cd ~/bongo-twisty
git pull origin main

# 2. Work — write posts, edit config, update templates, etc.

# 3. Commit and push
git add .
git commit -m "describe your change"
git push
# Pushes to GitHub and Codeberg in one command
```

After the push to Codeberg, Woodpecker CI automatically:

1. Builds the site with Hugo v0.160.1-extended.
2. Runs Pagefind 1.3.0 to index search.
3. Runs `tools/send_webmentions.py`.
4. Publishes the built `public/` to `codeberg.org:BongoTwisty/pages.git` on the `pages` branch.

The live site updates at **https://BongoTwisty.codeberg.page** within a few minutes.

---

## CI/CD pipeline (.woodpecker.yml)

Triggered on: push to `main` branch on Codeberg only (GitHub pushes do not trigger CI).

### Steps

#### build

- Image: `debian:bookworm-slim`
- Installs: git, curl, ca-certificates, python3, nodejs, npm, golang
- Downloads and installs Hugo v0.160.1-extended from GitHub releases
- Runs `git submodule update --init --recursive`
- Builds site: `hugo --gc --minify --baseURL "https://BongoTwisty.codeberg.page/"`
- Indexes search: `npx -y pagefind@1.3.0 --site public`
- Sends webmentions: `python3 tools/send_webmentions.py`
- Verifies `public/` and `public/index.html` exist

#### publish

- Image: `alpine:3.20`
- Uses the `pages_deploy_key` secret (set in Woodpecker CI settings)
- Clones `codeberg.org:BongoTwisty/pages.git` (branch: `pages`)
- Replaces its contents with the built `public/` directory
- Copies `static/.domains` to set the custom domain, or writes `BongoTwisty.codeberg.page` as fallback
- Commits and force-pushes to the `pages` branch

---

## Secrets and keys

| Secret / Key | Where stored | Purpose |
|---|---|---|
| `pages_deploy_key` | Woodpecker CI → repo secrets | Private key used by the publish step to push to the pages repo |
| Public key for above | Codeberg → `BongoTwisty/pages` → Deploy Keys (write access) | Allows CI to push built site to the pages repo |
| `~/.ssh/id_ed25519_codeberg` | xps13 only | SSH auth for pushing source to Codeberg |
| `~/.ssh/woodpecker_pages` | entroware-proteus only | SSH auth for pushing source to Codeberg (same key pair as CI deploy key) |

---

## Hugo module

The site uses the `hugo-module-listenbrainz` Go module (`go.deuill.org/hugo-module-listenbrainz`), declared in `go.mod`. Hugo fetches it automatically during build.

---

## Theme

Theme is a Git submodule at `themes/hugo-simple`. Always initialise it after cloning:

```bash
git submodule update --init --recursive
```

---

## Watching a pipeline run

1. Go to [https://ci.codeberg.org/BongoTwisty/bongo-twisty](https://ci.codeberg.org/BongoTwisty/bongo-twisty)
2. Click the latest pipeline.
3. Steps run in order: `clone` → `build` → `publish`.
4. All three must be green for the site to have deployed.

If a pipeline is stuck on "not started yet" for more than ~10 minutes, click **Restart**.

---

## New machine setup checklist

- [ ] Clone repo: `git clone git@github.com:alxtrnr/bongo-twisty.git`
- [ ] Init submodules: `git submodule update --init --recursive`
- [ ] Add Codeberg push URL: `git remote set-url --add --push origin git@codeberg.org:BongoTwisty/bongo-twisty.git`
- [ ] Generate a Codeberg SSH key: `ssh-keygen -t ed25519 -a 100 -f ~/.ssh/id_ed25519_codeberg -C "user@hostname-codeberg"`
- [ ] Add public key to Codeberg account: Settings → SSH / GPG Keys
- [ ] Add `~/.ssh/config` block for `codeberg.org` pointing to the new key
- [ ] Test: `ssh -T git@codeberg.org`
- [ ] Test dual push: `git commit --allow-empty -m "test: new machine" && git push`
