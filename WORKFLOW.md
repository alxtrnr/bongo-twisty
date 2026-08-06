# BongoTwisty - Development Workflow

A reference for day-to-day blog work across two machines.

## Machines

| Machine | Hostname | SSH key for Codeberg |
|---|---|---|
| Primary laptop | `entroware-proteus` | `~/.ssh/woodpecker_pages` (CI deploy key) |
| Second laptop | `xps13` | `~/.ssh/id_ed25519_codeberg` |

Both machines use `~/.ssh/id_ed25519` for GitHub.

## Remotes

`origin` is configured with **one fetch URL and three push URLs**:

fetch  → git@github.com:alxtrnr/bongo-twisty.git
push   → git@github.com:alxtrnr/bongo-twisty.git
push   → git@codeberg.org:BongoTwisty/bongo-twisty.git
push → git@codefloe.com:BongoTwisty/bongo-twisty.git

A single `git push` sends commits to **all three** GitHub, Codeberg, and Codefloe.

To verify on either machine:
```
git remote -v
git config --get-all remote.origin.pushurl
```
To rebuild these remotes from scratch on a new machine:bash
```
git remote set-url --add --push origin git@github.com:alxtrnr/bongo-twisty.git
git remote set-url --add --push origin git@codeberg.org:BongoTwisty/bongo-twisty.git
git remote set-url --add --push origin git@codefloe.com:BongoTwisty/bongo-twisty.git
```

## SSH config (~/.ssh/config)

### entroware-proteus ssh config
```
Host: codeberg.org
HostName: codeberg.org
User: git
IdentityFile: ~/.ssh/woodpecker_pages
IdentitiesOnly: yes

Host: codefloe.com
HostName: codefloe.com
User: git
IdentityFile: ~/.ssh/id_ed25519_codefloe
IdentitiesOnly: yes
```

### xps13 ssh config
```
Host codeberg.org
HostName codeberg.org
User git
IdentityFile ~/.ssh/id_ed25519_codeberg
IdentitiesOnly yes

Host codefloe.com
HostName: codefloe.com
User git
IdentityFile ~/.ssh/id_ed25519_codefloe
IdentitiesOnly yes
```
Test SSH auth at any time with:
```
ssh -T git@codeberg.org
Expected: Hi there, BongoTwisty! You've successfully authenticated

ssh -T git@codefloe.com
Expected: Hi there, BongoTwisty! You've successfully authenticated
```

## Day-to-day workflow
1. Start - always pull first to avoid diverging branches
```
cd ~/bongo-twisty
git pull origin main
```
2. Work - write posts, edit config, update templates, etc.
3. Commit and push
```
git add .
git commit -m "describe your change"
git push
```

A single `git push` triggers **all three** CI pipelines simultaneously. Pushes to GitHub, Codeberg, and Codefloe in one command. 

### GitHub Actions (primary deployment)

1. Installs Hugo v0.164.0-extended and Dart Sass.
2. Restores Hugo build cache from previous runs.
3. Builds site with `--gc --minify` using auto-detected base URL (custom domain:`https://bongotwisty.blog`).

5. Runs Pagefind to index search.
6. Saves Hugo build cache for next run.
7. Sends webmentions (incremental mode, `SITE_URL=https://bongotwisty.blog`).
8. Uploads `public/` as a GitHub Pages artifact and deploys.

The live site updates at **https://bongotwisty.blog** within a few minutes.

### Codeberg Woodpecker (mirror deployment)

1. Installs Hugo v0.164.0-extended (downloaded binary), sass, golang (required for Hugo module resolution), Python 3, Node.js.

3. Builds site with `--gc --minify --baseURL "https://BongoTwisty.codeberg.page/"`.
4. Runs Pagefind 1.3.0 to index search.
5. Sends webmentions (`SITE_URL=https://BongoTwisty.codeberg.page`).
6. Publishes the built `public/` to `codeberg.org:BongoTwisty/pages.git` on the `pages` branch.

The mirror site updates at **https://BongoTwisty.codeberg.page** within a few minutes.

### Codefloe Crow CI (contingency deployment)
1. Installs Hugo v0.164.0-extended (downloaded .deb), sass, golang (required for Hugo module resolution), Python 3, Node.js, npm.

