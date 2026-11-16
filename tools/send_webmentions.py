#!/usr/bin/env python3
"""
Webmention sender for Hugo static sites.

Sends W3C Webmentions (https://www.w3.org/TR/webmention/) for external
links found in generated HTML. Supports full and incremental (git-based)
modes. Designed to run in CI pipelines (GitHub Actions, Woodpecker/Codeberg).

Spec coverage (W3C Webmention REC):
  3.1.2  Endpoint discovery: Link header first, then <link>/<a>, with
         redirects followed on both header and body probes.
  3.1.3  Transmission: form-encoded source/target POST; any 2xx counts
         as success (200 synchronous / 201 created / 202 accepted).
  3.1.4  Updates: the outgoing link set of each source is hashed; a
         change clears the cached pairs and re-sends, including links
         that were removed by the edit.
  3.1.5  Deletions: git-deleted posts (and, in full mode, cached
         sources whose HTML no longer exists) have their previously
         sent webmentions re-sent so receivers can withdraw them.

Configuration via environment variables:
  SITE_URL  - Base URL of the site (default: https://bongotwisty.blog)
  MODE      - "full" or "incremental" (default: incremental)
  DRY_RUN   - "1"/"true"/"yes" performs no network POSTs, makes no
              cache changes, and prints WOULD SEND lines instead.

Run from the repository root (paths to public/, the cache file and the
git working tree are all relative). e.g.:
  MODE=full DRY_RUN=1 python3 tools/send_webmentions.py

Cache file (webmention-sent.json) should be committed to the repo
so it persists between CI runs.

Cache format (version 2):
  {
    "version": 2,
    "sources": {
      "<source url>": {
        "hash": "<sha256 of outgoing link set>",
        "targets": {
          "<target url>": {"ts": "<iso>", "event": "created|deleted"}
        }
      }
    }
  }
Version 1 (flat "source target" keys) is migrated transparently.
"""

import hashlib
import os
import sys
import json
import subprocess
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone, date

# --- Config -------------------------------------------------------------

SITE_URL = os.environ.get("SITE_URL", "https://bongotwisty.blog").rstrip("/")
PUBLIC_DIR = Path("public")
CACHE_PATH = Path("webmention-sent.json")
MAX_PER_RUN = 20  # cap for incremental mode
CUTOFF_DATE = date(2017, 1, 1)  # only consider content from 2017-01-01 onwards

DRY_RUN = os.environ.get("DRY_RUN", "0") in ("1", "true", "yes")

# Pages that should never act as webmention sources (site chrome,
# error pages) even though they contain links.
SKIP_SOURCES = {"404.html"}

# Domains that appear in site chrome (footers, sidebars) rather than
# content. These should not receive webmentions because they are
# navigation widgets, licences badges or profile widgets, not
# editorial references.
EXCLUDE_DOMAINS = frozenset({
    "xn--sr8hvo.ws",        # IndieWeb webring — redirects to random members
    "fediring.net",         # Fediring — same issue
    "creativecommons.org",  # licence badge in footer chrome
    "listenbrainz.org",     # ListenBrainz widget/profile link
})

# Internal-link detection by hostname rather than string prefix, so
# www.-prefixed internal links are correctly treated as internal.
SITE_HOST = urlparse(SITE_URL).netloc.lower().split(":")[0].removeprefix("www.")
INTERNAL_HOSTS = {SITE_HOST, "www." + SITE_HOST}


# --- Small helpers -------------------------------------------------------


def now_iso():
    return datetime.now(timezone.utc).isoformat()


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


# --- Cache handling ------------------------------------------------------
#
# [SPEC 3.1.4 / 3.1.5] The cache is organised per-source, holding a
# content hash of the source's outgoing link set and the per-target
# send state. Old flat-cache entries are migrated on load.


def load_cache():
    if CACHE_PATH.exists():
        try:
            with CACHE_PATH.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            return new_cache()
        if isinstance(raw, dict) and raw.get("version") == 2:
            return raw
        # v1 flat cache: keys are "source target" -> timestamp
        return migrate_v1(raw)
    return new_cache()


def new_cache():
    return {"version": 2, "sources": {}}


