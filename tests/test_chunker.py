"""Tests for lib.chunker."""

from lib.chunker import (
    estimate_tokens,
    chunk_markdown,
    _split_by_paragraphs,
    _split_by_lines,
)


class TestEstimateTokens:
    def test_empty(self):
        assert estimate_tokens("") == 0

    def test_known_length(self):
        # 100 chars → 25 tokens
        assert estimate_tokens("a" * 100) == 25

    def test_short(self):
        assert estimate_tokens("hi") == 0  # 2 // 4 = 0


class TestSplitByParagraphs:
    def test_small_text_unsplit(self):
        text = "Short paragraph."
        result = _split_by_paragraphs(text, max_tokens=512)
        assert result == [text]

    def test_splits_on_double_newline(self):
        para1 = "a" * 1200  # ~300 tokens
        para2 = "b" * 1200  # ~300 tokens
        text = f"{para1}\n\n{para2}"
        result = _split_by_paragraphs(text, max_tokens=512)
        assert len(result) == 2
        assert para1 in result[0]
        assert para2 in result[1]

    def test_oversized_paragraph_falls_through_to_lines(self):
        # A single giant paragraph with no \n\n breaks but with \n breaks
        lines = ["line " * 40 for _ in range(20)]  # each line ~200 chars = ~50 tokens
        text = "\n".join(lines)  # ~4000 chars, ~1000 tokens, no \n\n
        result = _split_by_paragraphs(text, max_tokens=512)
        # Should produce multiple chunks since _split_by_lines kicks in
        assert len(result) >= 2
        for chunk in result:
            assert estimate_tokens(chunk) <= 512


class TestSplitByLines:
    def test_small_text_unsplit(self):
        text = "One line."
        result = _split_by_lines(text, max_tokens=512)
        assert result == [text]

    def test_splits_on_newline(self):
        lines = ["x" * 800 for _ in range(4)]  # each ~200 tokens
        text = "\n".join(lines)
        result = _split_by_lines(text, max_tokens=512)
        assert len(result) >= 2
        for chunk in result:
            assert estimate_tokens(chunk) <= 512


class TestChunkMarkdown:
    def test_empty_input(self):
        assert chunk_markdown("") == []

    def test_single_section(self):
        md = "# Title\n\nSome content here."
        chunks = chunk_markdown(md)
        assert len(chunks) == 1
        assert "Some content here" in chunks[0].text
        assert chunks[0].section_path == "Title"

    def test_heading_hierarchy(self, sample_markdown):
        chunks = chunk_markdown(sample_markdown)
        paths = [c.section_path for c in chunks]
        assert any("Introduction" in p for p in paths)
        assert any("Section A" in p for p in paths)
        assert any("Subsection B1" in p for p in paths)
        assert any("Subsection B2" in p for p in paths)

    def test_oversized_paragraph_split(self, oversized_paragraph):
        md = f"# Big Section\n\n{oversized_paragraph}"
        chunks = chunk_markdown(md, max_tokens=512)
        assert len(chunks) >= 2
        for c in chunks:
            assert estimate_tokens(c.text) <= 512

    def test_sequential_chunk_indices(self, sample_markdown):
        chunks = chunk_markdown(sample_markdown)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_metadata_passed_through(self):
        md = "# H\n\nContent."
        chunks = chunk_markdown(md, source_id="s1", origin="/path")
        assert chunks[0].metadata["source_id"] == "s1"
        assert chunks[0].metadata["origin"] == "/path"
