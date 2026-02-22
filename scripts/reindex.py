#!/usr/bin/env python3
"""Chunk, embed, and index all registered sources."""

import argparse
import json
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from lib.config import load_config, save_config
from lib.fetcher import fetch_source
from lib.sources import collect_files, read_file_to_markdown
from lib.chunker import chunk_markdown
from lib.embedder import embed_texts
from lib.indexer import index_chunks


def _auto_fetch(source: dict) -> str | None:
    """Auto-fetch URL sources that have never been fetched. Returns error or None."""
    if source.get("type") != "url":
        return None
    if source.get("refreshed_at") is not None:
        return None

    result = fetch_source(source)
    if result["error"]:
        return result["error"]

    # Update source metadata in-place
    source["refreshed_at"] = result["fetched_at"]
    source["etag"] = result["etag"]
    source["last_modified"] = result["last_modified"]
    source["content_hash"] = result["content_hash"]
    return None


def reindex_source(source: dict) -> dict:
    """Reindex a single source. Returns summary."""
    # Auto-fetch URL sources on first reindex
    fetch_err = _auto_fetch(source)
    if fetch_err:
        return {
            "source_id": source["source_id"],
            "name": source["name"],
            "status": "error",
            "reason": f"fetch failed: {fetch_err}",
        }

    files = collect_files(source)
    if not files:
        return {
            "source_id": source["source_id"],
            "name": source["name"],
            "status": "skipped",
            "reason": "no indexable files found",
        }

    all_chunks = []
    for f in files:
        try:
            text = read_file_to_markdown(f)
            chunks = chunk_markdown(
                text,
                source_id=source["source_id"],
                origin=str(f),
            )
            all_chunks.extend(chunks)
        except Exception as e:
            print(
                json.dumps({"warning": f"Failed to read {f}: {e}"}),
                file=sys.stderr,
            )

    if not all_chunks:
        return {
            "source_id": source["source_id"],
            "name": source["name"],
            "status": "skipped",
            "reason": "no chunks produced",
        }

    # Embed all chunks
    texts = [c.text for c in all_chunks]
    vectors = embed_texts(texts)

    # Build chunk dicts for indexer
    chunk_dicts = [
        {
            "text": c.text,
            "section_path": c.section_path,
            "chunk_index": c.chunk_index,
        }
        for c in all_chunks
    ]

    count = index_chunks(
        chunks=chunk_dicts,
        vectors=vectors,
        source_id=source["source_id"],
        source_name=source["name"],
        source_kind=source.get("source_kind", "book"),
        origin=source["origin"],
        fetched_at=source.get("refreshed_at"),
    )

    return {
        "source_id": source["source_id"],
        "name": source["name"],
        "status": "indexed",
        "files": len(files),
        "chunks": count,
    }


def main():
    parser = argparse.ArgumentParser(description="Reindex library sources")
    parser.add_argument(
        "source_name",
        nargs="?",
        default=None,
        help="Name of source to reindex (default: all)",
    )
    args = parser.parse_args()

    config = load_config()
    sources = config.get("sources", [])

    if not sources:
        print(json.dumps({
            "status": "ok",
            "message": "No sources registered. Use 'add' first.",
            "results": [],
        }, indent=2))
        return

    if args.source_name:
        sources = [s for s in sources if s["name"] == args.source_name]
        if not sources:
            print(json.dumps({
                "status": "error",
                "message": f"Source '{args.source_name}' not found",
            }), file=sys.stderr)
            sys.exit(1)

    results = []
    for source in sources:
        result = reindex_source(source)
        results.append(result)
        # Update indexed_at in config
        if result["status"] == "indexed":
            source["indexed_at"] = datetime.now(timezone.utc).isoformat()

    save_config(config)

    print(json.dumps({
        "status": "ok",
        "results": results,
    }, indent=2))


if __name__ == "__main__":
    main()