def migrate_v1(flat):
    cache = new_cache()
    if not isinstance(flat, dict):
        return cache
    for key, ts in flat.items():
        if not isinstance(key, str) or " " not in key:
            continue
        source, target = key.split(" ", 1)
        entry = cache["sources"].setdefault(source, {"hash": None, "targets": {}})
        entry["targets"][target] = {"ts": ts, "event": "created"}
    print(f"Migrated {len(cache['sources'])} cached sources from v1 cache format.")
    return cache


def save_cache(cache):
    tmp = CACHE_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True)
    tmp.replace(CACHE_PATH)


def source_entry(cache, source_url):
    return cache["sources"].setdefault(source_url, {"hash": None, "targets": {}})


# --- Link filtering -----------------------------------------------------


def is_external_link(href: str):
    """Return True if href is an absolute external http(s) link."""
    if not href or href.startswith("#"):
        return False
    parsed = urlparse(href)
    if not parsed.scheme or not parsed.netloc:
        return False
    # Internal by hostname (covers the www. variant too)
    host = parsed.netloc.lower().split(":")[0]
    if host in INTERNAL_HOSTS:
        return False
    return parsed.scheme in ("http", "https")


def is_excluded_link(url: str):
    """Check if a URL belongs to an excluded (non-editorial) domain."""
    try:
        netloc = urlparse(url).netloc.lower()
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


def candidate_links(html_path: Path):
    """Filtered, de-duplicated external candidate targets for a page."""
    candidates = []
    seen = set()
    for href in extract_links_from_file(html_path):
        if not should_send_webmention(href):
            continue
        if href not in seen:
            seen.add(href)
            candidates.append(href)
    return candidates


def link_set_hash(candidates):
    """
    [SPEC 3.1.4] Fingerprint of the outgoing link set. Hashing the
    *filtered link set* rather than raw HTML means theme rebuilds and
    cosmetic edits do not trigger re-sends; only added or removed
    external links do. Caveat: an edit that changes only the visible
    h-entry text (which receivers may display) will not be detected.
    """
    payload = "\n".join(sorted(candidates))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --- Utilities ----------------------------------------------------------


def html_path_to_url(path: Path):
    rel = path.relative_to(PUBLIC_DIR)
    if rel == Path("index.html"):
        return SITE_URL + "/"
    if rel.name == "index.html":
        url_path = "/" + str(rel.parent).strip("/")
        if not url_path.endswith("/"):
            url_path += "/"
        return SITE_URL + url_path
    return SITE_URL + "/" + str(rel)


def url_to_html_path(url: str):
    """Best-effort inverse of html_path_to_url, for delete detection."""
    prefix = SITE_URL + "/"
    if not url.startswith(prefix):
        return None
    tail = url[len(prefix):].rstrip("/")
    if not tail:
        return PUBLIC_DIR / "index.html"
    if tail.endswith(".html") or tail.endswith(".htm"):
        return PUBLIC_DIR / tail
    return PUBLIC_DIR / tail / "index.html"


