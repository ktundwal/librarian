"""Tests for scripts/init.py."""

import json

import pytest
import yaml

from lib.config import DEFAULT_CONFIG, load_config, save_config

# Import the functions under test.
from init import _show_options, _apply, _is_customised, INIT_OPTIONS


class TestShowOptionsFresh:
    """When no config exists (fresh install), show options with existing=false."""

    def test_returns_existing_false(self, tmp_data_dir):
        result = _show_options()
        assert result["status"] == "ok"
        assert result["existing"] is False

    def test_contains_all_option_keys(self, tmp_data_dir):
        result = _show_options()
        keys = [o["key"] for o in result["options"]]
        assert keys == ["wiki_dir", "top_k", "chunk_size", "refresh_days"]

    def test_current_values_are_defaults(self, tmp_data_dir):
        result = _show_options()
        for opt in result["options"]:
            assert opt["current"] == DEFAULT_CONFIG[opt["key"]]

    def test_config_path_in_output(self, tmp_data_dir):
        result = _show_options()
        assert "config_path" in result


class TestShowOptionsExisting:
    """When config has non-default settings, show existing=true."""

    def test_customised_top_k(self, tmp_data_dir):
        save_config({**DEFAULT_CONFIG, "top_k": 20})
        result = _show_options()
        assert result["existing"] is True

    def test_customised_wiki_dir(self, tmp_data_dir):
        save_config({**DEFAULT_CONFIG, "wiki_dir": "/custom/wiki"})
        result = _show_options()
        assert result["existing"] is True

    def test_current_reflects_saved(self, tmp_data_dir):
        save_config({**DEFAULT_CONFIG, "top_k": 20})
        result = _show_options()
        top_k_opt = next(o for o in result["options"] if o["key"] == "top_k")
        assert top_k_opt["current"] == 20

    def test_sources_do_not_count_as_customisation(self, tmp_data_dir):
        """Adding sources should NOT mark config as customised."""
        cfg = dict(DEFAULT_CONFIG)
        cfg["sources"] = [{"origin": "/some/path", "name": "test"}]
        save_config(cfg)
        result = _show_options()
        assert result["existing"] is False


class TestApply:
    """Test the --apply mode."""

    def test_apply_single_value(self, tmp_data_dir):
        result = _apply('{"top_k": 10}')
        assert result["status"] == "ok"
        assert result["action"] == "configured"
        assert result["applied"] == {"top_k": 10}
        # Verify it was persisted
        config = load_config()
        assert config["top_k"] == 10

    def test_apply_multiple_values(self, tmp_data_dir):
        result = _apply('{"wiki_dir": "~/OneDrive/wiki", "top_k": 10}')
        assert result["status"] == "ok"
        assert result["applied"] == {"wiki_dir": "~/OneDrive/wiki", "top_k": 10}
        config = load_config()
        assert config["wiki_dir"] == "~/OneDrive/wiki"
        assert config["top_k"] == 10

    def test_apply_partial_preserves_other_keys(self, tmp_data_dir):
        """Applying top_k should not reset chunk_size."""
        save_config({**DEFAULT_CONFIG, "chunk_size": 1024})
        result = _apply('{"top_k": 10}')
        assert result["status"] == "ok"
        config = load_config()
        assert config["top_k"] == 10
        assert config["chunk_size"] == 1024

    def test_apply_invalid_json(self, tmp_data_dir):
        result = _apply("{not valid json")
        assert result["status"] == "error"
        assert "Invalid JSON" in result["message"]

    def test_apply_non_object(self, tmp_data_dir):
        result = _apply('"just a string"')
        assert result["status"] == "error"
        assert "Expected a JSON object" in result["message"]

    def test_apply_unknown_key(self, tmp_data_dir):
        result = _apply('{"embedding_model": "other"}')
        assert result["status"] == "error"
        assert "Unknown keys" in result["message"]

    def test_apply_wrong_type_int(self, tmp_data_dir):
        result = _apply('{"top_k": "not_a_number"}')
        assert result["status"] == "error"
        assert "must be an integer" in result["message"]

    def test_apply_wiki_dir_null(self, tmp_data_dir):
        """Setting wiki_dir to null should reset to default."""
        save_config({**DEFAULT_CONFIG, "wiki_dir": "/custom"})
        result = _apply('{"wiki_dir": null}')
        assert result["status"] == "ok"
        config = load_config()
        assert config["wiki_dir"] is None


class TestIsCustomised:
    def test_default_config(self):
        assert _is_customised(dict(DEFAULT_CONFIG)) is False

    def test_changed_top_k(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["top_k"] = 99
        assert _is_customised(cfg) is True

    def test_sources_ignored(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["sources"] = [{"origin": "x"}]
        assert _is_customised(cfg) is False

    def test_watchlist_ignored(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["watchlist"] = [{"name": "x"}]
        assert _is_customised(cfg) is False
