"""GitHub channel via Search API."""

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from typing import Any

import requests

from lib.channels import Candidate, register_channel

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
DEFAULT_MIN_STARS = 10
DEFAULT_LOOKBACK_DAYS = 7


@register_channel("github")
class GitHubChannel:
    def fetch_candidates(
        self,
        topics: list[str],
        since: str | None,
        **kwargs: Any,
    ) -> list[Candidate]:
        min_stars = int(kwargs.get("min_stars", DEFAULT_MIN_STARS))

        if since:
            since_dt = datetime.fromisoformat(since)
        else:
            since_dt = datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)

        since_date = since_dt.strftime("%Y-%m-%d")

        candidates: list[Candidate] = []
        for topic in topics:
            try:
                candidates.extend(self._search_topic(topic, since_date, min_stars))
            except Exception as exc:
                print(f"GitHub error for topic '{topic}': {exc}", file=sys.stderr)
        return candidates

    def _search_topic(
        self, topic: str, since_date: str, min_stars: int
    ) -> list[Candidate]:
        q = f"{topic} created:>{since_date} stars:>={min_stars}"
        params = {
            "q": q,
            "sort": "stars",
            "order": "desc",
            "per_page": 20,
        }
        headers = {"Accept": "application/vnd.github.v3+json"}
        resp = requests.get(GITHUB_SEARCH_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results: list[Candidate] = []
        for item in data.get("items", []):
            results.append(Candidate(
                url=item.get("html_url", ""),
                title=item.get("name", ""),
                source_channel="github",
                published=item.get("created_at"),
                summary=(item.get("description") or "")[:300],
                extra={
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language"),
                    "full_name": item.get("full_name", ""),
                },
            ))
        return results
