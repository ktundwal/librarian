"""arXiv channel via Atom API."""

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from typing import Any

import feedparser

from lib.channels import Candidate, register_channel

ARXIV_API_URL = "https://export.arxiv.org/api/query"
DEFAULT_LOOKBACK_DAYS = 30  # arXiv papers can take time to appear


@register_channel("arxiv")
class ArxivChannel:
    def fetch_candidates(
        self,
        topics: list[str],
        since: str | None,
        **kwargs: Any,
    ) -> list[Candidate]:
        categories = kwargs.get("categories", [])

        if since:
            since_dt = datetime.fromisoformat(since)
        else:
            since_dt = datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)

        try:
            return self._search(topics, categories, since_dt)
        except Exception as exc:
            print(f"arXiv error: {exc}", file=sys.stderr)
            return []

    def _search(
        self,
        topics: list[str],
        categories: list[str],
        since_dt: datetime,
    ) -> list[Candidate]:
        # Build query: (all:"topic1" OR all:"topic2") AND (cat:cs.AI OR cat:cs.LG)
        topic_parts = " OR ".join(f'all:"{t}"' for t in topics)
        query = f"({topic_parts})"
        if categories:
            cat_parts = " OR ".join(f"cat:{c}" for c in categories)
            query += f" AND ({cat_parts})"

        params = {
            "search_query": query,
            "max_results": 20,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        feed = feedparser.parse(f"{ARXIV_API_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}")

        results: list[Candidate] = []
        for entry in feed.entries:
            # Client-side date filtering
            published_str = entry.get("published", "")
            if published_str:
                try:
                    pub_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                    if pub_dt < since_dt:
                        continue
                except (ValueError, TypeError):
                    pass

            # Extract arxiv ID from entry id URL
            arxiv_id = entry.get("id", "").split("/abs/")[-1]

            # Clean title (strip embedded newlines)
            title = entry.get("title", "").replace("\n", " ").strip()

            # Truncate summary
            summary = entry.get("summary", "").replace("\n", " ").strip()[:300]

            # Authors
            authors = [a.get("name", "") for a in entry.get("authors", [])]

            # Categories
            cats = [t.get("term", "") for t in entry.get("tags", [])]

            # URL: prefer the abstract page
            url = entry.get("id", "")
            if not url.startswith("http"):
                url = f"https://arxiv.org/abs/{arxiv_id}"

            results.append(Candidate(
                url=url,
                title=title,
                source_channel="arxiv",
                published=published_str,
                summary=summary,
                extra={
                    "arxiv_id": arxiv_id,
                    "authors": authors,
                    "categories": cats,
                },
            ))
        return results
