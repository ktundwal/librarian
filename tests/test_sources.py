"""Tests for lib.sources."""

import pytest
from pathlib import Path

from lib.sources import (
    detect_source_type,
    source_id_from_origin,
    build_source_entry,
    collect_files,
    detect_format,
)


class TestDetectSourceType:
    def test_http_url(self):
        assert detect_source_type("http://example.com") == "url"

    def test_https_url(self):
        assert detect_source_type("https://docs.python.org") == "url"

    def test_existing_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("hello")
        assert detect_source_type(str(f)) == "file"

    def test_existing_directory(self, tmp_path):
        assert detect_source_type(str(tmp_path)) == "directory"

    def test_nonexistent_path(self, tmp_path):
        with pytest.raises(ValueError, match="Source not found"):
            detect_source_type(str(tmp_path / "nope.md"))


class TestSourceIdFromOrigin:
    def test_deterministic(self):
        a = source_id_from_origin("https://example.com")
        b = source_id_from_origin("https://example.com")
        assert a == b

    def test_length(self):
        sid = source_id_from_origin("/some/path")
        assert len(sid) == 12

    def test_different_origins_differ(self):
        a = source_id_from_origin("a")
        b = source_id_from_origin("b")
        assert a != b


class TestBuildSourceEntry:
    def test_url_source(self):
        entry = build_source_entry("https://docs.python.org/3/")
        assert entry["type"] == "url"
        assert entry["source_kind"] == "docs"
        assert entry["origin"] == "https://docs.python.org/3/"
        assert "refreshed_at" in entry

    def test_file_source(self, tmp_path):
        f = tmp_path / "book.pdf"
        f.write_text("content")
        entry = build_source_entry(str(f))
        assert entry["type"] == "file"
        assert entry["source_kind"] == "book"
        assert entry["name"] == "book"
        assert "refreshed_at" not in entry

    def test_directory_source(self, tmp_path):
        entry = build_source_entry(str(tmp_path))
        assert entry["type"] == "directory"
        assert entry["source_kind"] == "book"


class TestCollectFiles:
    def test_file_source(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# Hello")
        source = {"type": "file", "origin": str(f)}
        assert collect_files(source) == [f]

    def test_unsupported_file(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("a,b,c")
        source = {"type": "file", "origin": str(f)}
        assert collect_files(source) == []

    def test_directory_source(self, tmp_path):
        (tmp_path / "a.md").write_text("# A")
        (tmp_path / "b.txt").write_text("B")
        (tmp_path / "c.py").write_text("pass")  # not supported
        source = {"type": "directory", "origin": str(tmp_path)}
        files = collect_files(source)
        extensions = {f.suffix for f in files}
        assert ".md" in extensions
        assert ".txt" in extensions
        assert ".py" not in extensions

    def test_url_source_no_cache(self, tmp_data_dir):
        source = {"type": "url", "source_id": "abc123", "origin": "https://x.com"}
        assert collect_files(source) == []

    def test_url_source_with_cache(self, tmp_data_dir):
        cache_dir = tmp_data_dir / "cache" / "sources" / "abc123"
        cache_dir.mkdir(parents=True)
        cached = cache_dir / "source.md"
        cached.write_text("# Cached")
        source = {"type": "url", "source_id": "abc123", "origin": "https://x.com"}
        assert collect_files(source) == [cached]


class TestDetectFormat:
    def test_markdown(self):
        assert detect_format(Path("doc.md")) == "markdown"

    def test_text(self):
        assert detect_format(Path("notes.txt")) == "text"

    def test_pdf(self):
        assert detect_format(Path("paper.pdf")) == "pdf"

    def test_unknown(self):
        assert detect_format(Path("data.csv")) == "unknown"

    def test_case_insensitive(self):
        assert detect_format(Path("DOC.MD")) == "markdown"
