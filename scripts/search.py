#!/usr/bin/env python3
"""Query the library index."""

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from lib.config import load_config
from lib.retriever import search


def main():
    parser = argparse.ArgumentParser(description="Search the library index")
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--top-k", type=int, default=None, help="Number of results (default: from config)"
    )
    parser.add_argument(
        "--source", choices=["book", "docs", "paper"], default=None,
        help="Filter by source kind"
    )
    args = parser.parse_args()

    config = load_config()
    top_k = args.top_k or config.get("top_k", 5)

    results = search(
        query=args.query,
        top_k=top_k,
        source_filter=args.source,
    )

    print(json.dumps({
        "status": "ok",
        "query": args.query,
        "count": len(results),
        "results": results,
    }, indent=2))


if __name__ == "__main__":
    main()
