#!/usr/bin/env python3
"""
Webmention receiver-display fetcher for Hugo static sites.

Fetches all webmentions collected by webmention.io and writes a Hugo
data file (data/webmentions.json) keyed by site path, so the site can
display minimal, link-only "Around the web" backlinks.

DATA SOURCES, MERGED IN ORDER (earlier sources win):

1. Archive (ground truth for history): webmention.io's JF2 feed and
   exports have been observed to serve an incomplete projection of
   the account's stored mentions (dashboard count vs feed count
   disagree; records consolidate on re-verification; exports inherit
   the feed's gaps). data/webmentions-archive.jf2.json - a full export
   captured 2026-11-17 - is parsed first so history cannot shrink.

2. Supplement (hand-restored mentions): 19 mentions that the hosted
   service lost after an account merge, restored from the dashboard's
   HTML view on 2026-11-17. Held in data/webmentions-supplement.json
   in the display format (path-keyed, url/author/host/type/ts),
   merged after the archive.

3. Live feed: fetched per TARGET from webmention.io's legacy JSON
   API (https://webmention.io/api/mentions?target=...), NOT from the
   JF2 domain feed.

   WHY: verified on 2026-11-18, the JF2 endpoint's `domain=` filter
   returns ZERO results for targets on bongotwisty.uk even for
   mentions that exist in the account and are visible on the
   dashboard and retrievable by `domain=`+`target=` and by bare
   `target=` on the legacy endpoint. The legacy domain's index still
   works. The domain index for the new domain has apparently been
   broken since the webmention.io account merge (the same operation
   that lost 19 mentions). The legacy endpoint also requires NO token
   for target queries: it accepts a bare `target=` parameter.

   HOW: all mentionable page URLs are enumerated from the built
   site's sitemap (public/sitemap.xml), and the legacy API is queried
   once per target. The sitemap covers every page, so nothing can
   hide behind a broken server-side domain index. NOTE: this
   endpoint's paging is 0-BASED, unlike the JF2 feed's 1-based
   paging; the first page is page=0.

   SPEED: measured server-side latency for one target query is
   ~4.5 seconds (confirmed with curl, 2026-11-18), so the walk is
   threaded: workers only perform HTTP fetches, while ALL parsing,
   dedupe and merging happen in the main thread, keeping merge
   semantics identical to the serial version. With the default
   MAX_WORKERS=8, a ~540-page site takes roughly five minutes.

REMOVALS (a subtraction, not a source):

4. data/webmentions-removed.json, committed to the repo, lists
   mentions that must never be displayed: author takedown requests,
   duplicates, spam. Verified behaviour of webmention.io (checked
   2026-11-18 against the live feed and the archive key inventory):
   withdrawn mentions are OMITTED from the feeds entirely, never
   flagged, so deletions cannot be detected automatically from the
   feed. This file is therefore the withdrawal path. Each entry
   suppresses one source URL, optionally narrowed to a single page
   path and/or a single display type ("replied to", "discussed",
   "liked", "reposted", "bookmarked"; omit "type" to suppress every
   type, omit "path" to suppress the source everywhere). URL matching
   ignores scheme, host case, a leading www. and trailing slashes,
   so values can be copied loosely from data/webmentions.json.
   Suppression is deliberate and persistent: it is NOT lifted
   automatically if the source reappears; remove the entry by hand
   to restore a mention.

Display philosophy (following V.H. Belvadi's pattern): link back to
the source with credit, embed nothing. No reply text, no avatars, no
content from the sender's page is ever copied or displayed.

Environment variables:
  SITE_URL    - Base URL of the site (default: https://bongotwisty.uk)
  WM_TOKEN    - Kept for the JF2 fallback path only; the per-target
                legacy API needs no token.
  MAX_WORKERS - Concurrent target queries (default "8"). Raise with
                care: webmention.io is a free service and its API
                answers slowly (~4.5s) regardless.
  TARGET_DELAY- Seconds to sleep between requests WITHIN one worker
                when a target has multiple pages (default "0.1").
  DEBUG       - "1" prints a raw sample item and a summary of skipped
                items, to verify field names and diagnose the API.

Run from the repository root, AFTER `hugo` has built the site (the
fetcher reads public/sitemap.xml), BEFORE sending webmentions:
  python3 tools/fetch_webmentions.py

Commit data/webmentions-archive.jf2.json,
data/webmentions-supplement.json and data/webmentions-removed.json
to the repo (they are the historical record and the removal policy).
Do NOT commit data/webmentions.json: it is regenerated on every build.
"""