def run_curl(args):
    """Run curl, return (exit_code, stdout_str, stderr_str)."""
    proc = subprocess.run(
        ["curl", "--max-time", "10"] + args,
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
#
# [SPEC 3.1.2] The sender MUST fetch the target URL and follow
# redirects, checking in order: HTTP Link header, then the first
# <link> element, then the first <a> element. The header probe uses
# -sIL so redirects are followed there too.


def _extract_href_from_tag(tag_html: str, target_url: str):
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
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(target_url, href)


def discover_endpoint(target_url: str):
    # 1) HTTP Link header, following redirects [SPEC 3.1.2]
    code, headers, _ = run_curl(["-sIL", "-H", "Accept-Encoding: identity", target_url])
    if code == 0:
        for line in headers.splitlines():
            if line.lower().startswith("link:"):
                parts = line.split(": ", 1)[-1].split(",")
                for part in parts:
                    if 'rel="webmention"' in part:
                        start = part.find("<")
                        end = part.find(">", start + 1)
                        if start != -1 and end != -1:
                            endpoint = part[start + 1 : end]
                            if endpoint.startswith("/"):
                                endpoint = urljoin(target_url, endpoint)
                            return endpoint

    # 2) HTML <link rel="webmention"> and <a rel="webmention">
    code, body, _ = run_curl(["-sL", "-H", "Accept-Encoding: identity", target_url])
    if code != 0:
        return None

    lower = body.lower()
    idx = 0
    while True:
        idx = lower.find('rel="webmention"', idx)
        if idx == -1:
            break

        link_start = lower.rfind("<link", 0, idx)
        a_start = lower.rfind("<a", 0, idx)
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
#
# [SPEC 3.1.3] Any 2xx is success, covering synchronous (200), status
# page (201) and queued (202) receivers alike.


def send_webmention(source_url: str, target_url: str, endpoint_url: str):
    """
    Return a tuple (status, message) where status is one of:
      - True:   successfully sent (2xx)
      - "gone": target is permanently gone (410/404)
      - False:  transient failure or unexpected error
    "gone" results are not cached, so they are retried next run.
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


# --- Deliver a webmention to one target ---------------------------------


def deliver(cache, source_url: str, target_url: str, event: str, label: str):
    """
    Discover the endpoint and send one webmention. Records the result
    in the source's cache entry. Returns True if sent successfully.

    In DRY_RUN mode no network requests are made and nothing is
    cached; WOULD SEND lines indicate pairs that would be attempted
    (a superset of those that would succeed, since endpoint discovery
    is also skipped).
    """
    if DRY_RUN:
        print(f"WOULD SEND ({label}) [{event}]: {source_url} -> {target_url}")
        return False

    endpoint = discover_endpoint(target_url)
    if not endpoint:
        return False

    ok, msg = send_webmention(source_url, target_url, endpoint)
    entry = source_entry(cache, source_url)

    if ok is True:
        entry["targets"][target_url] = {"ts": now_iso(), "event": event}
        verb = "SENT" if event == "created" else "DELETE-NOTIFIED"
        print(f"{verb} ({label}): {source_url} -> {target_url} via {endpoint}")
        return True
    elif ok == "gone":
        print(f"GONE ({label}): {source_url} -> {target_url}: {msg}")
    else:
        print(
            f"FAIL ({label}): {source_url} -> {target_url}: {msg}",
            file=sys.stderr,
        )
    return False


# --- Process a live HTML file ------------------------------------------
#
# [SPEC 3.1.4] If the outgoing link set has changed since the last
# run, every previously sent pair for this source is queued for
# re-sending (including links the edit removed, which are no longer
# present in the page to be rediscovered). Receivers re-fetch the
# source and update their display.


def process_html_file(html_path: Path, cache: dict, label: str):
    """Returns number of webmentions sent for this file."""
    source_url = html_path_to_url(html_path)
    candidates = candidate_links(html_path)
    entry = source_entry(cache, source_url)

    resend = []
    if entry["hash"] is not None and entry["hash"] != link_set_hash(candidates):
        resend = [
            t for t, info in entry["targets"].items()
            if info.get("event") == "created"
        ]
        entry["targets"] = {t: i for t, i in entry["targets"].items() if t not in set(resend)}
        if resend:
            print(
                f"UPDATE ({label}): link set changed for {source_url}; "
                f"re-sending {len(resend)} webmentions"
            )

    to_process = list(dict.fromkeys(resend + candidates))

    sent_from_file = 0
    for target_url in to_process:
        if target_url in entry["targets"]:
            continue
        if deliver(cache, source_url, target_url, "created", label):
            sent_from_file += 1

    entry["hash"] = link_set_hash(candidates)
    return sent_from_file


# --- Notify receivers of a deleted source -------------------------------
#
# [SPEC 3.1.5] When a post is deleted, the sender re-sends every
# previously sent webmention for it. Receivers then re-fetch the
# source, see it gone (ideally 410/tombstone), and withdraw their
# display. Pairs are marked event="deleted" so the deletion is
# notified exactly once.


def notify_deletions_for(source_url: str, cache: dict, label: str):
    """Returns number of deletion notices sent for this source."""
    entry = cache["sources"].get(source_url)
    if not entry or not entry["targets"]:
        return 0
    pending = [
        t for t, info in entry["targets"].items()
        if info.get("event") != "deleted"
    ]
    if not pending:
        return 0

    print(
        f"DELETE ({label}): source removed: {source_url}; "
        f"re-sending {len(pending)} webmentions so receivers withdraw them"
    )
    sent = 0
    for target_url in pending:
        if deliver(cache, source_url, target_url, "deleted", label):
            sent += 1
    return sent


# --- Mode: full ---------------------------------------------------------


def full_mode(cache):
    sent_this_run = 0
    live_sources = set()

    for html_path in PUBLIC_DIR.rglob("*.html"):
        rel = html_path.relative_to(PUBLIC_DIR)
        if str(rel) in SKIP_SOURCES:
            continue
        mtime = datetime.fromtimestamp(html_path.stat().st_mtime, tz=timezone.utc).date()
        if mtime < CUTOFF_DATE:
            continue
        live_sources.add(html_path_to_url(html_path))
        sent_this_run += process_html_file(html_path, cache, "full")

    # [SPEC 3.1.5] cached sources whose page no longer exists
    deleted_notices = 0
    for source_url in list(cache["sources"]):
        if source_url in live_sources:
            continue
        html_path = url_to_html_path(source_url)
        if html_path is not None and html_path.exists():
            continue
        deleted_notices += notify_deletions_for(source_url, cache, "full")

    print(
        f"Full mode done, sent {sent_this_run} new webmentions "
        f"and {deleted_notices} deletion notices."
    )
    return cache


# --- Mode: incremental (git-based) -------------------------------------


def get_changed_content_files():
    cmd = ["git", "diff", "--name-only", "HEAD~10", "HEAD"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        return []
    files = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("content/") and not line.startswith("content/_"):
            files.append(Path(line))
    return files


def get_deleted_content_files():
    """
    [SPEC 3.1.5] Content files removed from the repo within the git
    window. These map to source URLs whose receivers must be notified.
    """
    cmd = ["git", "diff", "--name-only", "--diff-filter=D", "HEAD~10", "HEAD"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        return []
    files = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line and line.startswith("content/") and not line.startswith("content/_"):
            files.append(Path(line))
    return files


def content_to_public_path(content_path: Path):
    rel = content_path.relative_to("content")
    if rel.suffix in (".md", ".html"):
        rel = rel.with_suffix("")

    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "posts":
        slug = parts[-1]
        return PUBLIC_DIR / slug / "index.html"

    return PUBLIC_DIR / rel / "index.html"


def incremental_mode(cache):
    changed_content = get_changed_content_files()
    deleted_content = get_deleted_content_files()
    if not changed_content and not deleted_content:
        print("No changed or deleted content files detected, nothing to do.")
        return cache

    # Filter live files by mtime
    recent_content = []
    for content_path in changed_content:
        if not content_path.exists():
            continue
        mtime = datetime.fromtimestamp(content_path.stat().st_mtime, tz=timezone.utc).date()
        if mtime >= CUTOFF_DATE:
            recent_content.append(content_path)

    sent_this_run = 0
    processed_sources = set()

    # [SPEC 3.1.4] updates and new sends for live pages
    for content_path in recent_content:
        html_path = content_to_public_path(content_path)
        if not html_path.exists():
            continue
        source_url = html_path_to_url(html_path)
        if source_url in processed_sources:
            continue
        processed_sources.add(source_url)
        sent_this_run += process_html_file(html_path, cache, "incremental")
        if sent_this_run >= MAX_PER_RUN:
            print(f"Reached MAX_PER_RUN={MAX_PER_RUN}, stopping for this run.")
            if not DRY_RUN:
                if not DRY_RUN:
                    save_cache(cache)
            return cache

    # [SPEC 3.1.5] deletion notices for removed posts
    notified_sources = set()
    for content_path in deleted_content:
        html_path = content_to_public_path(content_path)
        source_url = html_path_to_url(html_path)
        if source_url in notified_sources:
            continue
        notified_sources.add(source_url)
        sent_this_run += notify_deletions_for(source_url, cache, "incremental")
        if sent_this_run >= MAX_PER_RUN:
            print(f"Reached MAX_PER_RUN={MAX_PER_RUN}, stopping for this run.")
            if not DRY_RUN:
                if not DRY_RUN:
                    save_cache(cache)
            return cache

    print(f"Incremental mode done, sent {sent_this_run} webmention deliveries.")
    return cache


# --- Main ---------------------------------------------------------------


def main():
    mode = os.environ.get("MODE", "incremental").lower()
    cache = load_cache()

    if mode == "full":
        cache = full_mode(cache)
    else:
        cache = incremental_mode(cache)

    if not DRY_RUN:
        if not DRY_RUN:
            save_cache(cache)
    else:
        print("Dry run complete. Cache unchanged; nothing was delivered.")


if __name__ == "__main__":
    main()
