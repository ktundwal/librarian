"""Tests for watch.py CLI arg parsing and shelf commands."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from watch import parse_channel_arg, build_parser, list_shelves, install_shelf


class TestParseChannelArg:
    def test_bare_type(self):
        assert parse_channel_arg("hn") == {"type": "hn"}

    def test_bare_pubmed(self):
        assert parse_channel_arg("pubmed") == {"type": "pubmed"}

    def test_hn_with_min_points(self):
        result = parse_channel_arg("hn:min_points=100")
        assert result == {"type": "hn", "min_points": 100}

    def test_arxiv_categories(self):
        result = parse_channel_arg("arxiv:cs.AI,cs.LG")
        assert result == {"type": "arxiv", "categories": ["cs.AI", "cs.LG"]}

    def test_rss_url(self):
        result = parse_channel_arg("rss:https://example.com/feed")
        assert result == {"type": "rss", "url": "https://example.com/feed"}

    def test_github_min_stars(self):
        result = parse_channel_arg("github:min_stars=50")
        assert result == {"type": "github", "min_stars": 50}


class TestBuildParser:
    def test_create_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "create", "AI advances",
            "--topic", "AI agents",
            "--topic", "LLM",
            "--channel", "hn",
            "--channel", "arxiv:cs.AI,cs.LG",
        ])
        assert args.command == "create"
        assert args.name == "AI advances"
        assert args.topic == ["AI agents", "LLM"]
        assert args.channel == ["hn", "arxiv:cs.AI,cs.LG"]

    def test_list_args(self):
        parser = build_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_check_args_no_name(self):
        parser = build_parser()
        args = parser.parse_args(["check"])
        assert args.command == "check"
        assert args.name is None

    def test_check_args_with_name(self):
        parser = build_parser()
        args = parser.parse_args(["check", "AI advances"])
        assert args.command == "check"
        assert args.name == "AI advances"

    def test_remove_args(self):
        parser = build_parser()
        args = parser.parse_args(["remove", "AI advances"])
        assert args.command == "remove"
        assert args.name == "AI advances"

    def test_shelf_list(self):
        parser = build_parser()
        args = parser.parse_args(["shelf", "list"])
        assert args.command == "shelf"
        assert args.shelf_action == "list"

    def test_shelf_install(self):
        parser = build_parser()
        args = parser.parse_args(["shelf", "install", "ai"])
        assert args.command == "shelf"
        assert args.shelf_action == "install"
        assert args.shelf_name == "ai"


class TestShelves:
    def test_list_shelves(self):
        shelves = list_shelves()
        ids = [s["id"] for s in shelves]
        assert "ai" in ids
        assert "biomedical" in ids

    def test_ai_shelf_has_topics(self):
        shelves = list_shelves()
        ai = next(s for s in shelves if s["id"] == "ai")
        assert len(ai["topics"]) > 0
        assert ai["channels"] > 0

    def test_install_shelf(self, tmp_data_dir):
        entry = install_shelf("ai")
        assert entry["name"] == "AI advances"
        assert len(entry["topics"]) > 0
        assert len(entry["channels"]) > 0

    def test_install_duplicate_raises(self, tmp_data_dir):
        install_shelf("ai")
        with pytest.raises(ValueError, match="already exists"):
            install_shelf("ai")

    def test_install_missing_shelf_raises(self, tmp_data_dir):
        with pytest.raises(ValueError, match="not found"):
            install_shelf("nonexistent")
