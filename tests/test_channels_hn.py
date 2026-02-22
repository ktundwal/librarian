"""Tests for HN channel."""

from unittest.mock import patch, MagicMock
from lib.channels.hn import HNChannel


class TestHNChannel:
    def test_parses_hits_into_candidates(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "hits": [
                {
                    "objectID": "123",
                    "title": "AI Agents Are Here",
                    "url": "https://example.com/ai-agents",
                    "points": 150,
                    "num_comments": 42,
                    "created_at": "2026-02-20T10:00:00.000Z",
                },
                {
                    "objectID": "456",
                    "title": "Show HN: My LLM Tool",
                    "url": None,  # self-post
                    "points": 80,
                    "num_comments": 15,
                    "created_at": "2026-02-19T08:00:00.000Z",
                },
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.hn.requests.get", return_value=mock_resp):
            ch = HNChannel()
            results = ch.fetch_candidates(["AI agents"], since=None)

        assert len(results) == 2
        assert results[0].url == "https://example.com/ai-agents"
        assert results[0].title == "AI Agents Are Here"
        assert results[0].source_channel == "hn"
        assert results[0].extra["points"] == 150
        assert results[0].extra["hn_id"] == "123"
        assert results[0].extra["num_comments"] == 42

        # Self-post should use HN URL
        assert results[1].url == "https://news.ycombinator.com/item?id=456"

    def test_respects_min_points(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hits": []}
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.hn.requests.get", return_value=mock_resp) as mock_get:
            ch = HNChannel()
            ch.fetch_candidates(["test"], since=None, min_points=100)

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert "points>100" in params["numericFilters"]

    def test_multiple_topics_concatenated(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hits": [
            {"objectID": "1", "title": "T1", "url": "https://a.com", "points": 50, "num_comments": 1, "created_at": "2026-01-01T00:00:00Z"},
        ]}
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.hn.requests.get", return_value=mock_resp) as mock_get:
            ch = HNChannel()
            results = ch.fetch_candidates(["AI", "LLM"], since=None)

        # Should be called once per topic
        assert mock_get.call_count == 2
        # Results from both calls concatenated
        assert len(results) == 2

    def test_handles_api_error_gracefully(self):
        with patch("lib.channels.hn.requests.get", side_effect=Exception("timeout")):
            ch = HNChannel()
            results = ch.fetch_candidates(["test"], since=None)

        assert results == []

    def test_since_parameter_used(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hits": []}
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.hn.requests.get", return_value=mock_resp) as mock_get:
            ch = HNChannel()
            ch.fetch_candidates(["test"], since="2026-02-15T00:00:00+00:00")

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert "created_at_i>" in params["numericFilters"]

    def test_candidate_to_dict_flattens_extra(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "hits": [
                {"objectID": "1", "title": "Test", "url": "https://test.com", "points": 99, "num_comments": 10, "created_at": "2026-01-01T00:00:00Z"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.hn.requests.get", return_value=mock_resp):
            ch = HNChannel()
            results = ch.fetch_candidates(["test"], since=None)

        d = results[0].to_dict()
        assert d["points"] == 99
        assert d["hn_id"] == "1"
        assert "extra" not in d
