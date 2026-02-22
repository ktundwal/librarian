"""Tests for lib.config."""

import pytest

from lib.config import (
    load_config,
    save_config,
    compute_freshness,
    DEFAULT_CONFIG,
)


class TestLoadConfig:
    def test_missing_file_creates_defaults(self, tmp_data_dir):
        config = load_config()
        assert config["chunk_size"] == 512
        assert config["top_k"] == 5
        assert config["sources"] == []

    def test_partial_merge(self, tmp_data_dir):
        # Write a config with only one key
        (tmp_data_dir / "config.yaml").write_text("top_k: 10\n")
        config = load_config()
        assert config["top_k"] == 10
        # Missing keys get defaults
        assert config["chunk_size"] == 512
        assert config["embedding_model"] == "BAAI/bge-small-en-v1.5"

    def test_corrupt_yaml(self, tmp_data_dir):
        (tmp_data_dir / "config.yaml").write_text("{{invalid: yaml: [")
        config = load_config()
        assert config == dict(DEFAULT_CONFIG)

    def test_empty_file(self, tmp_data_dir):
        (tmp_data_dir / "config.yaml").write_text("")
        config = load_config()
        # yaml.safe_load("") returns None → non-dict → defaults
        assert config == dict(DEFAULT_CONFIG)

    def test_non_dict_yaml(self, tmp_data_dir):
        (tmp_data_dir / "config.yaml").write_text("just a string\n")
        config = load_config()
        assert config == dict(DEFAULT_CONFIG)


class TestSaveConfig:
    def test_roundtrip(self, tmp_data_dir):
        original = dict(DEFAULT_CONFIG)
        original["top_k"] = 20
        save_config(original)
        loaded = load_config()
        assert loaded["top_k"] == 20


class TestComputeFreshness:
    def test_non_url_returns_na(self):
        source = {"type": "file", "origin": "/some/path"}
        assert compute_freshness(source) == "n/a"

    def test_never_fetched(self):
        source = {"type": "url", "origin": "https://x.com"}
        assert compute_freshness(source) == "never_fetched"

    def test_never_fetched_explicit_none(self):
        source = {"type": "url", "origin": "https://x.com", "refreshed_at": None}
        assert compute_freshness(source) == "never_fetched"

    def test_fresh(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        source = {"type": "url", "origin": "https://x.com", "refreshed_at": now}
        assert compute_freshness(source, refresh_days=7) == "fresh"

    def test_stale(self):
        # Use a date far in the past
        source = {"type": "url", "origin": "https://x.com", "refreshed_at": "2020-01-01T00:00:00+00:00"}
        assert compute_freshness(source, refresh_days=7) == "stale"
