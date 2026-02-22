"""Hacker News channel via Algolia API."""

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from typing import Any

import requests

from lib.channels import Candidate, register_channel

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
DEFAULT_MIN_POINTS = 30
DEFAULT_LOOKBACK_DAYS = 7


@register_channel("hn")
class HNChannel:
    def fetch_candidates(
        self,
        topics: list[str],
        since: str | None,
        **kwargs: Any,
    ) -> list[Candidate]:
        min_points = int(kwargs.get("min_points", DEFAULT_MIN_POINTS))

        if since:
            since_ts = int(datetime.fromisoformat(since).timestamp())
        else:
            since_ts = int((datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)).timestamp())

        candidates: list[Candidate] = []
        for topic in topics:
            try:
                candidates.extend(self._search_topic(topic, since_ts, min_points))
            except Exception as exc:
                print(f"HN error for topic '{topic}': {exc}", file=sys.stderr)
        return candidates

    def _search_topic(
        self, topic: str, since_ts: int, min_points: int
    ) -> list[Candidate]:
        params = {
            "query": topic,
            "tags": "story",
            "numericFilters": f"points>{min_points},created_at_i>{since_ts}",
            "hitsPerPage": 20,
        }
        resp = requests.get(HN_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results: list[Candidate] = []
        for hit in data.get("hits", []):
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
            results.append(Candidate(
                url=url,
                title=hit.get("title", ""),
                source_channel="hn",
                published=hit.get("created_at"),
                summary=f"{hit.get('points', 0)} points, {hit.get('num_comments', 0)} comments on HN",
                extra={
                    "points": hit.get("points", 0),
                    "hn_id": hit.get("objectID", ""),
                    "num_comments": hit.get("num_comments", 0),
                },
            ))
        return results
