#!/usr/bin/env python3
"""Re-fetch remote documentation sources and reindex if changed."""

import argparse
import json
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from lib.config import load_config, save_config, compute_freshness
from lib.fetcher import fetch_source
from lib.sources import collect_files, read_file_to_markdown
from lib.chunker import chunk_markdown
from lib.embedder import embed_texts
from lib.indexer import index_chunks


def _reindex_inline(source: dict) -> int:
    """Reindex a single source inline. Returns chunk count."""
    files = collect_files(source)
    if not files:
        return 0

    all_chunks = []
    for f in files:
        text = read_file_to_markdown(f)
        chunks = chunk_markdown(text, source_id=source["source_id"], origin=str(f))
        all_chunks.extend(chunks)

    if not all_chunks:
        return 0

    texts = [c.text for c in all_chunks]
    vectors = embed_texts(texts)

    chunk_dicts = [
        {"text": c.text, "section_path": c.section_path, "chunk_index": c.chunk_index}
        for c in all_chunks
    ]

    return index_chunks(
        chunks=chunk_dicts,
        vectors=vectors,
        source_id=source["source_id"],
        source_name=source["name"],
        source_kind=source.get("source_kind", "docs"),
        origin=source["origin"],
        fetched_at=source.get("refreshed_at"),
    )


def refresh_source(source: dict, force: bool = False, refresh_days: int = 7) -> dict:
    """Refresh a single URL source. Returns summary."""
    sid = source["source_id"]
    name = source["name"]

    if not force:
        freshness = compute_freshness(source, refresh_days)
        if freshness == "fresh":
            return {
                "source_id": sid,
                "name": name,
                "status": "skipped",
                "reason": "still fresh",
            }

    result = fetch_source(source)

    if result["error"]:
        # Track error but keep cached snapshot
        source.setdefault("fetch_error_count", 0)
        source["fetch_error_count"] = source.get("fetch_error_count", 0) + 1
        source["fetch_error"] = result["error"]
        return {
            "source_id": sid,
            "name": name,
            "status": "error",
            "error": result["error"],
        }

    # Clear any previous errors
    source.pop("fetch_error", None)
    source.pop("fetch_error_count", None)

    # Update source metadata
    source["refreshed_at"] = result["fetched_at"]
    source["etag"] = result["etag"]
    source["last_modified"] = result["last_modified"]
    source["content_hash"] = result["content_hash"]

    if not result["changed"]:
        return {
            "source_id": sid,
            "name": name,
            "status": "unchanged",
        }

    # Content changed — reindex inline
    chunks = _reindex_inline(source)
    source["indexed_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "source_id": sid,
        "name": name,
        "status": "refreshed",
        "chunks": chunks,
    }


def main():
    parser = argparse.ArgumentParser(description="Refresh remote documentation sources")
    parser.add_argument(
        "source_name",
        nargs="?",
        default=None,
        help="Name of source to refresh (default: all URL sources)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force refresh even if source is still fresh",
    )
    args = parser.parse_args()

    config = load_config()
    sources = config.get("sources", [])
    refresh_days = config.get("refresh_days", 7)

    url_sources = [s for s in sources if s["type"] == "url"]

    if args.source_name:
        url_sources = [s for s in url_sources if s["name"] == args.source_name]
        if not url_sources:
            print(json.dumps({
                "status": "error",
                "message": f"URL source '{args.source_name}' not found",
            }), file=sys.stderr)
            sys.exit(1)

    if not url_sources:
        print(json.dumps({
            "status": "ok",
            "message": "No URL sources registered.",
            "refreshed": [],
        }, indent=2))
        return

    results = []
    for source in url_sources:
        result = refresh_source(source, force=args.force, refresh_days=refresh_days)
        results.append(result)

    save_config(config)

    print(json.dumps({
        "status": "ok",
        "results": results,
    }, indent=2))


if __name__ == "__main__":
    main()
