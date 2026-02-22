"""RSS/Atom feed channel."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser

from lib.channels import Candidate, register_channel

DEFAULT_LOOKBACK_DAYS = 30


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _parse_entry_date(entry: dict) -> datetime | None:
    """Try to parse a feed entry's date."""
    for key in ("published_parsed", "updated_parsed"):
        tp = entry.get(key)
        if tp:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(tp), tz=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                pass
    for key in ("published", "updated"):
        raw = entry.get(key, "")
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except (TypeError, ValueError):
                pass
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except (TypeError, ValueError):
                pass
    return None


@register_channel("rss")
class RSSChannel:
    def fetch_candidates(
        self,
        topics: list[str],
        since: str | None,
        **kwargs: Any,
    ) -> list[Candidate]:
        url = kwargs.get("url")
        if not url:
            print("RSS channel requires 'url' config", file=sys.stderr)
            return []

        if since:
            since_dt = datetime.fromisoformat(since)
        else:
            since_dt = datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)

        try:
            return self._fetch(url, topics, since_dt)
        except Exception as exc:
            print(f"RSS error for {url}: {exc}", file=sys.stderr)
            return []

    def _fetch(
        self,
        feed_url: str,
        topics: list[str],
        since_dt: datetime,
    ) -> list[Candidate]:
        feed = feedparser.parse(feed_url)

        results: list[Candidate] = []
        for entry in feed.entries:
            # Date filtering
            pub_dt = _parse_entry_date(entry)
            if pub_dt and pub_dt < since_dt:
                continue

            # Topic matching: case-insensitive substring in title + summary
            title = entry.get("title", "")
            raw_summary = entry.get("summary", "") or entry.get("description", "")
            clean_summary = _strip_html(raw_summary)
            match_text = f"{title} {clean_summary}".lower()

            if not any(t.lower() in match_text for t in topics):
                continue

            link = entry.get("link", "")
            published_str = None
            if pub_dt:
                published_str = pub_dt.isoformat()

            results.append(Candidate(
                url=link,
                title=title,
                source_channel="rss",
                published=published_str,
                summary=clean_summary[:300],
                extra={
                    "feed_url": feed_url,
                },
            ))
        return results
