#!/usr/bin/env python3
"""Gather indexed material for a topic and return grouped chunks for LLM wiki synthesis."""

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from lib import config as _config
from lib.retriever import search


def _read_existing_wiki(topic: str) -> list[dict[str, str]]:
    """Read existing wiki articles for a topic. Returns list of {path, content}."""
    topic_dir = _config.WIKI_DIR / topic
    if not topic_dir.exists():
        return []

    articles = []
    for md_file in sorted(topic_dir.glob("*.md")):
        articles.append({
            "filename": md_file.name,
            "content": md_file.read_text(encoding="utf-8", errors="replace"),
        })
    return articles


def _group_chunks(results: list[dict]) -> list[dict]:
    """Group search results by source, preserving section paths."""
    sources: dict[str, dict] = {}
    for r in results:
        key = r["source_name"]
        if key not in sources:
            sources[key] = {
                "source_name": r["source_name"],
                "source_kind": r["source_kind"],
                "origin": r["origin"],
                "sections": [],
            }
        sources[key]["sections"].append({
            "section_path": r["section_path"],
            "content": r["content"],
            "distance": r["distance"],
        })
    return list(sources.values())


def main():
    parser = argparse.ArgumentParser(
        description="Gather indexed material for wiki compilation"
    )
    parser.add_argument("topic", help="Topic name (used as wiki subdirectory)")
    parser.add_argument(
        "--query",
        default=None,
        help="Search query (default: topic name)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=30,
        help="Number of chunks to gather (default: 30)",
    )
    args = parser.parse_args()

    query = args.query or args.topic

    # Gather chunks from the index
    results = search(query=query, top_k=args.top_k)

    if not results:
        print(json.dumps({
            "status": "ok",
            "topic": args.topic,
            "message": "No indexed material found. Add sources first.",
            "grouped_sources": [],
            "existing_wiki": [],
            "wiki_dir": str(_config.WIKI_DIR / args.topic),
        }, indent=2))
        return

    grouped = _group_chunks(results)
    existing = _read_existing_wiki(args.topic)

    print(json.dumps({
        "status": "ok",
        "topic": args.topic,
        "query": query,
        "total_chunks": len(results),
        "grouped_sources": grouped,
        "existing_wiki": existing,
        "wiki_dir": str(_config.WIKI_DIR / args.topic),
    }, indent=2))


if __name__ == "__main__":
    main()
