"""PubMed channel via NCBI E-utilities."""

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from typing import Any

import requests

from lib.channels import Candidate, register_channel

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
DEFAULT_LOOKBACK_DAYS = 30
MAX_AUTHORS = 5


@register_channel("pubmed")
class PubMedChannel:
    def fetch_candidates(
        self,
        topics: list[str],
        since: str | None,
        **kwargs: Any,
    ) -> list[Candidate]:
        if since:
            since_dt = datetime.fromisoformat(since)
        else:
            since_dt = datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)

        try:
            return self._search(topics, since_dt)
        except Exception as exc:
            print(f"PubMed error: {exc}", file=sys.stderr)
            return []

    def _search(
        self,
        topics: list[str],
        since_dt: datetime,
    ) -> list[Candidate]:
        # Build combined query
        query = " OR ".join(f'"{t}"' for t in topics)
        mindate = since_dt.strftime("%Y/%m/%d")
        maxdate = datetime.now(timezone.utc).strftime("%Y/%m/%d")

        # Step 1: esearch — get PMIDs
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": 20,
            "sort": "date",
            "mindate": mindate,
            "maxdate": maxdate,
        }
        resp = requests.get(ESEARCH_URL, params=search_params, timeout=15)
        resp.raise_for_status()
        search_data = resp.json()

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        # Step 2: esummary — get metadata
        summary_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json",
        }
        resp = requests.get(ESUMMARY_URL, params=summary_params, timeout=15)
        resp.raise_for_status()
        summary_data = resp.json()

        results: list[Candidate] = []
        for pmid in id_list:
            doc = summary_data.get("result", {}).get(pmid, {})
            if not doc or isinstance(doc, str):
                continue

            title = doc.get("title", "")
            # Authors: list of dicts with "name" key
            authors_raw = doc.get("authors", [])
            authors = [a.get("name", "") for a in authors_raw[:MAX_AUTHORS]]

            # Published date
            pubdate = doc.get("pubdate", "")

            # Journal
            journal = doc.get("fulljournalname", "") or doc.get("source", "")

            results.append(Candidate(
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                title=title,
                source_channel="pubmed",
                published=pubdate,
                summary=title,  # esummary doesn't return abstracts
                extra={
                    "pmid": pmid,
                    "authors": authors,
                    "journal": journal,
                },
            ))
        return results
