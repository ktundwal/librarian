"""Tests for arXiv channel."""

from unittest.mock import patch, MagicMock
from lib.channels.arxiv import ArxivChannel


def _make_feed(entries):
    """Create a mock feedparser result."""
    feed = MagicMock()
    feed.entries = entries
    return feed


class TestArxivChannel:
    def test_parses_entries_into_candidates(self):
        entries = [
            {
                "id": "http://arxiv.org/abs/2402.12345v1",
                "title": "Chain-of-Thought\nReasoning in LLMs",
                "published": "2026-02-20T00:00:00Z",
                "summary": "We present a novel approach to reasoning in large language models.",
                "authors": [{"name": "Alice"}, {"name": "Bob"}],
                "tags": [{"term": "cs.AI"}, {"term": "cs.CL"}],
            }
        ]
        with patch("lib.channels.arxiv.feedparser.parse", return_value=_make_feed(entries)):
            ch = ArxivChannel()
            results = ch.fetch_candidates(["LLM reasoning"], since=None)

        assert len(results) == 1
        c = results[0]
        assert c.source_channel == "arxiv"
        assert c.extra["arxiv_id"] == "2402.12345v1"
        assert c.extra["authors"] == ["Alice", "Bob"]
        assert "cs.AI" in c.extra["categories"]
        # Title should have newline stripped
        assert "\n" not in c.title

    def test_filters_by_date(self):
        entries = [
            {
                "id": "http://arxiv.org/abs/old-paper",
                "title": "Old Paper",
                "published": "2020-01-01T00:00:00Z",
                "summary": "Old stuff.",
                "authors": [],
                "tags": [],
            }
        ]
        with patch("lib.channels.arxiv.feedparser.parse", return_value=_make_feed(entries)):
            ch = ArxivChannel()
            results = ch.fetch_candidates(["AI"], since="2026-01-01T00:00:00+00:00")

        assert len(results) == 0

    def test_categories_in_query(self):
        with patch("lib.channels.arxiv.feedparser.parse", return_value=_make_feed([])) as mock_parse:
            ch = ArxivChannel()
            ch.fetch_candidates(["AI"], since=None, categories=["cs.AI", "cs.LG"])

        call_url = mock_parse.call_args[0][0]
        assert "cat:cs.AI" in call_url
        assert "cat:cs.LG" in call_url

    def test_handles_error_gracefully(self):
        with patch("lib.channels.arxiv.feedparser.parse", side_effect=Exception("parse error")):
            ch = ArxivChannel()
            results = ch.fetch_candidates(["test"], since=None)

        assert results == []

    def test_summary_truncated(self):
        long_summary = "A" * 500
        entries = [
            {
                "id": "http://arxiv.org/abs/123",
                "title": "Paper",
                "published": "2026-02-20T00:00:00Z",
                "summary": long_summary,
                "authors": [],
                "tags": [],
            }
        ]
        with patch("lib.channels.arxiv.feedparser.parse", return_value=_make_feed(entries)):
            ch = ArxivChannel()
            results = ch.fetch_candidates(["test"], since=None)

        assert len(results[0].summary) <= 300
