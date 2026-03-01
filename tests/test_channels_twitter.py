"""Tests for Twitter channel."""

from unittest.mock import patch, MagicMock

from lib.channels.twitter import (
    TwitterChannel,
    _compute_token,
    _float_to_base36,
    fetch_tweet,
    tweet_to_markdown,
    TWEET_URL_RE,
)


# ---------------------------------------------------------------------------
# Token computation
# ---------------------------------------------------------------------------

class TestTokenComputation:
    def test_returns_nonempty_string(self):
        token = _compute_token("2017742741636321619")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_no_dots_or_zeros(self):
        token = _compute_token("2017742741636321619")
        assert "." not in token
        assert "0" not in token

    def test_deterministic(self):
        t1 = _compute_token("2017742741636321619")
        t2 = _compute_token("2017742741636321619")
        assert t1 == t2

    def test_different_ids_produce_different_tokens(self):
        t1 = _compute_token("2017742741636321619")
        t2 = _compute_token("2007179832300581177")
        assert t1 != t2


# ---------------------------------------------------------------------------
# Base-36 conversion
# ---------------------------------------------------------------------------

class TestFloatToBase36:
    def test_integer_36(self):
        assert _float_to_base36(36.0) == "10"

    def test_zero(self):
        assert _float_to_base36(0.0) == "0"

    def test_integer_10(self):
        assert _float_to_base36(10.0) == "a"

    def test_integer_35(self):
        assert _float_to_base36(35.0) == "z"

    def test_fractional_part_included(self):
        result = _float_to_base36(36.5)
        assert "." in result
        assert result.startswith("10.")


# ---------------------------------------------------------------------------
# URL pattern matching
# ---------------------------------------------------------------------------

class TestTweetUrlPattern:
    def test_x_dot_com(self):
        m = TWEET_URL_RE.search("https://x.com/bcherny/status/2017742741636321619")
        assert m is not None
        assert m.group("user") == "bcherny"
        assert m.group("id") == "2017742741636321619"

    def test_twitter_dot_com(self):
        m = TWEET_URL_RE.search("https://twitter.com/karpathy/status/2015883857489522876")
        assert m is not None
        assert m.group("user") == "karpathy"
        assert m.group("id") == "2015883857489522876"

    def test_no_match_on_other_urls(self):
        assert TWEET_URL_RE.search("https://example.com/status/123") is None


# ---------------------------------------------------------------------------
# Syndication API fetch
# ---------------------------------------------------------------------------

SAMPLE_TWEET_JSON = {
    "id_str": "2017742741636321619",
    "text": "Thread: tips for getting the most out of Claude Code",
    "user": {"screen_name": "bcherny", "name": "Boris Cherny"},
    "created_at": "2026-02-20T10:00:00.000Z",
    "favorite_count": 142,
    "retweet_count": 53,
    "reply_count": 18,
    "photos": [],
}


