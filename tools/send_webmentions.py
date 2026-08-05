#!/usr/bin/env python3
"""
Webmention sender for Hugo static sites.

Sends W3C Webmentions (https://www.w3.org/TR/webmention/) for external
links found in generated HTML. Supports full and incremental (git-based)
modes. Designed to run in CI pipelines (GitHub Actions, Woodpecker/Codeberg).

Configuration via environment variables:
  SITE_URL  - Base URL of the site (default: https://bongotwisty.blog)
  MODE      - "full" or "incremental" (default: incremental)

Cache file (webmention-sent.json) should be committed to the repo
so it persists between CI runs.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone, date

# --- Config -------------------------------------------------------------

# [FIX 1] Read SITE_URL from environment so the script works correctly
# regardless of which CI platform (GitHub or Codeberg) is running it.
# Falls back to the production custom domain for local use.
SITE_URL = os.environ.get("SITE_URL", "https://bongotwisty.blog").rstrip("/")
PUBLIC_DIR = Path("public")
CACHE_PATH = Path("webmention-sent.json")
MAX_PER_RUN = 20  # cap for incremental mode
CUTOFF_DATE = date(2017, 1, 1)  # only consider content from 2017-01-01 onwards

# [FIX 4] Non-editorial link exclusion.
# Domains that appear in site chrome (footers, sidebars) rather than
# content. These should not receive webmentions because they are
# navigation widgets, not editorial references.
EXCLUDE_DOMAINS = frozenset({
    "xn--sr8hvo.ws",   # IndieWeb webring — redirects to random members
    "fediring.net",    # Fediring — same issue
})

# --- Simple HTML link extractor -----------------------------------------


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = None
        for k, v in attrs:
            if k.lower() == "href":
                href = v
                break
        if href:
            self.links.append(href)


def extract_links_from_file(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    parser = LinkExtractor()
    parser.feed(text)
    return parser.links


# --- Cache handling -----------------------------------------------------


def load_cache():
    if CACHE_PATH.exists():
        try:
            with CACHE_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache):
    tmp = CACHE_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True)
    tmp.replace(CACHE_PATH)


def cache_key(source, target):
    return f"{source} {target}"


# --- Link filtering -----------------------------------------------------


def is_external_link(href: str):
    """Return True if href is an absolute external http(s) link."""
    if not href or href.startswith("#"):
        return False
    parsed = urlparse(href)
    # relative URL
    if not parsed.scheme:
        return False
    if not parsed.netloc:
        return False
    # absolute, but internal
    # [FIX 1] Use the configurable SITE_URL instead of a hardcoded string
    if href.startswith(SITE_URL):
        return False
    return parsed.scheme in ("http", "https")


def is_excluded_link(url: str):
    """
    [FIX 4] Check if a URL belongs to an excluded (non-editorial) domain.
    These are webring redirectors and other site-chrome links that
    should not receive webmentions.
    """
    try:
        netloc = urlparse(url).netloc.lower()
        # Strip port if present
        if ":" in netloc:
            netloc = netloc.split(":")[0]
        return any(
            netloc == domain or netloc.endswith("." + domain)
            for domain in EXCLUDE_DOMAINS
        )
    except Exception:
        return False


def should_send_webmention(href: str):
    """Combined filter: must be external AND not excluded."""
    return is_external_link(href) and not is_excluded_link(href)


# --- Utilities ----------------------------------------------------------


def html_path_to_url(path: Path):
    # path is under PUBLIC_DIR
    rel = path.relative_to(PUBLIC_DIR)
    # index.html at root
    if rel == Path("index.html"):
        return SITE_URL + "/"
    # .../index.html
    if rel.name == "index.html":
        url_path = "/" + str(rel.parent).strip("/")
        if not url_path.endswith("/"):
            url_path += "/"
        return SITE_URL + url_path
    # other .html
    return SITE_URL + "/" + str(rel)


def run_curl(args):
    """Run curl, return (exit_code, stdout_str, stderr_str)."""
    proc = subprocess.run(
        ["curl", "--max-time", "10"] + args,  # 10-second timeout
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    def safe_decode(b):
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            return b.decode("latin-1", errors="replace")

    return proc.returncode, safe_decode(proc.stdout), safe_decode(proc.stderr)


# --- Discover Webmention endpoint --------------------------------------


def _extract_href_from_tag(tag_html: str, target_url: str):
    """
    [FIX 3] Extract a webmention endpoint href from an HTML tag string.
    Returns the absolute URL if found, otherwise None.
    Shared between <link> and <a> tag parsing.
    """
    href_pos = tag_html.lower().find("href=")
    if href_pos == -1:
        return None
    quote = tag_html[href_pos + 5]
    if quote not in ("'", '"'):
        return None
    end_href = tag_html.find(quote, href_pos + 6)
    if end_href == -1:
        return None
    href = tag_html[href_pos + 6 : end_href]
    # Make absolute if needed
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(target_url, href)


def discover_endpoint(target_url: str):
    # 1) try HTTP headers
    code, headers, _ = run_curl(["-sI", "-H", "Accept-Encoding: identity", target_url])
    if code == 0:
        for line in headers.splitlines():
            if line.lower().startswith("link:"):
                # crude parse for rel="webmention"
                # e.g. Link: <https://example.com/webmention>; rel="webmention"
                parts = line.split(": ", 1)[-1].split(",")
                for part in parts:
                    if 'rel="webmention"' in part:
                        start = part.find("<")
                        end = part.find(">", start + 1)
                        if start != -1 and end != -1:
                            return part[start + 1 : end]

    # 2) try HTML <link rel="webmention"> and <a rel="webmention">
    code, body, _ = run_curl(["-sL", "-H", "Accept-Encoding: identity", target_url])
    if code != 0:
        return None

    lower = body.lower()
    idx = 0
    while True:
        idx = lower.find('rel="webmention"', idx)
        if idx == -1:
            break

        # [FIX 3] Search backwards for either <link or <a tag
        link_start = lower.rfind("<link", 0, idx)
        a_start = lower.rfind("<a", 0, idx)

        # Use whichever tag is closer and still contains our position
        tag_start = max(link_start, a_start)
        if tag_start == -1:
            idx += 15
            continue

        tag_end = lower.find(">", idx)
        if tag_end == -1:
            break

        tag_html = body[tag_start:tag_end]
        href = _extract_href_from_tag(tag_html, target_url)
        if href:
            return href

        idx = tag_end

    return None


# --- Send Webmention ----------------------------------------------------


def send_webmention(source_url: str, target_url: str, endpoint_url: str):
    """
    [FIX 2] Return a tuple (status, message) where status is one of:
      - True:   successfully sent (2xx)
      - "gone": target is permanently gone (410/404)
      - False:  transient failure or unexpected error
    The caller caches True results, skips "gone" results (don't cache,
    will retry next run in case of temporary issue), and retries False.
    """
    data = f"source={source_url}&target={target_url}"
    code, out, err = run_curl([
        "-s",
        "-o", "/dev/null",
        "-w", "%{http_code}",
        "-X", "POST",
        "-d", data,
        endpoint_url,
    ])

    if code != 0:
        return False, (err.strip() or "curl error")

    try:
        http_status = int(out.strip())
    except ValueError:
        return False, f"unexpected output: {out.strip()}"

    if 200 <= http_status < 300:
        return True, f"HTTP {http_status}"
    elif http_status in (404, 410):
        return "gone", f"HTTP {http_status}"
    elif http_status == 429:
        return False, f"HTTP {http_status} (rate limited)"
    else:
        return False, f"HTTP {http_status}"


# --- Process a single HTML file ----------------------------------------


def process_html_file(html_path: Path, cache: dict, mode_label: str, sent_counter: list):
    """
    Extract external links from an HTML file and send webmentions for
    any that haven't been cached.

    Uses a mutable list for sent_counter so it can be updated across
    the caller's iteration without returning.

    Returns: number of new webmentions sent from this file.
    """
    source_url = html_path_to_url(html_path)
    links = extract_links_from_file(html_path)
    sent_from_file = 0

    for href in links:
        # [FIX 4] Combined filter: external + not excluded
        if not should_send_webmention(href):
            continue

        target_url = href
        key = cache_key(source_url, target_url)
        if key in cache:
            continue

        endpoint = discover_endpoint(target_url)
        if not endpoint:
            continue

        ok, msg = send_webmention(source_url, target_url, endpoint)

        if ok is True:
            sent_from_file += 1
            cache[key] = datetime.now(timezone.utc).isoformat()
            print(f"SENT ({mode_label}): {source_url} -> {target_url} via {endpoint}")
        elif ok == "gone":
            print(f"GONE ({mode_label}): {source_url} -> {target_url}: {msg}")
        else:
            print(
                f"FAIL ({mode_label}): {source_url} -> {target_url}: {msg}",
                file=sys.stderr,
            )

    return sent_from_file


# --- Mode: full ---------------------------------------------------------


def full_mode(cache):
    sent_this_run = 0
    for html_path in PUBLIC_DIR.rglob("*.html"):
        # Skip very old pages based on HTML mtime
        mtime = datetime.fromtimestamp(html_path.stat().st_mtime, tz=timezone.utc).date()
        if mtime < CUTOFF_DATE:
            continue

        sent_this_run += process_html_file(html_path, cache, "full", [])

    print(f"Full mode done, sent {sent_this_run} new webmentions.")
    return cache


# --- Mode: incremental (git-based) -------------------------------------


def get_changed_content_files():
    # Look at last 10 commits as a simple window
    cmd = ["git", "diff", "--name-only", "HEAD~10", "HEAD"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        return []
    files = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("content/"):
            files.append(Path(line))
    return files


def content_to_public_path(content_path: Path):
    """
    Map content paths to their public HTML paths.
    - posts: content/posts/foo.md -> public/foo/index.html  (permalinks setting)
    - everything else: content/section/slug.md -> public/section/slug/index.html
    """
    rel = content_path.relative_to("content")
    if rel.suffix in (".md", ".html"):
        rel = rel.with_suffix("")

    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "posts":
        # posts live at /<slugorcontentbasename>/ according to hugo.toml
        slug = parts[-1]
        return PUBLIC_DIR / slug / "index.html"

    # default: /section/slug/index.html
    return PUBLIC_DIR / rel / "index.html"


def incremental_mode(cache):
    changed_content = get_changed_content_files()
    if not changed_content:
        print("No changed content files detected, nothing to do.")
        return cache

    # Filter out very old content files by mtime
    recent_content = []
    for content_path in changed_content:
        if not content_path.exists():
            continue
        mtime = datetime.fromtimestamp(content_path.stat().st_mtime, tz=timezone.utc).date()
        if mtime >= CUTOFF_DATE:
            recent_content.append(content_path)

    if not recent_content:
        print("No changed content newer than cutoff date, nothing to do.")
        return cache

    sent_this_run = 0
    processed_sources = set()

    for content_path in recent_content:
        html_path = content_to_public_path(content_path)
        if not html_path.exists():
            continue
        source_url = html_path_to_url(html_path)
        if source_url in processed_sources:
            continue
        processed_sources.add(source_url)

        sent_this_run += process_html_file(html_path, cache, "incremental", [])

        if sent_this_run >= MAX_PER_RUN:
            print(f"Reached MAX_PER_RUN={MAX_PER_RUN}, stopping for this run.")
            save_cache(cache)
            return cache

    print(f"Incremental mode done, sent {sent_this_run} new webmentions.")
    return cache


# --- Main ---------------------------------------------------------------


def main():
    mode = os.environ.get("MODE", "incremental").lower()
    cache = load_cache()

    if mode == "full":
        cache = full_mode(cache)
    else:
        cache = incremental_mode(cache)

    save_cache(cache)


if __name__ == "__main__":
    main()