import json
import os
import re
import sys
import time
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse, urlencode
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

# --- Config -------------------------------------------------------------

SITE_URL = os.environ.get("SITE_URL", "https://bongotwisty.uk").rstrip("/")
WM_TOKEN = os.environ.get("WM_TOKEN", "")
DEBUG = os.environ.get("DEBUG", "0") in ("1", "true", "yes")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "8"))
TARGET_DELAY = float(os.environ.get("TARGET_DELAY", "0.1"))

DATA_PATH = Path("data/webmentions.json")
ARCHIVE_PATH = Path("data/webmentions-archive.jf2.json")
SUPPLEMENT_PATH = Path("data/webmentions-supplement.json")
REMOVED_PATH = Path("data/webmentions-removed.json")
SITEMAP_PATH = Path("public/sitemap.xml")

# Legacy JSON API: per-target queries, no token required, 0-based
# paging. This is the ONLY live endpoint observed to return mentions
# for targets on bongotwisty.uk (2026-11-18). Measured latency per
# query: ~4.5 seconds, server-side.
LEGACY_API = "https://webmention.io/api/mentions"
LEGACY_PER_PAGE = 20
LEGACY_MAX_PAGES = 50  # safety cap per target: 50 x 20 = 1000 mentions

# JF2 API: used only as a fallback sweep per domain if the sitemap is
# missing. The JF2 domain index is known to be unreliable for the
# current domain (see module docstring).
JF2_API = "https://webmention.io/api/mentions.jf2"
JF2_PER_PAGE = 20
JF2_MAX_PAGES = 100  # 100 x 20 = 2000 mentions per domain
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

# Candidate fields that may carry the *target* URL in JF2 items. The
# feed has been observed using different shapes over the years.
TARGET_KEYS = (
    "wm-target",
    "target",
    "mention-of",
    "in-reply-to",
    "like-of",
    "repost-of",
    "bookmark-of",
)

# Display verbs derived from the JF2 webmention property type.
VERB_BY_PROPERTY = {
    "mention-of": "discussed",
    "in-reply-to": "replied to",
    "like-of": "liked",
    "repost-of": "reposted",
    "bookmark-of": "bookmarked",
}

# Display verbs derived from the legacy API's activity.type.
VERB_BY_ACTIVITY = {
    "reply": "replied to",
    "repost": "reposted",
    "like": "liked",
    "link": "discussed",
    "mention": "discussed",
    "post": "discussed",
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


def load_jf2_children(data):
    """
    Accept a JF2 document in either shape: a feed wrapper
    {"type": "feed", "children": [...]} or a bare list of entries.
    """
    if isinstance(data, dict):
        return data.get("children", [])
    if isinstance(data, list):
        return data
    return []


# --- Removals (suppression filter) --------------------------------------


def norm_source_url(url: str):
    """
    Normalise a source URL for removal matching: lowercase host, drop
    a leading www., drop any trailing slash. Scheme is discarded and
    query strings are kept. Applied identically to entries in the
    removals file and to display URLs, so either side can be copied
    loosely.
    """
    if not isinstance(url, str):
        return ""
    try:
        parsed = urlparse(url)
    except Exception:
        return url.strip().lower().rstrip("/")
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").rstrip("/")
    return f"{host}{path}"


def load_removed():
    """
    Load data/webmentions-removed.json. Accepted shapes: a bare list
    of entries, or {"removed": [...]} for future extensibility. Each
    entry needs at least "url"; "path" and "type" are optional
    narrowers. Returns a list of rule dicts.
    """
    if not REMOVED_PATH.exists():
        print(f"No removals file at {REMOVED_PATH}; nothing suppressed.")
        return []

    try:
        with REMOVED_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"WARN: could not parse removals file: {e}", file=sys.stderr)
        return []

    if isinstance(data, dict):
        entries = data.get("removed", [])
    elif isinstance(data, list):
        entries = data
    else:
        print("WARN: removals file is neither a list nor an object.", file=sys.stderr)
        return []

    rules = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not url:
            continue
        rules.append(
            {
                "url": norm_source_url(url),
                "path": item.get("path"),
                "type": item.get("type"),
            }
        )
    print(f"Removals: loaded {len(rules)} suppression rules.")
    return rules


