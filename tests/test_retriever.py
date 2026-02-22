"""Tests for lib.retriever — focused on the output contract, not the full vector pipeline."""

import types
from unittest.mock import patch, MagicMock

import pyarrow as pa
import pytest

from lib.retriever import search


def _make_arrow_table(rows, has_fetched_at=True):
    """Build a minimal PyArrow table mimicking LanceDB search results."""
    columns = {
        "source_id": [r["source_id"] for r in rows],
        "content": [r["content"] for r in rows],
        "source_name": [r["source_name"] for r in rows],
        "source_kind": [r["source_kind"] for r in rows],
        "section_path": [r["section_path"] for r in rows],
        "origin": [r["origin"] for r in rows],
        "indexed_at": [r["indexed_at"] for r in rows],
        "chunk_id": [r["chunk_id"] for r in rows],
        "_distance": [r["_distance"] for r in rows],
    }
    if has_fetched_at:
        columns["fetched_at"] = [r.get("fetched_at", "") for r in rows]
    return pa.table(columns)


SAMPLE_ROW = {
    "source_id": "abc123",
    "content": "Hello world",
    "source_name": "test",
    "source_kind": "docs",
    "section_path": "Intro",
    "origin": "https://example.com",
    "indexed_at": "2025-01-01T00:00:00",
    "chunk_id": "chunk_1",
    "_distance": 0.42,
    "fetched_at": "2025-01-01T00:00:00",
}


class TestSearchResultContract:
    @patch("lib.retriever.get_sources", return_value=[])
    @patch("lib.retriever.embed_query", return_value=[0.0] * 384)
    @patch("lib.retriever.lancedb")
    def test_result_has_distance_not_score(self, mock_lancedb, mock_embed, mock_sources):
        table = _make_arrow_table([SAMPLE_ROW])
        mock_table = MagicMock()
        mock_table.search.return_value.limit.return_value.to_arrow.return_value = table
        mock_lancedb.connect.return_value.open_table.return_value = mock_table

        results = search("hello", top_k=1)
        assert len(results) == 1
        assert "distance" in results[0]
        assert "score" not in results[0]
        assert results[0]["distance"] == pytest.approx(0.42)

    @patch("lib.retriever.get_sources", return_value=[])
    @patch("lib.retriever.embed_query", return_value=[0.0] * 384)
    @patch("lib.retriever.lancedb")
    def test_empty_index_returns_empty(self, mock_lancedb, mock_embed, mock_sources):
        mock_lancedb.connect.return_value.open_table.side_effect = Exception("Table not found")
        results = search("hello")
        assert results == []

    @patch("lib.retriever.get_sources", return_value=[])
    @patch("lib.retriever.embed_query", return_value=[0.0] * 384)
    @patch("lib.retriever.lancedb")
    def test_missing_fetched_at_column_fallback(self, mock_lancedb, mock_embed, mock_sources):
        table = _make_arrow_table([SAMPLE_ROW], has_fetched_at=False)
        mock_table = MagicMock()
        mock_table.search.return_value.limit.return_value.to_arrow.return_value = table
        mock_lancedb.connect.return_value.open_table.return_value = mock_table

        results = search("hello", top_k=1)
        assert len(results) == 1
        assert results[0]["fetched_at"] == ""

    @patch("lib.retriever.get_sources")
    @patch("lib.retriever.embed_query", return_value=[0.0] * 384)
    @patch("lib.retriever.lancedb")
    def test_freshness_from_source_lookup(self, mock_lancedb, mock_embed, mock_sources):
        mock_sources.return_value = [
            {"source_id": "abc123", "type": "url", "origin": "https://example.com", "refreshed_at": None}
        ]
        table = _make_arrow_table([SAMPLE_ROW])
        mock_table = MagicMock()
        mock_table.search.return_value.limit.return_value.to_arrow.return_value = table
        mock_lancedb.connect.return_value.open_table.return_value = mock_table

        results = search("hello", top_k=1)
        assert results[0]["freshness"] == "never_fetched"