class TestFetchTweet:
    def test_calls_syndication_api(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_TWEET_JSON
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.twitter.requests.get", return_value=mock_resp) as mock_get:
            data = fetch_tweet("2017742741636321619")

        assert data["text"] == "Thread: tips for getting the most out of Claude Code"
        assert data["user"]["screen_name"] == "bcherny"
        # Verify syndication URL was called
        call_url = mock_get.call_args[0][0]
        assert "syndication.twimg.com" in call_url

    def test_raises_on_http_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")

        with patch("lib.channels.twitter.requests.get", return_value=mock_resp):
            try:
                fetch_tweet("999")
                assert False, "Should have raised"
            except Exception as e:
                assert "403" in str(e)


# ---------------------------------------------------------------------------
# Markdown conversion
# ---------------------------------------------------------------------------

class TestTweetToMarkdown:
    def test_includes_author_and_text(self):
        md = tweet_to_markdown(SAMPLE_TWEET_JSON)
        assert "@bcherny" in md
        assert "tips for getting the most out of Claude Code" in md

    def test_includes_metrics(self):
        md = tweet_to_markdown(SAMPLE_TWEET_JSON)
        assert "142" in md  # likes
        assert "53" in md   # retweets

    def test_includes_quoted_tweet(self):
        data = {
            **SAMPLE_TWEET_JSON,
            "quoted_tweet": {
                "user": {"screen_name": "anthropic"},
                "text": "Claude Code is now available",
            },
        }
        md = tweet_to_markdown(data)
        assert "@anthropic" in md
        assert "Claude Code is now available" in md


# ---------------------------------------------------------------------------
# Channel integration
# ---------------------------------------------------------------------------

class TestTwitterChannel:
    def test_fetches_known_tweet_ids(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_TWEET_JSON
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.twitter.requests.get", return_value=mock_resp):
            ch = TwitterChannel()
            results = ch.fetch_candidates(
                ["Claude Code"], since=None, tweet_ids=["2017742741636321619"]
            )

        assert len(results) == 1
        assert results[0].source_channel == "twitter"
        assert results[0].extra["tweet_id"] == "2017742741636321619"
        assert results[0].extra["author"] == "bcherny"
        assert results[0].extra["like_count"] == 142
        assert results[0].extra["retweet_count"] == 53

    def test_handles_syndication_error_gracefully(self):
        with patch("lib.channels.twitter.requests.get", side_effect=Exception("timeout")):
            ch = TwitterChannel()
            results = ch.fetch_candidates(
                ["test"], since=None, tweet_ids=["999"]
            )

        assert results == []

    def test_no_accounts_no_ids_returns_empty(self):
        ch = TwitterChannel()
        results = ch.fetch_candidates(["test"], since=None)
        assert results == []

    def test_multiple_tweet_ids(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_TWEET_JSON
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.twitter.requests.get", return_value=mock_resp):
            ch = TwitterChannel()
            results = ch.fetch_candidates(
                ["test"], since=None, tweet_ids=["111", "222", "333"]
            )

        assert len(results) == 3

    def test_candidate_to_dict_flattens_extra(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_TWEET_JSON
        mock_resp.raise_for_status = MagicMock()

        with patch("lib.channels.twitter.requests.get", return_value=mock_resp):
            ch = TwitterChannel()
            results = ch.fetch_candidates(
                ["test"], since=None, tweet_ids=["2017742741636321619"]
            )

        d = results[0].to_dict()
        assert "tweet_id" in d
        assert "author" in d
        assert "retweet_count" in d
        assert "like_count" in d
        assert "extra" not in d

    def test_timeline_discovery_filters_by_topic(self):
        """Tier 2: timeline tweets are filtered by topic keyword match."""
        timeline_tweets = [
            {
                "tweet_id": "100",
                "author": "bcherny",
                "text": "New Claude Code feature: agent teams with shared context",
                "published": "2026-02-25T10:00:00Z",
                "url": "https://x.com/bcherny/status/100",
            },
            {
                "tweet_id": "101",
                "author": "bcherny",
                "text": "Great coffee this morning",
                "published": "2026-02-25T09:00:00Z",
                "url": "https://x.com/bcherny/status/101",
            },
        ]

        with patch("lib.channels.twitter._scrape_timeline", return_value=timeline_tweets):
            ch = TwitterChannel()
            results = ch.fetch_candidates(
                ["Claude Code"], since=None, accounts=["bcherny"]
            )

        # Only the Claude Code tweet should match
        assert len(results) == 1
        assert results[0].extra["tweet_id"] == "100"

    def test_timeline_error_handled_gracefully(self):
        with patch(
            "lib.channels.twitter._scrape_timeline",
            side_effect=RuntimeError("not authenticated"),
        ):
            ch = TwitterChannel()
            results = ch.fetch_candidates(
                ["test"], since=None, accounts=["nonexistent"]
            )

        assert results == []