def is_removed(display: dict, path_key: str, rules):
    """
    True if this display entry matches any removal rule. A rule with
    no "path" matches every page; a rule with no "type" matches every
    display type.
    """
    source_key = norm_source_url(display.get("url", ""))
    for rule in rules:
        if rule["url"] != source_key:
            continue
        if rule["path"] is not None and rule["path"] != path_key:
            continue
        if rule["type"] is not None and rule["type"] != display.get("type"):
            continue
        return True
    return False


def apply_removals(by_path, rules):
    """
    Subtract suppressed mentions from the merged result, just before
    the write. The archive and supplement files on disk are never
    touched; only the rendered output shrinks. Returns
    (suppressed_count, affected_pages).
    """
    if not rules:
        return 0, set()
    suppressed = 0
    pages = set()
    for path_key in list(by_path):
        kept = [
            d for d in by_path[path_key] if not is_removed(d, path_key, rules)
        ]
        if len(kept) != len(by_path[path_key]):
            suppressed += len(by_path[path_key]) - len(kept)
            pages.add(path_key)
        if kept:
            by_path[path_key] = kept
        else:
            del by_path[path_key]
    return suppressed, pages


# --- Source 1: archive (ground truth for history) -----------------------


def load_archive():
    """
    Parse the committed JF2 export into (by_path, seen) using exactly
    the same rules as the live feeds. Returns empty structures if the
    archive file is absent, so the fetcher still works without it.
    """
    by_path = {}
    seen = set()
    if not ARCHIVE_PATH.exists():
        print(f"No archive at {ARCHIVE_PATH}; history relies on the live feed.")
        return by_path, seen

    try:
        with ARCHIVE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"WARN: could not parse archive file: {e}", file=sys.stderr)
        return by_path, seen

    children = load_jf2_children(data)
    used = 0
    for item in children:
        parsed = parse_jf2_item(item)
        if parsed is None:
            continue
        path_key, display = parsed
        dedupe_key = (display["url"], path_key, display["type"])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        by_path.setdefault(path_key, []).append(display)
        used += 1

    print(f"Archive: loaded {used} mentions across {len(by_path)} pages.")
    return by_path, seen


# --- Source 2: supplement (hand-restored mentions) ---------------------


def load_supplement(by_path, seen):
    """
    Merge the committed supplement file (display format: path-keyed
    display dicts) into the accumulated results. Only adds entries
    the archive does not already hold.
    """
    if not SUPPLEMENT_PATH.exists():
        return 0
    try:
        with SUPPLEMENT_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"WARN: could not parse supplement file: {e}", file=sys.stderr)
        return 0
    if not isinstance(data, dict):
        return 0

    added = 0
    for path_key, entries in data.items():
        if not isinstance(entries, list):
            continue
        for display in entries:
            if not isinstance(display, dict) or "url" not in display:
                continue
            dedupe_key = (display.get("url"), path_key, display.get("type"))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            by_path.setdefault(path_key, []).append(display)
            added += 1
    print(f"Supplement: merged {added} restored mentions.")
    return added


# --- Source 3: live feed via the legacy per-target API ------------------


def load_sitemap_targets():
    """
    Enumerate mentionable page URLs from the built site's sitemap.
    Keeps only URLs on our own hosts (current or legacy). Returns
    None on any problem so the caller can fall back to the
    (unreliable) JF2 domain sweep.
    """
    if not SITEMAP_PATH.exists():
        print(
            f"ERROR: sitemap not found at {SITEMAP_PATH}. Build the site "
            f"first (hugo), or the per-target fetch cannot enumerate pages.",
            file=sys.stderr,
        )
        return None

    try:
        tree = ET.parse(SITEMAP_PATH)
    except Exception as e:
        print(f"WARN: could not parse sitemap: {e}", file=sys.stderr)
        return None

    # Handle both the namespaced and bare <loc> elements.
    locs = []
    for elem in tree.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag == "loc" and elem.text:
            locs.append(elem.text.strip())

    targets = []
    for url in locs:
        if host_of(url) in OUR_HOSTS:
            targets.append(url)
    return targets


