"""LanceDB operations for vector storage."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa

from .config import INDEX_DIR

TABLE_NAME = "library"


def _get_db():
    """Open/create the LanceDB database."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(INDEX_DIR))


def _content_hash(text: str) -> str:
    """SHA-256 hash of chunk content."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _chunk_id(source_id: str, chunk_index: int) -> str:
    """Deterministic chunk ID."""
    return f"{source_id}_{chunk_index:06d}"


def index_chunks(
    chunks: list[dict[str, Any]],
    vectors: list[list[float]],
    source_id: str,
    source_name: str,
    source_kind: str,
    origin: str,
    fetched_at: str | None = None,
) -> int:
    """Insert or replace chunks for a source in the index.

    Each chunk dict should have: text, section_path, chunk_index.
    Returns the number of chunks indexed.
    """
    db = _get_db()
    now = datetime.now(timezone.utc).isoformat()

    records = []
    for chunk, vector in zip(chunks, vectors):
        records.append({
            "chunk_id": _chunk_id(source_id, chunk["chunk_index"]),
            "source_id": source_id,
            "source_name": source_name,
            "source_kind": source_kind,
            "origin": origin,
            "section_path": chunk["section_path"],
            "content": chunk["text"],
            "content_hash": _content_hash(chunk["text"]),
            "indexed_at": now,
            "fetched_at": fetched_at or "",
            "vector": vector,
        })

    if not records:
        return 0

    # Delete existing chunks for this source, then add new ones
    try:
        table = db.open_table(TABLE_NAME)
        # Migrate schema: add fetched_at column if missing
        schema_names = [f.name for f in table.schema]
        if "fetched_at" not in schema_names:
            table.add_columns({"fetched_at": "''"})
        table.delete(f'source_id = "{source_id}"')
        table.add(records)
    except (FileNotFoundError, ValueError):
        # Table doesn't exist yet — create it
        db.create_table(TABLE_NAME, data=records)

    return len(records)


def delete_source(source_id: str) -> int:
    """Delete all chunks for a source. Returns count deleted."""
    db = _get_db()
    try:
        table = db.open_table(TABLE_NAME)
        # Count before delete
        count = table.count_rows(f'source_id = "{source_id}"')
        table.delete(f'source_id = "{source_id}"')
        return count
    except Exception:
        return 0


def get_table_stats() -> dict[str, Any]:
    """Get index statistics."""
    db = _get_db()
    try:
        table = db.open_table(TABLE_NAME)
        total = table.count_rows()
        # Get unique sources via Arrow
        arrow_table = table.to_arrow()
        source_ids = arrow_table.column("source_id").to_pylist()
        source_names = arrow_table.column("source_name").to_pylist()
        source_kinds = arrow_table.column("source_kind").to_pylist()
        indexed_ats = arrow_table.column("indexed_at").to_pylist()

        sources = {}
        for sid, name, kind, idx_at in zip(source_ids, source_names, source_kinds, indexed_ats):
            if sid not in sources:
                sources[sid] = {"name": name, "kind": kind, "chunks": 0, "indexed_at": idx_at}
            sources[sid]["chunks"] += 1
        return {"total_chunks": total, "sources": sources}
    except Exception:
        return {"total_chunks": 0, "sources": {}}
