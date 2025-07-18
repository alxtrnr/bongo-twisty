+++
title = "Git & Hugo Blog Workflow: Aide-Mémoire"
description = "A concise aide-mémoire for managing your Hugo blog using Git."
date = 2025-07-07T13:32:00+01:00
draft = false
tags = []
toc = false
+++

## Git \& Hugo Blog Workflow: Aide-Mémoire

This guide covers the essential Git commands for my routine Hugo development workflow, from making local changes to deploying them live.

### The Golden Rule: Pull, Then Push

Because I work across two laptops, I must always follow this rule to keep them synchronized and avoid conflicts:

1. **PULL** changes from GitHub before you start working.
2. **PUSH** your changes to GitHub when you are finished.

### 1. Starting a Work Session

Before making any edits, always pull the latest version of your site from GitHub. This ensures you have any changes you might have pushed from your other machine.

```bash
# Fetch and merge changes from the remote 'main' branch
git pull origin main
```


### 2. The Local Development Cycle

This is the process you'll follow every time you add or edit content.

#### Step A: Preview Your Site Locally

Run the Hugo server to see a live preview of your site. This allows you to check your changes before they go live.

```bash
# Start the Hugo development server
hugo server
```

Your site will be available at `http://localhost:1313/`. The server will automatically refresh the page as you save files.

#### Step B: Check the Status of Your Changes

Use `git status` to see a summary of your work. It will show you:

- **Modified files**: Files you have edited.
- **Untracked files**: New files you have created (like a new blog post).

```bash
# See the current status of your repository
git status
```


#### Step C: Stage Your Changes

"Staging" is how you tell Git which changes you want to include in your next save point (commit).

```bash
# To stage ALL changes (modified and new files)
git add .

# To stage only a specific file
git add path/to/your/file.md
```


#### Step D: Commit Your Changes

A "commit" is a snapshot of your staged changes. It saves them to your local repository's history with a descriptive message.

```bash
# Commit your staged changes with a clear message
git commit -m "Docs: Update a blog post about Git"
```

*Good commit messages are helpful. Common prefixes include `Feat:` (new feature), `Fix:` (a bug fix), `Docs:` (documentation), or `Content:` (adding or editing content).*

### 3. Deploying Your Changes to the Live Site

To deploy your site, simply push your local commits to GitHub. This action will automatically trigger the GitHub Actions workflow to rebuild and publish your site.

```bash
# Push your committed changes to the 'main' branch on GitHub
git push origin main
```

After pushing, you can go to the **Actions** tab in your GitHub repository to watch the deployment process. Once it completes with a green checkmark, your changes are live.

### A Complete Workflow Example: Adding a New Post

Here is the entire process from start to finish for adding a new blog post.

```bash
# 1. Start your session by getting the latest updates
git pull origin main

# 2. Create a new blog post file using Hugo's command
hugo new content posts/my-awesome-new-post.md

# 3. Start the local server to preview as you write
hugo server

# 4. Edit your new markdown file in your text editor...
# (After editing and saving the file, you're ready to commit)

# 5. Stage the new post for commit
git add .

# 6. Save your work with a commit message
git commit -m "Content: Add new post on advanced Hugo techniques"

# 7. Push to GitHub to deploy the new post
git push origin main
```