def fetch_json(url: str):
    """Fetch one URL and parse the JSON body, or return None."""
    try:
        with urlopen(url, timeout=PAGE_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        print(f"HTTP error from webmention.io: {e.code} {e.reason}", file=sys.stderr)
        return None
    except URLError as e:
        print(f"Network error reaching webmention.io: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("webmention.io returned something that is not JSON.", file=sys.stderr)
        return None


def fetch_target_mentions(target_url: str):
    """
    Gather every mention for one target URL from the legacy API.
    Designed to run in a worker thread: performs HTTP only, no
    shared state, returns a plain list.

    Paging on this endpoint is 0-BASED (the first page is page=0 and
    is also the default). Only an empty "links" array signals the
    end; rely on paging."total-pages" when present, with a hard cap.
    """
    links = []
    total_pages = None  # unknown until the first response
    page = 0
    while page < LEGACY_MAX_PAGES:
        params = urlencode(
            {"target": target_url, "per-page": LEGACY_PER_PAGE, "page": page}
        )
        raw = fetch_json(f"{LEGACY_API}?{params}")
        if raw is None:
            break
        batch = raw.get("links", [])
        if page == 0 and DEBUG and batch:
            print("--- RAW SAMPLE LEGACY ITEM (DEBUG) ---")
            print(json.dumps(batch[0], indent=2)[:2000])
            print("--------------------------------------")
        links.extend(batch)
        paging = raw.get("paging") or {}
        declared = paging.get("total-pages")
        if isinstance(declared, int) and declared > 0:
            total_pages = declared
        if total_pages is not None and page + 1 >= total_pages:
            break
        if not batch:
            break
        page += 1
        if total_pages is None and len(batch) < LEGACY_PER_PAGE:
            break
        if TARGET_DELAY > 0:
            time.sleep(TARGET_DELAY)
    return links


def parse_legacy_item(item):
    """
    Map a legacy-API mention object onto (path_key, display_dict),
    matching the JF2-derived display shape, or None if skipped.

    Legacy shape (observed 2026-11-18):
      source           - the URL the ping came from
      data.url         - the canonical page of the mention (displayed)
      data.author.name - author display name
      data.published   - publication timestamp string
      activity.type    - "reply" | "repost" | "like" | ...
      private          - bool privacy flag
      target           - our page that was mentioned
    """
    if not isinstance(item, dict):
        return None
    if item.get("private"):
        return None

    target_url = item.get("target")
    if not target_url or host_of(target_url) not in OUR_HOSTS:
        if DEBUG:
            print(f"SKIP (foreign/absent target): {item.get('source')}")
        return None

    path_key = normalise_path(target_url)
    if path_key is None:
        return None

    data = item.get("data") or {}
    author_data = data.get("author") or {}
    author = clean_author(
        author_data.get("name") if isinstance(author_data, dict) else None
    )

    # Display URL: prefer the mention's canonical page over the raw
    # ping source, matching what the JF2 archive holds in "url".
    url = data.get("url") or item.get("source")
    if not url:
        return None

    source_host = host_of(url) or ""
    if source_host in EXCLUDE_SOURCE_DOMAINS:
        return None

    activity = item.get("activity") or {}
    verb = VERB_BY_ACTIVITY.get(activity.get("type"), "discussed")

    ts = data.get("published") or item.get("verified_date") or ""

    display = {
        "url": url,
        "author": author,
        "host": source_host.removeprefix("www."),
        "type": verb,
        "ts": ts,
    }
    return path_key, display


def live_targets_pass(seen, by_path):
    """
    Query the legacy API for every sitemap target concurrently and
    merge the results. Workers only fetch; ALL parsing, dedupe and
    merging happen here in the main thread, so merge semantics are
    identical to a serial walk. Returns (total_received, added_new).
    """
    total_received = 0
    added_from_feed = 0
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_target_mentions, t): t for t in ALL_TARGETS}
        for future in as_completed(futures):
            target_url = futures[future]
            try:
                links = future.result()
            except Exception as e:  # defensive: workers should not raise
                print(f"WARN: fetch failed for {target_url}: {e}", file=sys.stderr)
                links = []
            if links:
                total_received += len(links)
                for item in links:
                    parsed = parse_legacy_item(item)
                    if parsed is None:
                        continue
                    path_key, display = parsed
                    dedupe_key = (display["url"], path_key, display["type"])
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    by_path.setdefault(path_key, []).append(display)
                    added_from_feed += 1
            done += 1
            if done % 100 == 0:
                print(f"  ...queried {done}/{len(ALL_TARGETS)} targets.")

    print(
        f"Live (per-target): fetched {total_received} mentions, "
        f"{added_from_feed} new beyond archive+supplement."
    )
    return total_received, added_from_feed


