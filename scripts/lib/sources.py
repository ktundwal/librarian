"""Source detection, normalization, and reading."""

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def detect_source_type(path_or_url: str) -> str:
    """Detect whether a source is a file, directory, or URL."""
    if path_or_url.startswith(("http://", "https://")):
        return "url"
    p = Path(path_or_url).expanduser().resolve()
    if p.is_dir():
        return "directory"
    if p.is_file():
        return "file"
    raise ValueError(f"Source not found: {path_or_url}")


def detect_format(path: Path) -> str:
    """Detect file format from extension."""
    suffix = path.suffix.lower()
    format_map = {
        ".md": "markdown",
        ".txt": "text",
        ".pdf": "pdf",
    }
    return format_map.get(suffix, "unknown")


def source_id_from_origin(origin: str) -> str:
    """Generate a stable source ID from origin path/URL."""
    return hashlib.sha256(origin.encode()).hexdigest()[:12]


def build_source_entry(path_or_url: str) -> dict[str, Any]:
    """Build a source config entry from a path or URL."""
    source_type = detect_source_type(path_or_url)
    now = datetime.now(timezone.utc).isoformat()

    if source_type == "url":
        origin = path_or_url
        name = path_or_url.split("//")[-1].split("/")[0]
        source_kind = "docs"
    else:
        p = Path(path_or_url).expanduser().resolve()
        origin = str(p)
        name = p.stem if source_type == "file" else p.name
        source_kind = "book"

    entry = {
        "source_id": source_id_from_origin(origin),
        "name": name,
        "origin": origin,
        "type": source_type,
        "source_kind": source_kind,
        "added_at": now,
        "indexed_at": None,
    }

    if source_type == "url":
        entry.update({
            "refreshed_at": None,
            "etag": None,
            "last_modified": None,
            "content_hash": None,
        })

    return entry


def collect_files(source: dict[str, Any]) -> list[Path]:
    """Collect all indexable files from a source."""
    if source["type"] == "url":
        from .config import CACHE_DIR
        cached = CACHE_DIR / source["source_id"] / "source.md"
        return [cached] if cached.exists() else []

    origin = Path(source["origin"])
    supported = {".md", ".txt", ".pdf"}

    if source["type"] == "file":
        if origin.suffix.lower() in supported:
            return [origin]
        return []

    # directory
    files = []
    for ext in supported:
        files.extend(origin.rglob(f"*{ext}"))
    return sorted(files)


def read_file_to_markdown(path: Path) -> str:
    """Read a file and normalize to markdown text."""
    fmt = detect_format(path)

    if fmt in ("markdown", "text"):
        return path.read_text(encoding="utf-8", errors="replace")

    if fmt == "pdf":
        return _read_pdf(path)

    raise ValueError(f"Unsupported format: {path.suffix}")


def _read_pdf(path: Path) -> str:
    """Extract text from PDF using PyMuPDF."""
    import pymupdf

    doc = pymupdf.open(str(path))
    pages = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text)
    doc.close()
    return "\n\n".join(pages)