3. Builds site with `--gc --minify --baseURL "https://bongo-twisty.bongotwisty.codefloe.page/"`.
 
5. Runs Pagefind 1.3.0 to index search.
 
4. Sends webmentions (`SITE_URL=https://bongo-twisty.bongotwisty.codefloe.page`).
 
5. Pushes built public/ to the pages branch in the same repo on Codefloe.
 
6. statichost.eu serves the static content from the pages branch.

The contingency site updates at https://bongo-twisty.bongotwisty.codefloe.page within a few minutes.

## Triple deployment architecture

| Platform | Domain | Role | Custom domain |
|---|---|---|---|
| GitHub Pages | `bongotwisty.blog` | Primary | Yes (configured in GitHub repo settings) |
| Codeberg Pages | `BongoTwisty.codeberg.page` | Mirror / backup | No (uses default Codeberg Pages URL) |
| Codefloe Pages | `bongo-twisty.bongotwisty.codefloe.page` | Contingency| No (uses default Codefloe Pages URL) |

All three pipelines build from the same `main` branch on push. GitHub Actions is the primary deployment serving the custom domain. Codeberg Pages serves as a mirror with the default Codeberg domain. Codefloe Pages serves as a contingency deployment on statichost.eu infrastructure.

## CI/CD pipelines

### GitHub Actions (`.github/workflows/hugo.yaml`)

Triggered on: push to `main`, PRs to `main`, and manual dispatch.

**Concurrency**: Queues builds (`cancel-in-progress: false`).

#### build job

- Runner: `ubuntu-latest`
- Installs Hugo v0.164.0-extended via `.deb` package
- Installs Dart Sass via `snap`
- Checks out repo with `fetch-depth: 0` (full history for incremental webmentions)
- Configures GitHub Pages (auto-detects base URL)
- Installs Node.js dependencies (`npm ci`) if `package-lock.json` exists
- Restores Hugo cache from previous runs (`actions/cache/restore@v4`)
- Builds: `hugo --gc --minify --baseURL "<auto>/" --cacheDir "<runner_temp>/hugo_cache"`
- Indexes search: `npx -y pagefind --site public`
- Saves Hugo cache (`actions/cache/save@v4`)
- Sends webmentions (only on push, not PRs): `SITE_URL=https://bongotwisty.blog MODE=incremental python tools/send_webmentions.py`
- Uploads `./public` as Pages artifact

#### deploy job

- Runs only on push to `main` (not PRs)
- Deploys artifact to GitHub Pages via `actions/deploy-pages@v4`

### Codeberg Woodpecker (`.woodpecker.yml`)

Triggered on: push to `main` branch on Codeberg.

#### build step

- Image: `debian:bookworm-slim`
- Installs: git, curl, ca-certificates, python3, nodejs, npm, sass, golang
- Downloads and installs Hugo v0.164.0-extended from GitHub releases
- Builds site: `hugo --gc --minify --baseURL "${SITE_URL}/" --cacheDir "$HUGO_CACHE_DIR"`
- Indexes search: `npx -y pagefind@1.3.0 --site public`
- Sends webmentions: `SITE_URL=https://BongoTwisty.codeberg.page python tools/send_webmentions.py`
- Verifies `public/` and `public/index.html` exist

#### publish step

- Image: `alpine:3.20`
- Uses the `pages_deploy_key` secret (set in Woodpecker CI settings)
- Clones `codeberg.org:BongoTwisty/pages.git` (branch: `pages`)
- Replaces its contents with the built `public/` directory
- Copies `static/.domains` to set the custom domain, or writes `BongoTwisty.codeberg.page` as fallback
- Commits and pushes to the `pages` branch

### Codefloe Crow CI (.crow/build.yaml)
Triggered on: push to main branch on Codefloe (filtered via when: clause).

