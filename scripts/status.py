#!/usr/bin/env python3
"""Show index health and source status."""

import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from lib.config import load_config, compute_freshness
from lib.indexer import get_table_stats


def main():
    config = load_config()
    sources = config.get("sources", [])
    stats = get_table_stats()

    refresh_days = config.get("refresh_days", 7)

    source_status = []
    for source in sources:
        sid = source["source_id"]
        index_info = stats.get("sources", {}).get(sid, {})
        entry = {
            "name": source["name"],
            "source_id": sid,
            "origin": source["origin"],
            "type": source["type"],
            "source_kind": source.get("source_kind", "unknown"),
            "added_at": source.get("added_at"),
            "indexed_at": source.get("indexed_at"),
            "chunks_in_index": index_info.get("chunks", 0),
            "freshness": compute_freshness(source, refresh_days),
        }
        if source.get("type") == "url":
            entry["refreshed_at"] = source.get("refreshed_at")
            if source.get("fetch_error"):
                entry["fetch_error"] = source["fetch_error"]
        source_status.append(entry)

    print(json.dumps({
        "status": "ok",
        "total_chunks": stats.get("total_chunks", 0),
        "sources": source_status,
    }, indent=2))


if __name__ == "__main__":
    main()
