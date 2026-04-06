"""Shared fixtures for library-skill tests."""

import pytest
from pathlib import Path

from lib import config


@pytest.fixture()
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirect all config paths to a temp directory so tests never touch ~/.claude/library-skill/."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.yaml")
    monkeypatch.setattr(config, "INDEX_DIR", tmp_path / "index")
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache" / "sources")
    monkeypatch.setattr(config, "_DEFAULT_WIKI_DIR", tmp_path / "wiki")
    return tmp_path


@pytest.fixture()
def sample_markdown():
    """Multi-section markdown for chunker tests."""
    return """\
# Introduction

This is the introduction paragraph.

## Section A

Content of section A with enough detail to test paragraph splitting.

## Section B

### Subsection B1

Details in B1.

### Subsection B2

Details in B2.

## Section C

Final section content.
"""


@pytest.fixture()
def oversized_paragraph():
    """A single paragraph exceeding the 512-token budget (~2048 chars at 4 chars/token), with line breaks."""
    # Each line ~200 chars (~50 tokens), 20 lines = ~1000 tokens total
    return "\n".join(["word " * 40 for _ in range(20)])
