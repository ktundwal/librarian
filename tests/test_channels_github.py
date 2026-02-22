"""Tests for GitHub channel."""

from unittest.mock import patch, MagicMock
from lib.channels.github import GitHubChannel


class TestGitHubChannel:
    def test_parses_items_into_candidates(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "items": [
                {
                    "html_url": "https://github.com/org/cool-tool",
                    "name": "cool-tool",
                    "full_name": "org/cool-tool",
                    "description": "An AI agent framework for autonomous coding",
                    "stargazers_count": 230,
                    "language": "Python",
                    "created_at": "2026-02-20T15:30:00Z",
                },
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.github.requests.get", return_value=mock_resp):
            ch = GitHubChannel()
            results = ch.fetch_candidates(["AI agent"], since=None)

        assert len(results) == 1
        c = results[0]
        assert c.url == "https://github.com/org/cool-tool"
        assert c.title == "cool-tool"
        assert c.source_channel == "github"
        assert c.extra["stars"] == 230
        assert c.extra["language"] == "Python"
        assert c.extra["full_name"] == "org/cool-tool"

    def test_min_stars_in_query(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"items": []}
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.github.requests.get", return_value=mock_resp) as mock_get:
            ch = GitHubChannel()
            ch.fetch_candidates(["test"], since=None, min_stars=100)

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert "stars:>=100" in params["q"]

    def test_multiple_topics(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"items": [
            {"html_url": "https://github.com/a/b", "name": "b", "full_name": "a/b",
             "description": "desc", "stargazers_count": 10, "language": "Go", "created_at": "2026-01-01T00:00:00Z"},
        ]}
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.github.requests.get", return_value=mock_resp) as mock_get:
            ch = GitHubChannel()
            results = ch.fetch_candidates(["AI", "LLM"], since=None)

        assert mock_get.call_count == 2
        assert len(results) == 2  # one per topic call

    def test_handles_error_gracefully(self):
        with patch("lib.channels.github.requests.get", side_effect=Exception("rate limit")):
            ch = GitHubChannel()
            results = ch.fetch_candidates(["test"], since=None)

        assert results == []

    def test_description_truncated(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "items": [
                {
                    "html_url": "https://github.com/x/y",
                    "name": "y",
                    "full_name": "x/y",
                    "description": "A" * 500,
                    "stargazers_count": 50,
                    "language": "Rust",
                    "created_at": "2026-02-20T00:00:00Z",
                },
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.github.requests.get", return_value=mock_resp):
            ch = GitHubChannel()
            results = ch.fetch_candidates(["test"], since=None)

        assert len(results[0].summary) <= 300