# --- Fallback: JF2 per-domain sweep (used only without a sitemap) ------


def parse_jf2_item(item):
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


def fetch_all_mentions_jf2(domain: str):
    """
    Fallback: gather every mention the JF2 feed serves for a domain.
    KNOWN ISSUE: the domain index is unreliable for the current
    domain; this path exists only for legacy domains and as a
    stopgap. The API clamps per_page (to 20), so page length tells us
    nothing about completeness. The only reliable end signal is an
    empty page, so we keep paging until one comes back with no
    children (or the safety cap is hit).
    """
    all_children = []
    for page in range(1, JF2_MAX_PAGES + 1):
        params = urlencode(
            {
                "token": WM_TOKEN,
                "domain": domain,
                "per_page": JF2_PER_PAGE,
                "page": page,
            }
        )
        raw = fetch_json(f"{JF2_API}?{params}")
        if raw is None:
            break
        children = raw.get("children", [])
        if page == 1 and DEBUG and children:
            print("--- RAW SAMPLE ITEM (DEBUG) ---")
            print(json.dumps(children[0], indent=2)[:2000])
            print("--------------------------------")
        if not children:
            break
        all_children.extend(children)
        if page == JF2_MAX_PAGES:
            print(
                f"WARN: hit page cap ({JF2_MAX_PAGES}) for {domain}; "
                f"fetch may be incomplete.",
                file=sys.stderr,
            )
    return all_children


def live_jf2_fallback_pass(seen, by_path):
    """
    Stand-in for the per-target walk when no sitemap exists. Loudly
    reports its unreliability for the current domain.
    """
    total_received = 0
    added_from_feed = 0
    for domain in sorted(OUR_HOSTS):
        children = fetch_all_mentions_jf2(domain)
        total_received += len(children)
        print(f"[fallback JF2] {domain}: received {len(children)} mentions.")
        for item in children:
            parsed = parse_jf2_item(item)
            if parsed is None:
                continue
            path_key, display = parsed
            dedupe_key = (display["url"], path_key, display["type"])
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            by_path.setdefault(path_key, []).append(display)
            added_from_feed += 1
    return total_received, added_from_feed


# --- Globals set in main (targets for the concurrent walk) --------------

ALL_TARGETS = []


# --- Main ---------------------------------------------------------------


def main():
    # History first: the archive is ground truth and cannot be
    # altered by whatever the live feed later reports.
    by_path, seen = load_archive()
    archive_pages = len(by_path)

    # Restored mentions second: hand-recovered from the dashboard
    # after the hosted service lost them.
    load_supplement(by_path, seen)

    # Live feed last: can only add.
    targets = load_sitemap_targets()
    if targets is None:
        print(
            "Falling back to the JF2 domain sweep, which is KNOWN to miss "
            "mentions for the current domain. Fix the sitemap to get "
            "reliable per-target fetching.",
            file=sys.stderr,
        )
        _, added = live_jf2_fallback_pass(seen, by_path)
    else:
        ALL_TARGETS[:] = targets
        print(
            f"Sitemap: {len(ALL_TARGETS)} target pages to query "
            f"({MAX_WORKERS} workers)."
        )
        _, added = live_targets_pass(seen, by_path)

    # Suppression last: subtract hand-listed removals from the merged
    # result, immediately before the write. History files on disk are
    # untouched; only the display output shrinks.
    rules = load_removed()
    suppressed, suppressed_pages = apply_removals(by_path, rules)
    if suppressed:
        print(
            f"Removals: suppressed {suppressed} mentions across "
            f"{len(suppressed_pages)} page(s)."
        )

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
        f"({archive_pages} from archive) to {DATA_PATH}."
    )


if __name__ == "__main__":
    main()
