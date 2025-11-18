# bongo-twisty

Hugo blog deployed via GitHub Pages.

## Quick Start

```bash
# Install npm dependencies (for PostCSS/Tailwind)
npm install

# Run development server with drafts
hugo server -D

# Build site for production
hugo --minify
```

## Configuration

- **Theme**: Hugo Simple (via Git submodule)
- **Hugo Version**: Checked automatically by GitHub Actions workflow
- **Output Directory**: `public/`
- **License**: MIT

## Project Structure

```
bongo-twisty/
├── .github/
│   └── workflows/       # GitHub Actions (deployment + Hugo version check)
├── archetypes/          # Content templates
├── assets/              # Source assets (CSS/JS processed by Hugo Pipes)
├── content/             # Blog posts and pages
├── layouts/             # Custom template overrides
├── static/              # Static files (copied directly to public/)
├── themes/              # Hugo Simple theme (Git submodule)
├── hugo.toml            # Main configuration file
├── package.json         # npm dependencies
└── postcss.config.js    # PostCSS configuration
```

## Deployment

Site builds and deploys automatically to GitHub Pages via GitHub Actions on push to `main` branch.

The workflow:
- Builds the Hugo site with `--minify`
- Deploys to GitHub Pages
- Runs a Hugo version check

## Development Notes

### Working with Content
- Create new posts: `hugo new content/posts/my-post.md`
- Draft posts are excluded from production builds (omit `-D` flag)

### Theme Management
- Theme is installed as a Git submodule in `themes/hugo-simple`
- Update theme: `git submodule update --remote --merge`

### Dependencies
- npm packages are used for PostCSS processing
- Run `npm install` after cloning the repository

## License

MIT License - See [LICENSE](LICENSE) file for details.
