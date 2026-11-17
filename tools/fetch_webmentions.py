#!/usr/bin/env python3
"""
Webmention receiver-display fetcher for Hugo static sites.

Fetches all webmentions collected by webmention.io for one or more
domains and writes a Hugo data file (data/webmentions.json) keyed by
site path, so the site can display minimal, link-only "Around the
web" backlinks.

Display philosophy (following V.H. Belvadi's pattern): link back to
the source with credit, embed nothing. No reply text, no avatars, no
content from the sender's page is ever copied or displayed.

Environment variables:
  SITE_URL   - Base URL of the site (default: https://bongotwisty.uk)
  WM_TOKEN   - API token from the webmention.io dashboard (REQUIRED)
  WM_DOMAINS - Comma-separated webmention.io site domains to query.
               Defaults to the site host plus the legacy
               bongotwisty.blog domains.
  DEBUG      - "1" prints a raw sample item and a summary of skipped
               items, to verify field names and diagnose the API.

Pagination: the JF2 feed silently clamps per_page to 20. A short page
is therefore NOT the end of the feed - only an EMPTY page is. The
fetcher pages until it receives no children (with a hard page cap).

Run from the repository root, BEFORE the hugo build:
  WM_TOKEN=xxx python3 tools/fetch_webmentions.py && hugo

Do NOT commit data/webmentions.json to the repo: it is regenerated on
every build, and incoming mentions change without the repo changing.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse, urlencode
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

# --- Config -------------------------------------------------------------

SITE_URL = os.environ.get("SITE_URL", "https://bongotwisty.uk").rstrip("/")
WM_TOKEN = os.environ.get("WM_TOKEN", "")
DEBUG = os.environ.get("DEBUG", "0") in ("1", "true", "yes")

DATA_PATH = Path("data/webmentions.json")

# The API clamps per_page to 20 whatever we ask for; the value here
# only shapes the request. Termination is by empty page, not length.
PER_PAGE = 20
MAX_PAGES = 100  # hard safety cap: 100 x 20 = 2000 mentions per domain
PAGE_TIMEOUT = 30

SITE_HOST = urlparse(SITE_URL).netloc.lower().split(":")[0].removeprefix("www.")

# Legacy domains that also belong to this site: mention targets filed
# under the old domain are ours too, and must be recognised as
# internal so they can be mapped to page paths for display.
LEGACY_HOSTS = {"bongotwisty.blog", "www.bongotwisty.blog"}

OUR_HOSTS = {SITE_HOST, "www." + SITE_HOST} | LEGACY_HOSTS

# Sources that should never be displayed. Test fixtures from
# webmention.rocks are functional pings, not editorial references;
# sources from our own domains are self-mentions.
EXCLUDE_SOURCE_DOMAINS = frozenset({"webmention.rocks"}) | OUR_HOSTS

WM_DOMAINS = [
    d.strip()
    for d in os.environ.get(
        "WM_DOMAINS",
        f"{SITE_HOST},bongotwisty.blog,www.bongotwisty.blog",
    ).split(",")
    if d.strip()
]

API_BASE = "https://webmention.io/api/mentions.jf2"

# Candidate fields that may carry the *target* URL (our page that was
# mentioned). The feed has been observed using different shapes over
# the years; accept any of these, string or first-of-list.
TARGET_KEYS = (
    "wm-target",
    "target",
    "mention-of",
    "in-reply-to",
    "like-of",
    "repost-of",
    "bookmark-of",
)

# Display verbs derived from the webmention property type.
VERB_BY_PROPERTY = {
    "mention-of": "discussed",
    "in-reply-to": "replied to",
    "like-of": "liked",
    "repost-of": "reposted",
    "bookmark-of": "bookmarked",
}

# Fediverse author names often carry instance-local emoji written as
# :shortcodes:, which render as literal ":debian:" clutter outside the
# fediverse. Strip them; real Unicode emoji (e.g. 🚲) are unaffected.
SHORTCODE_RE = re.compile(r"\s*:[a-z0-9_]+:\s*")


# --- Helpers -------------------------------------------------------------


def clean_author(name):
    """Strip :shortcode: emoji from a fediverse display name."""
    if not name:
        return name
    return SHORTCODE_RE.sub(" ", name).strip()


def first_url(value):
    """Coerce a field value (string or list) to a single string."""
    if isinstance(value, list):
        return value[0] if value else None
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and "url" in value:
        return value["url"]
    return None


def normalise_path(url: str):
    """
    Convert a target URL into the site-path key the Hugo partial will
    look up (matching .RelPermalink, i.e. pretty URLs with trailing
    slash). Tolerates the target having been stored under any host
    variant (legacy domain, www, http, etc).
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    path = parsed.path or "/"
    if path == "":
        path = "/"
    last = path.rstrip("/").rsplit("/", 1)[-1]
    if "." in last:  # file-like path such as /foo.html - leave as is
        return path
    if not path.endswith("/"):
        path += "/"
    return path


