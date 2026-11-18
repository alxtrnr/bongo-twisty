# Bongo Twisty

A personal Hugo blog built on Codefloe, deployed by Crow CI and served by Statichost.eu at [bongotwisty.uk](https://bongotwisty.uk).

The legacy domain bongotwisty.blog redirects here (path-preserving) but hosts nothing.

## Quick Start

Install npm dependencies (for PostCSS)
```
npm install
```
Initialize Hugo submodule (theme)
```
git submodule update --init --recursive
```
Run development server with drafts
```
hugo server -D
```
Build site for production
```
hugo --gc --minify
```

## Configuration

| Setting | Value |
| -------- | -------- |
| Hugo Version | v0.164.0-extended |
| Theme | hugo-simple (Git submodule) |
| Output Directory | public/ |
| Canonical Domain | bongotwisty.uk |

## Deployment Architecture

Single endpoint, single forge, single CI chain.

| Component | Detail |
| -------- | -------- |
| Git forge | Codefloe — `git@codefloe.com:BongoTwisty/bongo-twisty.git` |
| CI | Crow CI (`.crow/build.yaml`) — builds on push to main |
| Hosting | Statichost.eu (builder: `builder.statichost.eu/bongotwisty/`) |
| Canonical URL | `https://bongotwisty.uk` (www subdomain redirects to apex) |
| Legacy domain | bongotwisty.blog — GitHub Pages forwarding + path-preserving redirects at the registrar |

### What Happens on Push

A push to main on Codefloe triggers the Crow pipeline:

1. Builds Hugo site with `--gc --minify`
2. Runs Pagefind 1.3.0 for search indexing
3. Sends webmentions (incremental mode)
4. Pushes built site to the pages branch in the same repo

Statichost.eu serves the content from the pages branch. A forced redeploy can be triggered with an empty commit:

```
git commit --allow-empty -m "rebuild" && git push
```

## Project Structure
```
bongo-twisty/
├── .crow/build.yaml       # Crow CI pipeline
├── archetypes/            # Content templates
├── assets/                # Source assets (CSS/JS)
├── content/               # Blog posts and pages
├── data/                  # Committed data files (webmention history)
├── layouts/               # Custom template overrides
├── static/                # Static files (copied directly)
├── tools/                 # Webmention sender and receiver
├── themes/                # Hugo Simple theme (submodule)
├── .gitmodules            # Submodule definitions
├── hugo.toml              # Main configuration
├── package.json           # npm dependencies
└── webmention-sent.json   # Sender cache (Git-tracked, v2 format)
```

## Webmentions

### Sending — tools/send_webmentions.py

W3C Webmention spec-compliant sender. Runs incrementally on every CI push, or manually in full mode.

**How it works:**

* Scans generated HTML for external links
* Internal link targets are classified and skipped via the `INTERNAL_HOSTS` set
* Discovers webmention endpoints on target sites (following redirects)
* Accepts any 2xx response as delivered
* Sends update re-sends when previously-mentioned targets are re-linked
* Sends deletion notices when links disappear from updated pages
* Dry-run mode filters legacy hosts and is watertight: nothing sent, cache untouched
* Caches results in `webmention-sent.json` (Git-tracked, v2 format, domain-migrated)

**Running locally:**
```
# Full scan of all content
SITE_URL="https://bongotwisty.uk" MODE=full python3 tools/send_webmentions.py

# Incremental (recent commits)
SITE_URL="https://bongotwisty.uk" MODE=incremental python3 tools/send_webmentions.py

# Dry run (audit only, no sends, no cache writes)
SITE_URL="https://bongotwisty.uk" MODE=full DRY_RUN=true python3 tools/send_webmentions.py
```

### Receiving — tools/fetch_webmentions.py

Three-source receiver with an un-losable history design:

1. `data/webmentions-archive.jf2.json` — committed JF2 export from webmention.io, ground truth
2. `data/webmentions-supplement.json` — 19 hand-restored mentions recovered after the domain migration
3. Live webmention.io API feed — can only add entries, never remove or override the archive

Merged output lands in `data/webmentions.json`, keyed by page path, which the `around-the-web.html` partial renders (link-only display, authors credited, nothing embedded).

The webmention.io inbox is registered under the apex domain `bongotwisty.uk`; the legacy www.bongotwisty.blog account (~195 mentions) was merged into it via webmention.io's account merge.

Authentication: token read from `WM_TOKEN` (locally `~/.config/webmention_token`; in Crow CI passed as a `from_secret`).

## Templates and Shortcodes

### Image Handling

Images are handled by a custom render hook (`layouts/_default/markup/render-image.html`) that intercepts all standard Markdown image syntax and applies automatic processing.

Basic usage (uses page resources, resizes to 600px width, enables GLightbox):
```
![Alt text](image.jpg)
![Alt text](image.jpg "Caption text")
```

Advanced usage (JSON parameters in title for per-image control):
```
![Alt text](banner.jpg '{"resize": "1200x400 Smart", "title": "Hero Banner"}')
![Alt text](photo.jpg '{"gallery": "/gallery/events", "resize": "800x600"}')
```

**JSON parameter options:**

| Parameter | Purpose | Default |
| -------- | -------- | -------- |
| title | Caption displayed below image | Empty |
| gallery | Gallery page path for resource fallback | /gallery |
| resize | Hugo image processing string | 600px |

**Resource lookup order:** Page bundle → gallery page → global assets directory.

In development (hugo server), missing images show a detailed error panel listing all searched locations. In production, a fallback image renders with a minimal warning.

**Configuration (in hugo.toml):**
```
[markup.goldmark.parser]
wrapStandAloneImageWithinParagraph = false

[markup.goldmark.parser.attribute]
title = true

[params.imageProcessing]
defaultGallery = "/gallery"
defaultResize = "600x"
enableGlobalFallback = true
lightbox = true
```

## Shortcodes

### BANDCAMP
Embeds a Bandcamp album or track player.

**Usage:**
```
{{< bandcamp src="..." link="..." title="..." >}}
```

| Parameters | Required | Description |
| -------- | -------- | -------- |
| src | Yes | Bandcamp embed iframe URL |
| link | Yes | Fallback hyperlink to the album/track |
| title | Yes | Display text for the fallback link |

### CENTER
Centres any wrapped content. Supports full Markdown inside.

**Usage:**
```
{{< center >}}
### Centered Heading
Centered text.
{{< /center >}}
```

**Parameters:** None. Wraps inner content in a centred `<div>`.

### DIVIDER
Renders a centred decorative text-based divider. No parameters.

**Usage:**
```
{{< divider >}}
```

Output: •• ━━━━━ ••●•• ━━━━━ ••

### GLIGHTBOX-FIGURE
Displays an image from the current page bundle in a GLightbox figure with caption. Shows a visible warning if the image is not found.

**Usage:**
```
{{< glightbox-figure src="my-photo.jpg" title="A lovely view" alt="..." >}}
```

| Parameters | Required | Description |
| -------- | -------- | -------- |
| src | Yes | Filename of image in page bundle |
| title | Yes | Caption shown below image and in lightbox |
| alt | Yes | Alt text (defaults to title) |

Resizes to 600px width. Groups images into `data-gallery="gallery"`.

### GLIGHTBOX-FIGURE-GLOBAL
Like glightbox-figure but with three-step resource lookup: page bundle → specified gallery page → global assets.

**Usage:**
```
{{< glightbox-figure-global src="shared-photo.jpg" caption="..." alt="..." >}}
```

| Parameters | Required | Description |
| -------- | -------- | -------- |
| src | Yes | Image filename or path |
| caption | No | Caption (falls back to image Title) |
| alt | No | Alt text (falls back to caption) |

Creates a 400×300 Smart thumbnail for display, links to full-resolution image in lightbox.

### IMAGE
Simple figure wrapper with optional caption. No lightbox, no image processing.

**Usage:**
```
{{< image src="diagram.png" alt="..." caption="..." title="..." >}}
```

| Parameters | Required | Description |
| -------- | -------- | -------- |
| src | Yes | Path to image (relative or absolute) |
| alt | Yes | Alt text for accessibility |
| caption | No | Caption below image (Markdown supported) |
| title | No | Hover tooltip text |

### IMG
Resized image from page bundle. Hard-fails with error if the image is not found (stops the build). Useful when missing images should break the build rather than silently render a placeholder.

**Usage:**
```
{{< img src="header.jpg" alt="..." >}}
```

| Parameters | Required | Description |
| -------- | -------- | -------- |
| src | Yes | Filename in page bundle |
| alt | Yes | Alt text for accessibility |

Resizes to 1200px width. Outputs width and height attributes.

### PDF
Embeds a PDF document using an `<object>` tag with a download fallback.

**Usage:**
```
{{< pdf src="/documents/report.pdf" height="800px" width="100%" >}}
```

| Parameters | Required | Default | Description |
| -------- | -------- | -------- | ------- |
| src | Yes | — | Path to PDF file |
| height | No | 600px | Height of the embed area |
| width | No | 100% | Width of the embed area |

### RUMBLE
Embeds a Rumble video.

**Usage:**
```
{{< rumble id="v123abc" pub="4pbo88" title="My Video Title" >}}
```

| Parameters | Required | Default | Description |
| -------- | -------- | -------- | ------- |
| id | Yes | — | Rumble video ID |
| pub | No | 4pbo88 | Rumble publisher ID |
| title | No | Rumble video | Accessibility title for iframe |

### RWGPSIMG
Renders an image from the RideWithGPS recap gallery, organised by year.

**Usage:**
```
{{< rwgpsimg year="2016" name="y_2016_RWGPS.webp" alt="..." class="..." >}}
```

| Parameters | Required | Default | Description |
| -------- | -------- | -------- | ------- |
| year | Yes | — | Year subdirectory under /gallery/cycling/rwgps_recap/ |
| name | Yes | — | Image filename |
| alt | No | empty | Alt text |
| class | No | empty | CSS class for the `<img>` tag |

### STRAVA-CHALLENGES
Renders a responsive grid gallery of Strava challenges from the page's front matter. Includes inline CSS, GLightbox integration, and mobile-responsive single-column layout.

Front matter structure (in the content file):
```
challenges:
    name: "January Ride"
    date: "Jan 2025"
    stat: "125 km"
    goal: "Goal: 200 km"
    image: "strava-jan.jpg"
    url: "https://strava.com/challenges/123"
    activity: "https://strava.com/activities/456"
```

**Usage:**
```
{{< strava-challenges >}}
```

No parameters — reads from `.Page.Params.challenges`. Creates 200×200 thumbnails for display and 300×300 for lightbox. Each challenge card shows the image, date, name (linked if url provided), stats, and an optional activity link.

### YOUTUBE
Full-featured YouTube embed with privacy controls. Supports both positional and named arguments.

**Simple usage:**
```
{{< youtube 0RKpf3rK57I >}}
```

**Advanced usage:**
```
{{< youtube id=0RKpf3rK57I loading=lazy start=30 title="My Tutorial" >}}
```

| Parameters | Default | Description |
| -------- | -------- | -------- |
| id | — | YouTube video ID (required) |
| title | YouTube video | Accessibility title for iframe |
| loading | eager | eager or lazy |
| start | 0 | Start time in seconds |
| end | 0 | End time in seconds (0 = no limit) |
| autoplay | false | Auto-plays (forces mute) |
| mute | false | Mutes audio |
| loop | false | Loops indefinitely |
| controls | true | Shows player controls |
| allowFullScreen | true | Allows fullscreen mode |
| class | empty | CSS class for wrapper div (removes inline styles) |

Respects hugo.toml privacy settings (privacyYouTube). Uses `youtube-nocookie.com` when privacy-enhanced mode is enabled.

## Partials

| Partial | Purpose |
| -------- | -------- |
| analytics.html | Injects GoatCounter analytics |
| custom_head.html | Extension point for additional `<head>` content (incl. webmention endpoint link) |
| email-comment.html | Email-based comment CTA (LetterBird) |
| favicon.html | Favicon with cache-busting parameter |
| footer.html | Footer with webring widgets, copyright, GLightbox JS |
| hcard.html | hCard microformat for author identity |
| hcard-home.html | Extended hCard variant for homepage |
| header.html | Custom header override |
| listenbrainz.html | ListenBrainz now-playing widget |
| nav.html | Navigation menu |
| pagination.html | Pagination with semantic `<a>`/`<span>` switching |
| seo_tags.html | OpenGraph and meta tags |
| theme-toggle.html | Dark/light theme switcher |

## Layouts

| Layout | Purpose |
| -------- | -------- |
| 404.html | Custom 404 page |
| _default/baseof.html | Base template override |
| _default/home.html | Homepage layout |
| _default/list.html | List/section pages with year-based pagination skip |
| _default/search.html | Search page (Pagefind integration) |
| _default/single.html | Single post layout |
| _default/single.vcard.vcf | vCard output format for author contact |
| gallery/list.html | Gallery section list page |
| gallery/single.html | Individual gallery page |
| pages/list.html | Static pages section |
| posts/list.html | Blog posts section with archive grouping |
| robots.txt | Dynamic robots.txt template |

## Theme Management

The theme is a Git submodule at themes/hugo-simple:

Update theme to latest
```
git submodule update --remote --merge
```

View theme commit hash
```
git ls-tree HEAD themes/hugo-simple
```

## Dependencies

* **npm:** PostCSS processing (postcss, postcss-cli)
* **Go modules:** ListenBrainz integration (hugo-module-listenbrainz)
* **Node.js:** Pagefind search indexer

Install after cloning:
```
npm install
git submodule update --init --recursive
```

## Environment Variables

Set in `.crow/build.yaml` during build:

| Variable | Value |
| -------- | -------- |
| HUGO_ENVIRONMENT | production |
| TZ | Europe/London |
| SITE_URL | https://bongotwisty.uk |
| WM_DOMAIN | www.bongotwisty.uk |
| wm_token | webmention.io API token (from_secret) |

## Monitoring Builds

| Platform | Status |
| -------- | -------- |
| Codefloe Crow CI | [CI](https://ci.crowci.dev/BongoTwisty/bongo-twisty) |
| Statichost builder | [builder.statichost.eu/bongotwisty/](https://builder.statichost.eu/bongotwisty/) |

## Contributing / Forking

If you fork this blog:

1. Update the baseURL and hcard_url in hugo.toml
2. Set SITE_URL and WM_DOMAIN in the CI pipeline
3. Register your own webmention.io inbox and update the endpoint in layouts/partials/custom_head.html
4. Delete webmention-sent.json and the data/webmentions-* files to start with a clean slate, or keep them out of your repo
5. Configure the webmention.io API token as a CI secret

## License

* **Blog content** (posts, images, etc.): CC BY-SA 4.0 (see [Creative Commons](https://creativecommons.org/licenses/by-sa/4.0/))
* **Infrastructure code** (scripts, configs, templates): MIT License (see [LICENSE](LICENSE))
* **Theme** (hugo-simple): Licensed separately under its own terms
