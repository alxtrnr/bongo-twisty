#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone, date

# --- Config -------------------------------------------------------------

SITE_URL = "https://bongotwisty.blog"  # matches hugo.toml baseURL
PUBLIC_DIR = Path("public")
CACHE_PATH = Path("webmention-sent.json")
MAX_PER_RUN = 20  # cap for incremental mode
CUTOFF_DATE = date(2017, 1, 1)  # only consider content from 2017-01-01 onwards

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


# --- Utilities ----------------------------------------------------------


def is_external_link(href: str):
    if not href or href.startswith("#"):
        return False
    parsed = urlparse(href)
    # relative URL
    if not parsed.scheme:
        return False
    if not parsed.netloc:
        return False
    # absolute, but internal
    if href.startswith(SITE_URL):
        return False
    return parsed.scheme in ("http", "https")


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

    # 2) try HTML <link rel="webmention">
    code, body, _ = run_curl(["-sL", "-H", "Accept-Encoding: identity", target_url])
    if code != 0:
        return None

    lower = body.lower()
    idx = 0
    while True:
        idx = lower.find('rel="webmention"', idx)
        if idx == -1:
            break
        # search backwards a bit for <link ...>
        snippet_start = lower.rfind("<link", 0, idx)
        if snippet_start == -1:
            idx += 15
            continue
        snippet_end = lower.find(">", idx)
        if snippet_end == -1:
            break
        snippet = body[snippet_start:snippet_end]
        # crude href parse
        href_pos = snippet.lower().find("href=")
        if href_pos != -1:
            quote = snippet[href_pos + 5]
            if quote in ("'", '"'):
                end_href = snippet.find(quote, href_pos + 6)
                if end_href != -1:
                    href = snippet[href_pos + 6 : end_href]
                    # make absolute if needed
                    if href.startswith("http://") or href.startswith("https://"):
                        return href
                    else:
                        return urljoin(target_url, href)
        idx = snippet_end
    return None


# --- Send Webmention ----------------------------------------------------


def send_webmention(source_url: str, target_url: str, endpoint_url: str):
    data = f"source={source_url}&target={target_url}"
    code, out, err = run_curl(["-s", "-X", "POST", "-d", data, endpoint_url])
    if code == 0:
        return True, out.strip()
    else:
        return False, (err.strip() or out.strip())


# --- Mode: full ---------------------------------------------------------


def full_mode(cache):
    sent_this_run = 0
    for html_path in PUBLIC_DIR.rglob("*.html"):
        # Skip very old pages based on HTML mtime
        mtime = datetime.fromtimestamp(html_path.stat().st_mtime, tz=timezone.utc).date()
        if mtime < CUTOFF_DATE:
            continue

        source_url = html_path_to_url(html_path)
        links = extract_links_from_file(html_path)
        for href in links:
            if not is_external_link(href):
                continue
            target_url = href
            key = cache_key(source_url, target_url)
            if key in cache:
                continue
            endpoint = discover_endpoint(target_url)
            if not endpoint:
                continue
            ok, msg = send_webmention(source_url, target_url, endpoint)
            if ok:
                sent_this_run += 1
                cache[key] = datetime.now(timezone.utc).isoformat()
                print(f"SENT (full): {source_url} -> {target_url} via {endpoint}")
            else:
                print(
                    f"FAIL (full): {source_url} -> {target_url}: {msg}",
                    file=sys.stderr,
                )
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

        links = extract_links_from_file(html_path)
        for href in links:
            if not is_external_link(href):
                continue
            target_url = href
            key = cache_key(source_url, target_url)
            if key in cache:
                continue
            endpoint = discover_endpoint(target_url)
            if not endpoint:
                continue
            ok, msg = send_webmention(source_url, target_url, endpoint)
            if ok:
                sent_this_run += 1
                cache[key] = datetime.now(timezone.utc).isoformat()
                print(f"SENT (incremental): {source_url} -> {target_url} via {endpoint}")
            else:
                print(
                    f"FAIL (incremental): {source_url} -> {target_url}: {msg}",
                    file=sys.stderr,
                )
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
