#!/usr/bin/env python3
"""
Webmention receiver-display fetcher for Hugo static sites.

Fetches all webmentions collected by webmention.io for a domain and
writes a Hugo data file (data/webmentions.json) keyed by site path,
so the site can display minimal, link-only "Around the web" backlinks.

Display philosophy (following V.H. Belvadi's pattern): link back to the
source with credit, embed nothing. No reply text, no avatars, no
content from the sender's page is ever copied or displayed.

Environment variables:
  SITE_URL  - Base URL of the site (default: https://bongotwisty.blog)
  WM_TOKEN  - API token from the webmention.io dashboard (REQUIRED)
  WM_DOMAIN - The domain registered with webmention.io. MUST match the
              registration exactly, e.g. "www.bongotwisty.blog" (note
              the www) or "bongotwisty.uk" after re-registration.
              Defaults to the host part of SITE_URL.
  DEBUG     - "1" prints a raw sample item and a summary of skipped
              items, to verify field names and diagnose the API.

Run from the repository root, BEFORE the hugo build:
  WM_TOKEN=xxx python3 tools/fetch_webmentions.py && hugo

Do NOT commit data/webmentions.json to the repo: it is regenerated on
every build, and incoming mentions change without the repo changing.

NOTE ON FIELD NAMES: the JSON returned by webmention.io's API has
evolved over the years, and the domain-wide JF2 feed has been observed
with slightly different shapes. The parser below is deliberately
defensive and accepts several candidate field names for the target
URL. If no mentions are extracted on a first run, run with DEBUG=1
and compare the printed raw item against the candidates listed in
TARGET_KEYS below.
"""

import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

# --- Config -------------------------------------------------------------

SITE_URL = os.environ.get("SITE_URL", "https://bongotwisty.uk").rstrip("/")
WM_TOKEN = os.environ.get("WM_TOKEN", "")
WM_DOMAIN = os.environ.get(
    "WM_DOMAIN",
    urlparse(SITE_URL).netloc.lower(),
)
DEBUG = os.environ.get("DEBUG", "0") in ("1", "true", "yes")

DATA_PATH = Path("data/webmentions.json")

SITE_HOST = urlparse(SITE_URL).netloc.lower().split(":")[0].removeprefix("www.")
INTERNAL_HOSTS = {SITE_HOST, "www." + SITE_HOST}

# Sources that should never be displayed. Test fixtures from
# webmention.rocks are functional pings, not editorial references;
# sources from our own domain are self-mentions.
EXCLUDE_SOURCE_DOMAINS = frozenset({"webmention.rocks"}) | INTERNAL_HOSTS

API_URL = (
    "https://webmention.io/api/mentions.jf2"
    f"?token={WM_TOKEN}&domain={WM_DOMAIN}"
)

# Candidate fields that may carry the *target* URL (our page that was
# mentioned). The domain-wide feed has been observed using different
# shapes over the years; accept any of these, string or first-of-list.
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
    variant (www, http, etc).
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


def fetch_mentions():
    print(f"Fetching webmentions for domain: {WM_DOMAIN}")
    try:
        with urlopen(API_URL, timeout=30) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        print(f"HTTP error from webmention.io: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Network error reaching webmention.io: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print("webmention.io returned something that is not JSON.", file=sys.stderr)
        sys.exit(1)

    children = raw.get("children", [])
    if DEBUG and children:
        print("--- RAW SAMPLE ITEM (DEBUG) ---")
        print(json.dumps(children[0], indent=2)[:2000])
        print("--------------------------------")
    return children


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
    # our own domain.
    target_url = None
    for key in TARGET_KEYS:
        value = first_url(item.get(key))
        if not value:
            continue
        if host_of(value) in INTERNAL_HOSTS:
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

    children = fetch_mentions()
    print(f"Received {len(children)} mentions from webmention.io.")

    by_path = {}
    seen = set()
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
        f"Wrote {mentions} displayable mentions across {pages} pages "
        f"to {DATA_PATH}."
    )


if __name__ == "__main__":
    main()
