#!/usr/bin/env python3
"""Register a source in config."""

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from lib.config import add_source
from lib.sources import build_source_entry


def main():
    parser = argparse.ArgumentParser(description="Add a source to the library")
    parser.add_argument("path_or_url", help="File path, directory, or URL to add")
    args = parser.parse_args()

    try:
        entry = build_source_entry(args.path_or_url)
        add_source(entry)
        print(json.dumps({
            "status": "ok",
            "action": "added",
            "source": entry,
        }, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
