
# Bongo Twisty

A personal Hugo blog deployed via **dual CI/CD** to both GitHub Pages and Codeberg Pages.

## Quick Start

Install npm dependencies (for PostCSS)
```bash
npm install
```
Initialize Hugo submodule (theme)
```bash
git submodule update --init --recursive
```
Run development server with drafts
```bash
hugo server -D
```
Build site for production
```bash
hugo --gc --minify
```

## Configuration

| Setting | Value 
| -------- | -------- 
| Hugo Version     | v0.164.0-extended
| Theme | hugo-simple (Git submodule)
|Output Directory | public/
| License | MIT

## Deployment Architecture
**Dual deployment:** Both platforms build from the same main branch on push.



| Platform | Domain | Role |
| -------- | -------- | -------- |
| GitHub     | https://bongotwisty.blog/     | Primary (custom domain)     |
| Codeberg Pages     | https://bongotwisty.codeberg.page/     | Mirror / backup    |




## What Happens on Push
A single git push triggers both CI pipelines simultaneously:

**GitHub Actions**

1. Builds Hugo site with --gc --minify
2. Runs Pagefind for search indexing
3. Sends webmentions (incremental mode)
4. Deploys to GitHub Pages with custom domain

**Codeberg Woodpecker CI**

1. Builds Hugo site with --gc --minify
2. Runs Pagefind 1.3.0 for search indexing
3. Sends webmentions (incremental mode)
4. Publishes to pages branch (default Codeberg domain)

## Project Structure
bongo-twisty/
├── .github/workflows/     # GitHub Actions pipeline
├── .woodpecker.yml        # Codeberg Woodpecker CI
├── archetypes/            # Content templates
├── assets/                # Source assets (CSS/JS)
├── content/               # Blog posts and pages
├── layouts/               # Custom template overrides
├── static/                # Static files (copied directly)
├── tools/                 # Build utilities (webmentions)
├── themes/                # Hugo Simple theme (submodule)
├── .gitmodules            # Submodule definitions
├── hugo.toml              # Main configuration
├── package.json           # npm dependencies
└── WORKFLOW.md            # Development workflow reference

## CI/CD Pipelines
### GitHub Actions (.github/workflows/hugo.yaml)
**Trigger:** Push to main, PRs to main, manual dispatch

**Features:**

- Caches Hugo build artefacts for faster subsequent builds
- Auto-detects base URL from Pages configuration
- Runs on ubuntu-latest

### Codeberg Woodpecker (.woodpecker.yml)
**Trigger:** Push to main on Codeberg

**Features:**

- Installs sass and golang for Hugo module resolution
- Uses /tmp/hugo_cache for Hugo build cache (ephemeral)
- Requires pages_deploy_key secret for publishing

## Webmentions
This blog sends W3C Webmentions for external content references using tools/send_webmentions.py.

**How it works:**

* Scans generated HTML for external links
* Discovers webmention endpoints on target sites
* Sends webmentions to notify referenced sites
* Caches results in webmention-sent.json (Git-tracked)

**Running locally:**
```bash
# Full scan of all content
SITE_URL="https://bongotwisty.blog" MODE=full python3 tools/send_webmentions.py

# Incremental (last 10 commits)
SITE_URL="https://bongotwisty.blog" MODE=incremental python3 tools/send_webmentions.py
```

## Development Notes
#### Creating Content
```bash
# Create a new post
hugo new content/posts/my-new-post.md

# Draft posts are excluded from production builds
hugo server -D      # Include drafts in dev server
hugo                # Production build (excludes drafts)
```
## Theme Management
The theme is a Git submodule at themes/hugo-simple:

```bash
# Update theme to latest
git submodule update --remote --merge

# View theme commit hash
git ls-tree HEAD themes/hugo-simple
```

## Dependencies
* **npm:** PostCSS processing (postcss, postcss-cli)
* **Go modules**: ListenBrainz integration (hugo-module-listenbrainz)
* **Node.js**: Pagefind search indexer

Install after cloning:
```bash
npm install
git submodule update --init --recursive
```

## Environment Variables
Both CI pipelines set these during build:



| Variable | GitHub | Codeberg |
| -------- | -------- | -------- |
| HUGO_ENVIRONMENT     |   production   |   production   |
| TZ | LondonEurope | LondonEurope
| SITE_URL | https://bongotwisty.blog | https://BongoTwisty.codeberg.page

## Monitoring Builds

| Platform | Status 
| -------- | --------
| GitHub Actions     | [Actions](https://github.com/alxtrnr/bongo-twisty/actions) 
| Codeberg WoodpeckerCI | [CI](https://ci.codeberg.org/BongoTwisty/bongo-twisty)


## Contributing / Forking
If you fork this blog:

1. Update the baseURL in hugo.toml
2. Reconfigure SITE_URL in both CI pipelines
3. Set up your own webmentions cache or disable webmentions
4. Clear the webmention-sent.json cache

See WORKFLOW.md for detailed multi-machine setup instructions.

## License

- **Blog content** (posts, images, etc.): CC BY-NC 4.0 (see [Creative Commons](https://creativecommons.org/licenses/by-nc/4.0/))
- **Infrastructure code** (scripts, configs, templates): MIT License (see [LICENSE](LICENSE))
- **Theme** (hugo-simple): Licensed separately under its own terms