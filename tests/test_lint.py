"""Tests for lint.py — health checks across wiki and sources."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lib import config


class TestLintWiki:
    """Wiki structural health checks."""

    def test_empty_wiki_dir(self, tmp_data_dir):
        """Empty wiki dir (no .md files) returns info finding."""
        from lint import _lint_wiki

        findings = _lint_wiki()
        assert len(findings) == 1
        assert findings[0]["severity"] == "info"
        assert "empty" in findings[0]["message"]

    def test_missing_topic_index(self, tmp_data_dir):
        """Topic dir without _index.md gets a warning."""
        topic_dir = tmp_data_dir / "wiki" / "ddia"
        topic_dir.mkdir(parents=True)
        (topic_dir / "replication.md").write_text("# Replication\nContent.")

        from lint import _lint_wiki

        findings = _lint_wiki()
        warnings = [f for f in findings if f["severity"] == "warning"]
        assert any("no _index.md" in w["message"] for w in warnings)

    def test_broken_wiki_link(self, tmp_data_dir):
        """Broken [[link]] in a wiki article is flagged."""
        topic_dir = tmp_data_dir / "wiki" / "ddia"
        topic_dir.mkdir(parents=True)
        (topic_dir / "_index.md").write_text("# DDIA\n")
        (topic_dir / "replication.md").write_text(
            "# Replication\nSee [[nonexistent-article]] for details."
        )

        from lint import _lint_wiki

        findings = _lint_wiki()
        broken = [f for f in findings if "Broken link" in f["message"]]
        assert len(broken) == 1
        assert "nonexistent-article" in broken[0]["message"]

    def test_valid_wiki_link_no_warning(self, tmp_data_dir):
        """Valid [[link]] within same topic does not trigger warning."""
        topic_dir = tmp_data_dir / "wiki" / "ddia"
        topic_dir.mkdir(parents=True)
        (topic_dir / "_index.md").write_text("# DDIA\n- [[replication]]\n- [[consensus]]")
        (topic_dir / "replication.md").write_text("# Replication\nSee [[consensus]].")
        (topic_dir / "consensus.md").write_text("# Consensus\nSee [[replication]].")

        from lint import _lint_wiki

        findings = _lint_wiki()
        broken = [f for f in findings if "Broken link" in f["message"]]
        assert len(broken) == 0

    def test_orphan_article(self, tmp_data_dir):
        """Article not referenced in any _index.md is flagged."""
        topic_dir = tmp_data_dir / "wiki" / "ddia"
        topic_dir.mkdir(parents=True)
        (topic_dir / "_index.md").write_text("# DDIA\n- [[replication]]")
        (topic_dir / "replication.md").write_text("# Replication")
        (topic_dir / "orphan.md").write_text("# Orphan Article")

        from lint import _lint_wiki

        findings = _lint_wiki()
        orphans = [f for f in findings if "Orphan" in f["message"]]
        assert len(orphans) == 1
        assert "orphan" in orphans[0]["message"]


class TestLintSources:
    """Source health checks."""

    def test_no_sources(self, tmp_data_dir):
        """No registered sources returns info."""
        cfg = {**config.DEFAULT_CONFIG}
        config.save_config(cfg)

        from lint import _lint_sources

        findings = _lint_sources(cfg)
        assert len(findings) == 1
        assert "No sources" in findings[0]["message"]

    def test_unindexed_source(self, tmp_data_dir):
        """Source that was never indexed gets a warning."""
        cfg = {**config.DEFAULT_CONFIG, "sources": [{
            "source_id": "abc123",
            "name": "test-book",
            "origin": "/tmp/test.pdf",
            "type": "file",
            "source_kind": "book",
            "added_at": "2026-01-01T00:00:00+00:00",
            "indexed_at": None,
        }]}
        config.save_config(cfg)

        from lint import _lint_sources

        findings = _lint_sources(cfg)
        warnings = [f for f in findings if f["severity"] == "warning"]
        assert any("never been indexed" in w["message"] for w in warnings)

    def test_stale_url_source(self, tmp_data_dir):
        """URL source past refresh_days is flagged as stale."""
        cfg = {**config.DEFAULT_CONFIG, "refresh_days": 7, "sources": [{
            "source_id": "def456",
            "name": "docs.example.com",
            "origin": "https://docs.example.com",
            "type": "url",
            "source_kind": "docs",
            "added_at": "2026-01-01T00:00:00+00:00",
            "indexed_at": "2026-01-01T00:00:00+00:00",
            "refreshed_at": "2025-01-01T00:00:00+00:00",
            "etag": None,
            "last_modified": None,
            "content_hash": "abc",
        }]}
        config.save_config(cfg)

        from lint import _lint_sources

        findings = _lint_sources(cfg)
        stale = [f for f in findings if "stale" in f["message"]]
        assert len(stale) == 1


class TestLintCLI:
    """End-to-end CLI invocation."""

    def test_lint_returns_valid_json(self, tmp_data_dir):
        """CLI returns valid JSON with expected structure."""
        config.save_config(config.DEFAULT_CONFIG)

        result = subprocess.run(
            [sys.executable, "scripts/lint.py", "--scope", "all"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent.parent,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["status"] == "ok"
        assert "total_findings" in data
        assert "summary" in data
        assert "findings" in data
