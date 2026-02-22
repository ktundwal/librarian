"""Tests for RSS channel."""

import time
from unittest.mock import patch, MagicMock
from lib.channels.rss import RSSChannel


def _make_feed(entries):
    feed = MagicMock()
    feed.entries = entries
    return feed


class TestRSSChannel:
    def test_topic_matching(self):
        entries = [
            {
                "title": "New AI Agent Framework Released",
                "summary": "A comprehensive agent framework for building autonomous systems.",
                "link": "https://blog.example.com/ai-agent",
                "published_parsed": time.strptime("2026-02-20", "%Y-%m-%d"),
            },
            {
                "title": "Cooking Tips for Winter",
                "summary": "Best soups for cold weather.",
                "link": "https://blog.example.com/cooking",
                "published_parsed": time.strptime("2026-02-20", "%Y-%m-%d"),
            },
        ]
        with patch("lib.channels.rss.feedparser.parse", return_value=_make_feed(entries)):
            ch = RSSChannel()
            results = ch.fetch_candidates(
                ["AI agent"], since=None, url="https://blog.example.com/feed"
            )

        assert len(results) == 1
        assert results[0].title == "New AI Agent Framework Released"
        assert results[0].source_channel == "rss"
        assert results[0].extra["feed_url"] == "https://blog.example.com/feed"

    def test_html_stripped_from_summary(self):
        entries = [
            {
                "title": "LLM Tool Use Guide",
                "summary": "<p>Learn how to build <b>LLM tools</b> for agents.</p>",
                "link": "https://example.com/llm",
                "published_parsed": time.strptime("2026-02-20", "%Y-%m-%d"),
            },
        ]
        with patch("lib.channels.rss.feedparser.parse", return_value=_make_feed(entries)):
            ch = RSSChannel()
            results = ch.fetch_candidates(
                ["LLM"], since=None, url="https://example.com/feed"
            )

        assert "<p>" not in results[0].summary
        assert "<b>" not in results[0].summary

    def test_date_filtering(self):
        entries = [
            {
                "title": "Old AI Post",
                "summary": "AI agents discussion",
                "link": "https://example.com/old",
                "published_parsed": time.strptime("2020-01-01", "%Y-%m-%d"),
            },
        ]
        with patch("lib.channels.rss.feedparser.parse", return_value=_make_feed(entries)):
            ch = RSSChannel()
            results = ch.fetch_candidates(
                ["AI"], since="2026-01-01T00:00:00+00:00", url="https://example.com/feed"
            )

        assert len(results) == 0

    def test_requires_url(self):
        ch = RSSChannel()
        results = ch.fetch_candidates(["test"], since=None)
        assert results == []

    def test_handles_error_gracefully(self):
        with patch("lib.channels.rss.feedparser.parse", side_effect=Exception("parse error")):
            ch = RSSChannel()
            results = ch.fetch_candidates(
                ["test"], since=None, url="https://example.com/feed"
            )

        assert results == []

    def test_case_insensitive_matching(self):
        entries = [
            {
                "title": "TRANSFORMER Architecture Deep Dive",
                "summary": "Understanding attention mechanisms",
                "link": "https://example.com/transformer",
                "published_parsed": time.strptime("2026-02-20", "%Y-%m-%d"),
            },
        ]
        with patch("lib.channels.rss.feedparser.parse", return_value=_make_feed(entries)):
            ch = RSSChannel()
            results = ch.fetch_candidates(
                ["transformer"], since=None, url="https://example.com/feed"
            )

        assert len(results) == 1
