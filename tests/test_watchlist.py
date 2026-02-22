"""Tests for watchlist CRUD and scout logic."""

import pytest
from unittest.mock import patch, MagicMock

from lib.watchlist import (
    create_watchlist_entry,
    list_watchlist_entries,
    get_watchlist_entry,
    remove_watchlist_entry,
    update_last_checked,
    scout,
    scout_all,
    _normalize_url,
)
from lib.channels import Candidate


class TestNormalizeUrl:
    def test_lowercase(self):
        assert _normalize_url("HTTPS://Example.COM/Path") == "https://example.com/path"

    def test_strip_trailing_slash(self):
        assert _normalize_url("https://example.com/") == "https://example.com"

    def test_already_normalized(self):
        assert _normalize_url("https://example.com/path") == "https://example.com/path"


class TestCRUD:
    def test_create_and_list(self, tmp_data_dir):
        entry = create_watchlist_entry(
            "AI", ["AI agents"], [{"type": "hn"}]
        )
        assert entry["name"] == "AI"
        assert entry["topics"] == ["AI agents"]
        assert entry["last_checked"] is None

        entries = list_watchlist_entries()
        assert len(entries) == 1
        assert entries[0]["name"] == "AI"

    def test_create_duplicate_raises(self, tmp_data_dir):
        create_watchlist_entry("AI", ["AI agents"], [{"type": "hn"}])
        with pytest.raises(ValueError, match="already exists"):
            create_watchlist_entry("AI", ["other"], [{"type": "hn"}])

    def test_get_entry(self, tmp_data_dir):
        create_watchlist_entry("AI", ["AI agents"], [{"type": "hn"}])
        entry = get_watchlist_entry("AI")
        assert entry is not None
        assert entry["name"] == "AI"

    def test_get_missing_entry(self, tmp_data_dir):
        assert get_watchlist_entry("nope") is None

    def test_remove_entry(self, tmp_data_dir):
        create_watchlist_entry("AI", ["AI agents"], [{"type": "hn"}])
        assert remove_watchlist_entry("AI") is True
        assert list_watchlist_entries() == []

    def test_remove_missing_entry(self, tmp_data_dir):
        assert remove_watchlist_entry("nope") is False

    def test_update_last_checked(self, tmp_data_dir):
        create_watchlist_entry("AI", ["AI agents"], [{"type": "hn"}])
        update_last_checked("AI")
        entry = get_watchlist_entry("AI")
        assert entry["last_checked"] is not None


class TestScout:
    def test_dedup_within_results(self, tmp_data_dir):
        """Same URL from different channels is deduped."""
        c1 = Candidate("https://example.com/post", "Post", "hn", None, "HN", {})
        c2 = Candidate("https://example.com/post", "Post", "rss", None, "RSS", {})

        mock_hn = MagicMock()
        mock_hn.fetch_candidates.return_value = [c1]
        mock_rss = MagicMock()
        mock_rss.fetch_candidates.return_value = [c2]

        entry = {
            "name": "test",
            "topics": ["test"],
            "channels": [{"type": "hn"}, {"type": "rss", "url": "https://feed.com"}],
            "last_checked": None,
        }

        def fake_get_channel(t):
            return {"hn": mock_hn, "rss": mock_rss}[t]

        with patch("lib.watchlist.get_channel", side_effect=fake_get_channel):
            results, errors = scout(entry)

        assert len(results) == 1
        assert results[0].source_channel == "hn"  # first occurrence kept

    def test_filters_existing_sources(self, tmp_data_dir):
        """URLs already in library sources are filtered out."""
        from lib.config import save_config, load_config

        config = load_config()
        config["sources"] = [{"origin": "https://example.com/existing", "type": "url"}]
        save_config(config)

        c1 = Candidate("https://example.com/existing", "Old", "hn", None, "", {})
        c2 = Candidate("https://example.com/new", "New", "hn", None, "", {})

        mock_ch = MagicMock()
        mock_ch.fetch_candidates.return_value = [c1, c2]

        entry = {
            "name": "test",
            "topics": ["test"],
            "channels": [{"type": "hn"}],
            "last_checked": None,
        }

        with patch("lib.watchlist.get_channel", return_value=mock_ch):
            results, errors = scout(entry)

        assert len(results) == 1
        assert results[0].url == "https://example.com/new"

    def test_channel_error_captured(self, tmp_data_dir):
        """Channel errors are captured, not raised."""
        mock_ch = MagicMock()
        mock_ch.fetch_candidates.side_effect = Exception("API down")

        entry = {
            "name": "test",
            "topics": ["test"],
            "channels": [{"type": "hn"}],
            "last_checked": None,
        }

        with patch("lib.watchlist.get_channel", return_value=mock_ch):
            results, errors = scout(entry)

        assert results == []
        assert len(errors) == 1
        assert "API down" in errors[0]


class TestScoutAll:
    def test_scouts_all_entries(self, tmp_data_dir):
        create_watchlist_entry("A", ["topic"], [{"type": "hn"}])
        create_watchlist_entry("B", ["topic"], [{"type": "hn"}])

        mock_ch = MagicMock()
        mock_ch.fetch_candidates.return_value = []

        with patch("lib.watchlist.get_channel", return_value=mock_ch):
            results = scout_all()

        assert len(results) == 2

    def test_scouts_specific_entry(self, tmp_data_dir):
        create_watchlist_entry("A", ["topic"], [{"type": "hn"}])
        create_watchlist_entry("B", ["topic"], [{"type": "hn"}])

        mock_ch = MagicMock()
        mock_ch.fetch_candidates.return_value = []

        with patch("lib.watchlist.get_channel", return_value=mock_ch):
            results = scout_all("A")

        assert len(results) == 1
        assert results[0]["name"] == "A"

    def test_missing_entry_raises(self, tmp_data_dir):
        with pytest.raises(ValueError, match="not found"):
            scout_all("nope")

    def test_updates_last_checked(self, tmp_data_dir):
        create_watchlist_entry("A", ["topic"], [{"type": "hn"}])

        mock_ch = MagicMock()
        mock_ch.fetch_candidates.return_value = []

        with patch("lib.watchlist.get_channel", return_value=mock_ch):
            scout_all("A")

        entry = get_watchlist_entry("A")
        assert entry["last_checked"] is not None