def host_of(url: str):
    try:
        return urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return None


# --- Fetch ---------------------------------------------------------------


def api_url(domain: str, page: int):
    params = urlencode(
        {"token": WM_TOKEN, "domain": domain, "per_page": PER_PAGE, "page": page}
    )
    return f"{API_BASE}?{params}"


def fetch_page(url: str):
    """Fetch one page of the JF2 feed. Returns the parsed JSON dict."""
    try:
        with urlopen(url, timeout=PAGE_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        print(f"HTTP error from webmention.io: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Network error reaching webmention.io: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print("webmention.io returned something that is not JSON.", file=sys.stderr)
        sys.exit(1)


def fetch_all_mentions(domain: str):
    """
    Gather every mention for a domain.

    The API clamps per_page (to 20) regardless of what we request,
    so page length tells us nothing about completeness. The only
    reliable end signal is an empty page, so we keep paging until
    one comes back with no children (or the safety cap is hit).

    Note: if the mention total is an exact multiple of the page size,
    the final request returns an empty page and costs one extra call.
    That is acceptable.
    """
    all_children = []
    for page in range(1, MAX_PAGES + 1):
        raw = fetch_page(api_url(domain, page))
        children = raw.get("children", [])
        if page == 1 and DEBUG and children:
            print("--- RAW SAMPLE ITEM (DEBUG) ---")
            print(json.dumps(children[0], indent=2)[:2000])
            print("--------------------------------")
        if not children:
            break
        all_children.extend(children)
        if page == MAX_PAGES:
            print(
                f"WARN: hit page cap ({MAX_PAGES}) for {domain}; "
                f"fetch may be incomplete.",
                file=sys.stderr,
            )
    return all_children


# --- Parse ---------------------------------------------------------------


def parse_item(item):
    """Return (path_key, display_dict) or None if the item is skipped."""

    source_url = first_url(item.get("url"))
    if not source_url:
        return None

    # Verified/private guards. Older feeds may omit these; only skip
    # when explicitly marked unverified or private.
    if item.get("wm-verified") is False:
        return None
    if item.get("wm-private"):
        return None

    source_host = host_of(source_url) or ""
    if source_host in EXCLUDE_SOURCE_DOMAINS:
        return None

    # Locate the target: the first candidate field holding a URL on
    # one of our own domains (current or legacy).
    target_url = None
    for key in TARGET_KEYS:
        value = first_url(item.get(key))
        if not value:
            continue
        if host_of(value) in OUR_HOSTS:
            target_url = value
            break
    if target_url is None:
        if DEBUG:
            print(f"SKIP (no target found): {source_url}")
        return None

    path_key = normalise_path(target_url)
    if path_key is None:
        return None

    # Author: an h-card dict in most feeds.
    author = None
    author_data = item.get("author")
    if isinstance(author_data, dict):
        author = author_data.get("name") or None
    elif isinstance(author_data, str):
        author = author_data or None
    author = clean_author(author)

    prop = item.get("wm-property") or "mention-of"
    verb = VERB_BY_PROPERTY.get(prop, "discussed")

    ts = item.get("wm-received") or item.get("published") or ""

    display = {
        "url": source_url,
        "author": author,
        "host": source_host.removeprefix("www."),
        "type": verb,
        "ts": ts,
    }
    return path_key, display


# --- Main ---------------------------------------------------------------


def main():
    if not WM_TOKEN:
        print(
            "WM_TOKEN is not set. Copy the token from your webmention.io "
            "dashboard and pass it via the WM_TOKEN environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    by_path = {}
    seen = set()
    total_received = 0

    for domain in WM_DOMAINS:
        children = fetch_all_mentions(domain)
        total_received += len(children)
        print(f"{domain}: received {len(children)} mentions.")

        for item in children:
            parsed = parse_item(item)
            if parsed is None:
                continue
            path_key, display = parsed
            dedupe_key = (display["url"], path_key, display["type"])
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            by_path.setdefault(path_key, []).append(display)

    # Stable ordering: oldest first within each page
    for path_key in by_path:
        by_path[path_key].sort(key=lambda d: d["ts"] or "")

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(dir=str(DATA_PATH.parent), suffix=".tmp")
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
        json.dump(by_path, f, indent=2, sort_keys=True)
    os.replace(tmp_name, DATA_PATH)

    pages = len(by_path)
    mentions = sum(len(v) for v in by_path.values())
    print(
        f"Fetched {total_received} mentions across {len(WM_DOMAINS)} domains; "
        f"wrote {mentions} displayable mentions across {pages} pages "
        f"to {DATA_PATH}."
    )


if __name__ == "__main__":
    main()
