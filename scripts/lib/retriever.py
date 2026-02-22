"""Vector search + result formatting."""

from typing import Any

import lancedb

from .config import INDEX_DIR, compute_freshness, get_sources
from .embedder import embed_query
from .indexer import TABLE_NAME


def search(
    query: str,
    top_k: int = 5,
    source_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Search the index for relevant chunks.

    Args:
        query: Search query string.
        top_k: Number of results to return.
        source_filter: Optional filter by source_kind (book, docs, paper).

    Returns:
        List of result dicts with content, attribution, and score.
    """
    db = lancedb.connect(str(INDEX_DIR))

    try:
        table = db.open_table(TABLE_NAME)
    except Exception:
        return []

    query_vector = embed_query(query)

    search_builder = table.search(query_vector).limit(top_k)

    if source_filter:
        search_builder = search_builder.where(
            f'source_kind = "{source_filter}"'
        )

    results = search_builder.to_arrow()

    if results.num_rows == 0:
        return []

    # Build source lookup for freshness
    sources_by_id = {s["source_id"]: s for s in get_sources()}

    # Check if fetched_at column exists (backwards compat with older indexes)
    column_names = [f.name for f in results.schema]
    has_fetched_at = "fetched_at" in column_names

    formatted = []
    for i in range(results.num_rows):
        source_id = results.column("source_id")[i].as_py()
        source_entry = sources_by_id.get(source_id, {})

        fetched_at = ""
        if has_fetched_at:
            fetched_at = results.column("fetched_at")[i].as_py()

        formatted.append({
            "rank": i + 1,
            "score": float(results.column("_distance")[i].as_py()),
            "content": results.column("content")[i].as_py(),
            "source_name": results.column("source_name")[i].as_py(),
            "source_kind": results.column("source_kind")[i].as_py(),
            "section_path": results.column("section_path")[i].as_py(),
            "origin": results.column("origin")[i].as_py(),
            "indexed_at": results.column("indexed_at")[i].as_py(),
            "chunk_id": results.column("chunk_id")[i].as_py(),
            "fetched_at": fetched_at,
            "freshness": compute_freshness(source_entry),
        })

    return formatted
