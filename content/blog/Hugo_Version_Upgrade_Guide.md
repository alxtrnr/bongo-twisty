+++
title = "Hugo (extended edition) Version Upgrade Guide"
description = "A belts and braces approach to help mitigate the risk of breaking changes."
date = 2026-01-08
tags = ["Hugo"]
+++

**This guide covers Hugo Extended Edition upgrades for Linux + GitHub Pages. See the footnote before reading on.**[^1]

I like to keep things up to date. Every time I went through this process I'd generate a thread with my preferred LLM to help me through from beginning to end. The thread always became cluttered as I asked follow-up questions and sought clarification.

This time round, after successfully completing the upgrade (I've now done this multiple times with different versions), I remembered to prompt:

> *"...list in sequential order everything I should do in the future to upgrade the hugo version. Granular step-by-step instructions with a concise description of the aim and why for each step".*

The guide is excellent for my exact use case and good for similar Linux + GitHub Pages setups, but has limited value for people on different operating systems or hosting platforms. What I've done here is easy enough to replicate to suit your own use case if you're not opposed to using an LLM to do so. It's not all slop and you can always offset the [environmental impact](https://andymasley.substack.com/i/154446312/other-online-activities-emissions) of your prompts easily enough. 

#### Pre-Upgrade: Check Release Notes and Current Version

**Aim**: Understand what's changing and know your starting point.

**Process**:

1. Visit the Hugo releases page: `https://github.com/gohugoio/hugo/releases`
2. Review the release notes for your target version, paying attention to:
    - Breaking changes (marked with ⚠️ or "BREAKING")
    - Deprecation warnings
    - New features that might affect your workflow
3. Check your current local version:
```bash
hugo version
```

**Why**: Hugo occasionally introduces breaking changes that can affect your site's build or appearance. Understanding these beforehand helps you anticipate issues. The version check confirms what you're running locally and whether you have the extended edition (look for `+extended` in output).

***

#### Step 1: Download the new Hugo version

**Aim**: Get the extended edition of the new Hugo release.

**Process**:

```bash
cd ~/Downloads
wget https://github.com/gohugoio/hugo/releases/download/v0.154.2/hugo_extended_0.154.2_linux-amd64.tar.gz
```

Replace the version numbers with your target version (e.g., `v0.154.2` in the URL and `0.154.2` in the filename). **Note**: The URL includes the `v` prefix, but the filename does not.

**Why**: Downloads the official Hugo extended binary from GitHub. The extended edition includes Sass/SCSS transpiling and WebP processing capabilities required by many themes.

***

#### Step 2: Extract the archive

**Aim**: Unpack the compressed file to access the Hugo executable.

**Process**:

```bash
tar -xzf hugo_extended_0.154.2_linux-amd64.tar.gz
```

(Replace version number to match your download)

**What this does**:

- `tar`: Archive extraction tool
- `-x`: Extract files
- `-z`: Decompress gzip format
- `-f`: Specify filename

**Why**: The `.tar.gz` format is a compressed archive. This unpacks it to create the `hugo` executable file.

***

#### Step 3: Verify the extracted binary

**Aim**: Confirm you downloaded the correct version and extended edition.

**Process**:

```bash
./hugo version
```

**Expected output**: Should show `hugo v0.154.2-...<commit-hash>+extended linux/amd64`

**Critical check**: Look for `+extended` in the output.[^3]

**Why**: The `./` runs the binary in your current directory (not the system-installed version). This tests the new version before installation.

***

#### Step 4: Replace the system Hugo binary

**Aim**: Install the new version system-wide.

**Process**:

```bash
sudo mv hugo /usr/local/bin/hugo
```

**What this does**:

- `sudo`: Runs with administrator privileges (required for system directories)
- `mv`: Moves/overwrites the file
- Replaces your old `/usr/local/bin/hugo` with the new version

**You'll be prompted**: Enter your system password.

**Why**: Installs the new Hugo binary in the system PATH so the `hugo` command uses the updated version.

***

#### Step 5: Confirm system upgrade

**Aim**: Verify the `hugo` command now runs the new version.

**Process**:

```bash
hugo version
```

**Expected output**: Should show the new version number with `+extended`.

**Why**: Confirms the system-wide Hugo is now the upgraded version (no `./` prefix needed).

***

#### Step 6: Clean up downloads

**Aim**: Remove temporary files to free disk space.

**Process**:

```bash
cd ~/Downloads
rm hugo_extended_0.154.2_linux-amd64.tar.gz LICENSE README.md
```

(Replace version number to match your files)

**Why**: The archive and documentation files are no longer needed since Hugo is installed.

***

#### Step 7: Navigate to your Hugo project

**Aim**: Work in the correct directory for testing.

**Process**:

```bash
cd ~/path/to/your-hugo-project
```

**Verify you're in the right place**:

```bash
ls -la
```

**Should see**: `hugo.toml` (or `config.toml`), `content/`, `layouts/`, `themes/` directories.

**Why**: Hugo commands must run from the project root directory where the config file lives.

***

#### Step 8: Run a production build test

**Aim**: Test that the new version builds your site without errors.

**Process**:

```bash
hugo --gc --minify
```

**What each flag does**:

- `hugo`: Builds your site (Markdown to HTML)
- `--gc`: Garbage collection—removes unused cache files
- `--minify`: Compresses HTML/CSS/JS output (production setting)

**Watch for**:

- Build completion message with timing (e.g., "Total in 774 ms")
- Page/image counts
- Any ERROR messages (build failures—these are critical)
- WARN messages (note these; they indicate deprecated features you should eventually address but usually won't break your build)[^4][^6]

**Why**: Simulates your production build environment. If this succeeds, GitHub Actions deployment will likely succeed.

***

#### Step 9: Test the development server

**Aim**: Visually verify your site renders correctly in a browser.

**Process**:

```bash
hugo server --disableFastRender
```

**What this does**:

- Starts local web server at `http://localhost:1313`
- Builds site in memory (no disk writes)
- Watches files for changes and auto-rebuilds
- `--disableFastRender`: Forces complete page rebuilds (catches more issues)

**Expected output**: `Web Server is available at http://localhost:1313/`

**Why**: The flag ensures full rebuilds instead of partial rendering, which better matches production behavior.

***

#### Step 10: Visual testing in browser

**Aim**: Confirm templates, images, and layout render correctly.

**Process**:

1. Open browser to `http://localhost:1313` (or `http://localhost:1313/your-base-path/`)
2. Click through:
    - Homepage
    - Individual blog posts/pages
    - List/archive pages
    - Tag/category pages
    - Navigation menu
    - Search (if applicable)
3. Watch the terminal for WARNING or ERROR messages

**Why**: Visual testing catches issues that don't produce error messages—broken layouts, missing images, CSS problems (especially if your theme uses Sass/SCSS), JavaScript errors.

***

#### Step 11: Stop the development server

**Aim**: Release the local web server and file watcher.

**Process**:

Press `Ctrl+C` in the terminal.

**Why**: Stops the server process and frees port 1313.

***

#### Step 12: Update GitHub Actions workflow file

**Aim**: Configure your production deployment to use the new Hugo version.

**Process**:

```bash
nano .github/workflows/hugo.yaml
```

**Find the line** (search with `Ctrl+W` and type `HUGO_VERSION:`):

```yaml
env:
  HUGO_VERSION: 0.153.2
```

**Change to**:

```yaml
env:
  HUGO_VERSION: 0.154.2
```

Replace with your target version number (no `v` prefix in the version number itself).

**Critical**: Leave all other lines unchanged, especially `extended: true` settings.

**Save and exit**: `Ctrl+O`, `Enter`, `Ctrl+X`

**Alternative approach**: If your workflow uses the `peaceiris/actions-hugo` action instead of manual `.deb` installation, you'll update the version in the action configuration instead:

```yaml
- name: Setup Hugo
  uses: peaceiris/actions-hugo@v3
  with:
    hugo-version: '0.154.2'
    extended: true
```

**Why**: This environment variable controls which Hugo version GitHub Actions downloads when building your site.[^7]

***

#### Step 13: Stage the workflow file

**Aim**: Prepare the modified file for Git commit.

**Process**:

```bash
git add .github/workflows/hugo.yaml
```

**Why**: Git requires explicit staging of files before committing. This tells Git "include this file in my next commit."

***

#### Step 14: Verify what you're committing

**Aim**: Safety check before creating the commit.

**Process**:

```bash
git status
```

**Expected output**:

```bash
Changes to be committed:
  modified:   .github/workflows/hugo.yaml
```

**Verify**: Only the workflow file is listed; status shows "modified".

**Why**: Final confirmation you're only changing what you intended, preventing accidental commits.

***

#### Step 15: Create a Git commit

**Aim**: Save a snapshot of your change with a descriptive message.

**Process**:

```bash
git commit -m "Upgrade Hugo to v0.154.2"
```

Replace with your new version number.

**Expected output**: Shows commit hash and "1 file changed, 1 insertion(+), 1 deletion(-)".

**Why**: Commits are the fundamental unit in Git. Each has a unique ID and message describing what changed.

***

#### Step 16: Push to GitHub

**Aim**: Upload your commit to trigger the automated deployment.

**Process**:

```bash
git push origin main
```

(Replace `main` with your branch name if different, e.g., `master`.)

**Expected output**: Shows upload progress ending with `main -> main`.

**Why**: Pushing to GitHub automatically triggers your Actions workflow. GitHub reads the updated workflow file and starts a build with the new Hugo version.

***

#### Step 17: Open GitHub Actions in browser

**Aim**: Monitor the automated build in real-time.

**Process**:

Navigate to: `https://github.com/YOUR-USERNAME/YOUR-REPO/actions`

**Why**: GitHub Actions runs in a clean cloud environment. This confirms your site builds successfully there, not just locally.

***

#### Step 18: Find your workflow run

**Aim**: Locate the build triggered by your push.

**Process**:

Look for:

- Workflow name: "Deploy Hugo site to Pages" (or your workflow name)
- Commit message: "Upgrade Hugo to v0.154.2"
- Status: Yellow dot (in progress) or green checkmark (completed)
- Timestamp matching when you pushed

**Click on the workflow run** to see detailed logs.

**Why**: Opens the detailed view showing all build steps and their status.

***

#### Step 19: Monitor build job logs

**Aim**: Verify each build step completes successfully.

**Process**:

Click on the **build** job to expand steps. Watch for:

**"Install Hugo CLI" step**: Should show

```bash
Unpacking hugo (from .../hugo_extended_0.154.2_linux-amd64.deb) ...
```

(Or if using `peaceiris/actions-hugo`, you'll see different installation messages)

**"Build with Hugo" step**: Should show

```bash
hugo v0.154.2-...+extended linux/amd64
Pages            | [YOUR_PAGE_COUNT]
Processed images | [YOUR_IMAGE_COUNT]
Total in [TIME] ms
```

**Look for**:

- Green checkmarks next to each step
- Any WARNING messages (usually harmless but note them)
- Any ERROR messages (build failures—investigate these immediately)

**Why**: The build logs show exactly what GitHub's servers are doing. This catches environment-specific issues.

***

#### Step 20: Verify deployment completion

**Aim**: Confirm the site deployed to GitHub Pages successfully.

**Process**:

1. Wait for the **deploy** job to complete (appears after **build**)
2. Look for green checkmark and "Reported success!" message
3. Note the deployment URL shown in the logs

**Why**: The deploy step publishes your built site. A green checkmark means your updated site is live.

***

#### Step 21: Test your live site

**Aim**: Final verification that the production site works correctly.

**Process**:

1. Visit your GitHub Pages URL (e.g., `https://username.github.io/repo-name/`)
2. **Wait 2-5 minutes** for GitHub Pages to fully propagate the changes
3. Click through several pages
4. Check images load
5. Verify navigation works
6. Test any interactive features
7. If your theme uses Sass/SCSS, verify styling appears correctly

**Why**: Confirms the new Hugo version works in production, not just in CI/CD. This is your users' experience.

***

#### Rollback Procedure (if needed)

**Aim**: Quickly restore the working version if something breaks.

**Process**:

```bash
nano .github/workflows/hugo.yaml
```

Change the version back to the previous working version:

```yaml
env:
  HUGO_VERSION: 0.153.2
```

Then commit and push:

```bash
git add .github/workflows/hugo.yaml
git commit -m "Rollback to Hugo v0.153.2 - investigating v0.154.2 issue"
git push origin main
```

**Why**: Version control gives you a safety net. You can always revert to restore your site while investigating issues.

***

#### Notes

- Always use the **extended edition** (`hugo_extended_`) to maintain Sass/SCSS and WebP support
- The local version and GitHub Actions version should match to ensure consistent builds
- Check release notes for breaking changes before upgrading
- Deprecation warnings (WARN messages) usually don't break builds but should be addressed eventually to future-proof your site
- Build times should be similar between versions; significant slowdowns may indicate issues
- Keep your local Hugo version updated to match your deployment environment

[^1]:
    This guide is specifically tailored for:

    #### Operating System

    **Linux distributions** (Ubuntu, Debian, Fedora, Mint, Pop!_OS, etc.)
    Specifically uses Linux commands like:
    - `wget` for downloading
    - `tar` for extraction
    - `sudo` for system permissions
    - `/usr/local/bin/` as the installation path
    - Bash shell commands

    **Not for**:
        - macOS (uses different download file: `darwin-universal.tar.gz`)
        - Windows (uses `.zip` files and different paths like `C:\Hugo\bin\`)


    #### Hosting Platform

    **GitHub Pages** specifically
    - Uses GitHub Actions workflows (`.github/workflows/hugo.yaml`)
    - Works with both manual `.deb` package installation or `peaceiris/actions-hugo` action
    - Assumes the `Deploy Hugo site to Pages` workflow structure

    **Not for**:
    - Netlify (uses `netlify.toml` configuration)
    - Vercel (uses `vercel.json`)
    - AWS S3/CloudFront
    - Self-hosted servers
    - GitLab Pages (uses `.gitlab-ci.yml`)


    #### Architecture

    - **64-bit Linux** (`linux-amd64`)
    - If you're on ARM Linux (like Raspberry Pi), you'd need `linux-arm64.tar.gz` instead


    #### Key Linux-specific elements in the guide

    1. **File paths**: `/usr/local/bin/hugo`, `~/Downloads`
    2. **Commands**: `wget`, `tar`, `sudo`, `nano`, `ls`, `grep`
    3. **Permissions**: Uses `sudo` to install system-wide
    4. **Package format**: `.tar.gz` archives (Linux standard)
    5. **GitHub Actions runner**: Uses `ubuntu-latest` in workflows
    **If you are on a different operating system or hosting platform**, you need a modified version of this guide.