#### build step
* Image: `debian:bookworm-slim`
* Installs: git, curl, ca-certificates, python3, nodejs, npm, sass, golang
* Downloads and installs Hugo v0.164.0-extended from GitHub releases (.deb package)
* Updates git submodules (`git submodule update --init --recursive`)
* Builds site: `hugo --gc --minify --baseURL "${SITE_URL}/" --cacheDir "$HUGO_CACHE_DIR"`
* Indexes search: `npx -y pagefind@1.3.0 --site public`
* Verifies `public/index.html` exists
* Sends webmentions: `SITE_URL=https://bongo-twisty.bongotwisty.codefloe.page MODE=incremental python3 tools/send_webmentions.py`

#### publish step
* Image: `alpine:3.20`
* Uses the pages_deploy_key secret (set in Crow CI settings)
* Writes the private key from the secret to `~/.ssh/id_ed25519`
* Scans Codefloe SSH host key into `known_hosts`
* Clones `codefloe.com:BongoTwisty/bongo-twisty.git` (branch: pages)
* Replaces its contents with the built `public/` directory
* Writes `statichost.yml` configuration file
* Commits and pushes to the pages branch
* `statichost.eu` deploys the updated content automatically

**Note:** The publish step only runs when the push event is to the main branch (when: clause with evaluate).


## Environment variables

All three pipelines set the following environment variables:

| Variable | GitHub Actions | Codeberg Woodpecker | Purpose |
|---|---|---|---|
| `HUGO_ENVIRONMENT` | `production` | `production` | Enables production-specific Hugo features |
| `TZ` | `Europe/London` | `Europe/London` | Consistent timestamps in logs and deploy commits |
| `SITE_URL` | `https://bongotwisty.blog` | `https://BongoTwisty.codeberg.page` | Webmention script internal link filtering |
| `HUGO_CACHE_DIR` | `<runner_temp>/hugo_cache` | `/tmp/hugo_cache` | Hugo build cache location |


## Webmentions (`tools/send_webmentions.py`)

The webmention script implements the W3C Webmention protocol with two modes:

- **Incremental** (default): Uses `git diff HEAD~10` to find recently changed content files, sends webmentions only for those.
- **Full** (`MODE=full`): Scans all HTML files in `public/`, sends webmentions for all uncached external links.

### Features

- **`SITE_URL` env var**: Filters internal links correctly per deployment target.
- **HTTP status checking**: Distinguishes 2xx (success), 404/410 (gone - not cached, will retry), 429 (rate limited), and other errors.
- **`<a rel="webmention">` support**: Discovers endpoints in both `<link>` and `<a>` tags per W3C spec.
- **Webring denylist**: Excludes `xn--sr8hvo.ws` and `fediring.net` (site chrome, not editorial references).
- **Cache persistence**: `webmention-sent.json` is committed to the repo so it survives between CI runs on both platforms. Prevents duplicate sends.

### Running locally
Build first
```
hugo --gc --minify --baseURL "https://bongotwisty.blog/"
```
Full scan (first run or debugging)
```
SITE_URL="https://bongotwisty.blog" MODE=full python3 tools/send_webmentions.py
```
Incremental (checks last 10 commits)
```
SITE_URL="https://bongotwisty.blog" MODE=incremental python3 tools/send_webmentions.py
```

## Secrets and keys

| Secret / Key | Where stored | Purpose |
|---|---|---|
| `pages_deploy_key` | Woodpecker CI → repo secrets | Private key used by the Codeberg publish step to push to the pages repo |
| Public key for above | Codeberg → `BongoTwisty/pages` → Deploy Keys (write access) | Allows CI to push built site to the pages repo |
| `pages_deploy_key` | Crow CI → repo secrets | Private key used by the Codefloe publish step to push to the pages repo |
| Public key for above | Codefloe → `BongoTwisty/bongo-twisty` → Deploy Keys (write access) | Allows CI to push built site to the pages repo |
| `~/.ssh/id_ed25519` | Both machines | SSH auth for pushing source to GitHub |
| `~/.ssh/woodpecker_pages` | entroware-proteus | SSH auth for pushing source to Codeberg (same key pair as CI deploy key) |
| `~/.ssh/id_ed25519_codeberg` | xps13 | SSH auth for pushing source to Codeberg |
| `~/.ssh/id_ed25519_codefloe` | Both machines | SSH auth for pushing source to Codefloe |
| `~/.ssh/codefloe_pages_deploy` | entroware-proteus (local only) | Private key for Crow CI publish step (stored as Crow CI secret) |

