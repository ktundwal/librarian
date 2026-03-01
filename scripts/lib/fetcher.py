"""HTTP fetching, HTML-to-markdown conversion, and caching for URL sources."""

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import CACHE_DIR

_TWEET_URL_RE = re.compile(
    r"https?://(?:twitter\.com|x\.com)/\w+/status/(\d+)"
)


def fetch_source(source: dict[str, Any]) -> dict[str, Any]:
    """Fetch a URL source, cache the result, and return status.

    Returns dict with keys:
        changed: bool — whether content changed
        cached_path: str | None — path to cached markdown file
        etag: str | None
        last_modified: str | None
        content_hash: str | None
        fetched_at: str — ISO timestamp
        error: str | None
    """
    url = source["origin"]
    source_id = source["source_id"]
    old_etag = source.get("etag")
    old_last_modified = source.get("last_modified")
    old_content_hash = source.get("content_hash")

    cache_dir = CACHE_DIR / source_id
    cached_path = cache_dir / "source.md"

    try:
        status_code, headers, body = _fetch_url(url, old_etag, old_last_modified)
    except Exception as e:
        return {
            "changed": False,
            "cached_path": str(cached_path) if cached_path.exists() else None,
            "etag": old_etag,
            "last_modified": old_last_modified,
            "content_hash": old_content_hash,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }

    now = datetime.now(timezone.utc).isoformat()

    if status_code == 304:
        return {
            "changed": False,
            "cached_path": str(cached_path) if cached_path.exists() else None,
            "etag": old_etag,
            "last_modified": old_last_modified,
            "content_hash": old_content_hash,
            "fetched_at": now,
            "error": None,
        }

    # Convert based on content type
    content_type = headers.get("content-type", "")
    if "text/html" in content_type:
        markdown = _html_to_markdown(body)
    else:
        # text/plain, text/markdown, or fallback
        markdown = body

    new_hash = hashlib.sha256(markdown.encode()).hexdigest()[:16]
    changed = new_hash != old_content_hash

    # Write to cache
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_path.write_text(markdown, encoding="utf-8")

    return {
        "changed": changed,
        "cached_path": str(cached_path),
        "etag": headers.get("etag", old_etag),
        "last_modified": headers.get("last-modified", old_last_modified),
        "content_hash": new_hash,
        "fetched_at": now,
        "error": None,
    }


def _fetch_url(
    url: str,
    etag: str | None = None,
    last_modified: str | None = None,
) -> tuple[int, dict[str, str], str]:
    """HTTP GET with conditional headers. Returns (status_code, headers, body)."""
    import requests

    # Twitter/X URLs: route through syndication API instead of HTTP GET
    tweet_match = _TWEET_URL_RE.match(url)
    if tweet_match:
        return _fetch_twitter(tweet_match.group(1))

    req_headers = {"User-Agent": "library-skill/0.1"}
    if etag:
        req_headers["If-None-Match"] = etag
    if last_modified:
        req_headers["If-Modified-Since"] = last_modified

    resp = requests.get(url, headers=req_headers, timeout=30)

    # Let 304 through without raising
    if resp.status_code != 304:
        resp.raise_for_status()

    resp_headers = {k.lower(): v for k, v in resp.headers.items()}
    return resp.status_code, resp_headers, resp.text


def _html_to_markdown(html: str) -> str:
    """Convert HTML to clean markdown, stripping boilerplate elements."""
    from bs4 import BeautifulSoup
    from markdownify import markdownify

    soup = BeautifulSoup(html, "html.parser")

    # Strip boilerplate elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    cleaned_html = str(soup)
    md = markdownify(cleaned_html, heading_style="ATX", strip=["img"])
    # Collapse excessive blank lines
    lines = md.split("\n")
    collapsed = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                collapsed.append(line)
        else:
            blank_count = 0
            collapsed.append(line)
    return "\n".join(collapsed).strip()


def _fetch_twitter(tweet_id: str) -> tuple[int, dict[str, str], str]:
    """Fetch a tweet via syndication API and return as (status, headers, markdown)."""
    from lib.channels.twitter import fetch_tweet_as_markdown

    markdown = fetch_tweet_as_markdown(tweet_id)
    return 200, {"content-type": "text/markdown"}, markdown
