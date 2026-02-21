+++
title = "Webmentions"
description = "How this site sends and receives Webmentions."
date = 2026-02-21T00:00:00
draft = false
url = "/webmentions/"
+++

This site supports [Webmentions](https://indieweb.org/Webmention). If your site sends Webmentions and you link to a page here, your mention should be delivered to my Webmention endpoint.

**Receiving**

I use [webmention.io](https://webmention.io) as an inbox for this space:

- Endpoint: `https://webmention.io/bongotwisty.blog/webmention`
- The endpoint is advertised via a `<link rel="webmention">` tag in the HTML `<head>` of each page.

I’m not currently rendering Webmentions publicly on posts. I check them via the webmention.io dashboard and may follow links or respond, but they’re not shown as a visible comments thread.

**Sending**

This is a static site built with Hugo and deployed via GitHub Pages. Outgoing Webmentions are sent automatically as part of the publish pipeline:

- After Hugo builds the site, a Python script runs on each deploy.
- It looks at Markdown content files that changed in the latest commits, maps them to their generated HTML pages, and scans those pages for external links.
- For each external link, it:
  - Checks for a Webmention endpoint on the target (HTTP `Link` headers or `<link rel="webmention">` in the HTML).
  - Sends a Webmention (`source` = my post URL, `target` = your URL) if an endpoint is found.
  - Records `source:target` pairs in a local JSON cache so the same Webmention is not re-sent on future builds.

To keep the noise down:

- Only posts whose source files have actually changed are considered on each deploy.
- There is a cap on how many new Webmentions are sent per run.
- Content prior to 2017 is ignored for automated catch-up.

**Expectations**

If you run a Webmention-aware site or use a service like [Micro.blog](https://micro.blog) or webmention.io for your own domain, linking here should result in a Webmention being delivered to my endpoint. Likewise, when I link to your Webmention enabled posts from newer content, my site will attempt to notify you once via Webmention as part of the build process.

**Why I’m using Webmentions**

I see Webmentions as a lightweight way to have cross-site conversations without depending on a single social platform. By adding them to my Hugo + GitHub Pages workflow, I can:

- Acknowledge other people’s writing when I link to them from newer posts, without manually sending notifications.
- Give Webmention enabled sites a quiet, one-time signal that I’ve referenced their work, which they can choose to display, archive, or ignore as they see fit.
- Keep my own site simple and static while still participating in a small social layer on the web.

At the moment I’m using Webmentions mainly for discovery and personal awareness. That may evolve over time into a public comment system, but for now the goal is to support and take part in the broader IndieWeb ecosystem in a low-noise, respectful way.

