"""Tests for compile.py — gather + group indexed material for wiki synthesis."""

import pytest

from lib import config


class TestCompileGather:
    """Test the compile script's gather and grouping logic."""

    def test_no_index_returns_empty(self, tmp_data_dir):
        """When no index exists, search returns nothing and compile gets empty results."""
        from compile import _read_existing_wiki, _group_chunks

        # No wiki articles exist
        articles = _read_existing_wiki("test-topic")
        assert articles == []

        # No chunks to group
        grouped = _group_chunks([])
        assert grouped == []

    def test_existing_wiki_articles_returned(self, tmp_data_dir):
        """When wiki articles exist for a topic, they're included in output."""
        topic_dir = tmp_data_dir / "wiki" / "ddia"
        topic_dir.mkdir(parents=True)
        (topic_dir / "_index.md").write_text("# DDIA\n- [[replication]]")
        (topic_dir / "replication.md").write_text("# Replication\nContent here.")

        from compile import _read_existing_wiki

        articles = _read_existing_wiki("ddia")
        assert len(articles) == 2
        filenames = [a["filename"] for a in articles]
        assert "_index.md" in filenames
        assert "replication.md" in filenames

    def test_group_chunks_by_source(self):
        """Chunks from the same source are grouped together."""
        from compile import _group_chunks

        results = [
            {
                "source_name": "ddia.pdf",
                "source_kind": "book",
                "origin": "/books/ddia.pdf",
                "section_path": "Chapter 5 > Replication",
                "content": "chunk 1",
                "distance": 0.1,
            },
            {
                "source_name": "ddia.pdf",
                "source_kind": "book",
                "origin": "/books/ddia.pdf",
                "section_path": "Chapter 7 > Transactions",
                "content": "chunk 2",
                "distance": 0.2,
            },
            {
                "source_name": "raft-paper.pdf",
                "source_kind": "paper",
                "origin": "/papers/raft.pdf",
                "section_path": "Abstract",
                "content": "chunk 3",
                "distance": 0.3,
            },
        ]

        grouped = _group_chunks(results)
        assert len(grouped) == 2

        ddia = next(g for g in grouped if g["source_name"] == "ddia.pdf")
        assert len(ddia["sections"]) == 2
        assert ddia["source_kind"] == "book"

        raft = next(g for g in grouped if g["source_name"] == "raft-paper.pdf")
        assert len(raft["sections"]) == 1

    def test_empty_wiki_dir(self, tmp_data_dir):
        """Non-existent topic dir returns empty list."""
        from compile import _read_existing_wiki

        articles = _read_existing_wiki("nonexistent")
        assert articles == []