GitHub Actions authenticates via its built-in `GITHUB_TOKEN` - no additional secrets needed.

## Dependencies

### System packages

| Package | GitHub Actions | Codeberg Woodpecker | Required for |
|---|---|---|---|
| Hugo v0.164.0-extended | `.deb` from GitHub releases | Binary tarball from GitHub releases | Site build (SCSS via `toCSS`) |
| Dart Sass | `snap install dart-sass` | `apt-get install sass` | SCSS compilation |
| Go (golang) | Pre-installed on runner | `apt-get install golang` | Hugo module resolution (`go.mod`) |
| Python 3 | Pre-installed on runner | `apt-get install python3` | Webmention script |
| Node.js + npm | Pre-installed on runner | `apt-get install nodejs npm` | Pagefind, PostCSS |

### Node.js (`package.json`)

- `postcss` and `postcss-cli` — CSS post-processing during Hugo build.

### Hugo modules (`go.mod`)

- `go.deuill.org/hugo-module-listenbrainz` — Displays recent ListenBrainz scrobbles.

### Theme

Theme is a Git submodule at `themes/hugo-simple`. Always initialise it after cloning:
```
git submodule update --init --recursive
```

## Cache files

| File | Tracked in Git | Purpose |
|---|---|---|
| `webmention-sent.json` | Yes | Records sent webmentions to prevent duplicates across CI runs |

Hugo's own build cache (`hugo_cache` / `HUGO_CACHE_DIR`) is handled separately:
- GitHub Actions: `actions/cache@v4` (persists between runs)
- Codeberg Woodpecker: `/tmp/hugo_cache` (ephemeral, lost between runs)
- Codefloe Crow CI:`/tmp/hugo_cache` (ephemeral, lost between runs)


## Watching a pipeline run

### GitHub Actions

1. Go to https://github.com/alxtrnr/bongo-twisty/actions
2. Click the latest workflow run.
3. Jobs run in order: `build` → `deploy`.
4. Both must be green for the site to have deployed.

### Codeberg Woodpecker

1. Go to https://ci.codeberg.org/BongoTwisty/bongo-twisty
2. Click the latest pipeline.
3. Steps run in order: `clone` → `build` → `publish`.
4. All three must be green for the site to have deployed.

### Codefloe Crow CI
1. Go to https://ci.crowci.dev/BongoTwisty/bongo-twisty
2. Click the latest pipeline.
3. Steps run in order: clone → build → publish.
4. Both build and publish must be green for the site to have deployed.

If a pipeline is stuck on "not started yet" for more than ~10 minutes, click **Restart**.


## New machine setup checklist

- [ ] Clone repo: `git clone git@github.com:alxtrnr/bongo-twisty.git`
- [ ] Init submodules: `git submodule update --init --recursive`
- [ ] Add Codeberg push URL: `git remote set-url --add --push origin git@codeberg.org:BongoTwisty/bongo-twisty.git`
- [ ] Add Codefloe push URL: `git remote set-url --add --push origin git@codefloe.com:BongoTwisty/bongo-twisty.git`
- [ ] Generate a Codeberg SSH key: `ssh-keygen -t ed25519 -a 100 -f ~/.ssh/id_ed25519_codeberg -C "user@hostname-codeberg"`
- [ ] Add public key to Codeberg account: Settings → SSH / GPG Keys
- [ ] Add `~/.ssh/config` block for `codeberg.org` pointing to the new key
- [ ] Test: `ssh -T git@codeberg.org`
- [ ] Generate a Codefloe SSH key: `ssh-keygen -t ed25519 -a 100 -f ~/.ssh/id_ed25519_codefloe -C "user@hostname-codefloe"`
- [ ] Add public key to Codefloe account: Settings → SSH / GPG Keys
- [ ] Add `~/.ssh/config` block for `codefloe.com` pointing to the new key
- [ ] Test: `ssh -T git@codefloe.com`
- [ ] Test triple push: `git commit --allow-empty -m "test: new machine" && git push`
- [ ] Verify all three CI pipelines ran green (GitHub Actions + Codeberg Woodpecker + Codefloe Crow CI)

