"""CLI entry point for watchlist operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lib.watchlist import (
    create_watchlist_entry,
    list_watchlist_entries,
    remove_watchlist_entry,
    scout_all,
)

SHELVES_DIR = Path(__file__).resolve().parent.parent / "shelves"


# ---------------------------------------------------------------------------
# Channel argument parsing
# ---------------------------------------------------------------------------

def parse_channel_arg(raw: str) -> dict[str, Any]:
    """Parse a --channel CLI argument into a config dict.

    Formats:
        hn                        → {"type": "hn"}
        hn:min_points=100         → {"type": "hn", "min_points": 100}
        arxiv:cs.AI,cs.LG         → {"type": "arxiv", "categories": ["cs.AI", "cs.LG"]}
        rss:https://example.com   → {"type": "rss", "url": "https://..."}
        github:min_stars=50       → {"type": "github", "min_stars": 50}
        pubmed                    → {"type": "pubmed"}
    """
    if ":" not in raw:
        return {"type": raw}

    ch_type, rest = raw.split(":", 1)
    config: dict[str, Any] = {"type": ch_type}

    if ch_type == "rss":
        config["url"] = rest
    elif ch_type == "arxiv" and "=" not in rest:
        # arxiv:cs.AI,cs.LG → categories list
        config["categories"] = [c.strip() for c in rest.split(",")]
    elif "=" in rest:
        # key=value parsing (e.g., min_points=100, min_stars=50)
        key, value = rest.split("=", 1)
        # Try numeric conversion
        try:
            config[key] = int(value)
        except ValueError:
            config[key] = value
    else:
        # Fallback: treat as simple value
        config["value"] = rest

    return config


# ---------------------------------------------------------------------------
# Shelf helpers
# ---------------------------------------------------------------------------

def list_shelves() -> list[dict[str, Any]]:
    """List available shelf templates."""
    if not SHELVES_DIR.is_dir():
        return []
    shelves = []
    for f in sorted(SHELVES_DIR.glob("*.yaml")):
        import yaml
        with open(f) as fh:
            data = yaml.safe_load(fh)
        if data:
            shelves.append({
                "id": f.stem,
                "name": data.get("name", f.stem),
                "topics": data.get("topics", []),
                "channels": len(data.get("channels", [])),
            })
    return shelves


def install_shelf(shelf_id: str) -> dict[str, Any]:
    """Install a shelf template as a watchlist entry."""
    import yaml
    shelf_path = SHELVES_DIR / f"{shelf_id}.yaml"
    if not shelf_path.exists():
        raise ValueError(f"Shelf '{shelf_id}' not found. Available: {[s['id'] for s in list_shelves()]}")
    with open(shelf_path) as f:
        data = yaml.safe_load(f)
    return create_watchlist_entry(
        name=data["name"],
        topics=data["topics"],
        channels=data["channels"],
    )


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _output(data: dict[str, Any]) -> None:
    json.dump(data, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def _error(message: str) -> None:
    _output({"status": "error", "message": message})
    sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_create(args: argparse.Namespace) -> None:
    if not args.topic:
        _error("At least one --topic is required")
    if not args.channel:
        _error("At least one --channel is required")

    channels = [parse_channel_arg(c) for c in args.channel]
    try:
        entry = create_watchlist_entry(args.name, args.topic, channels)
        _output({"status": "ok", "action": "created", "entry": entry})
    except ValueError as exc:
        _error(str(exc))


def cmd_list(args: argparse.Namespace) -> None:
    entries = list_watchlist_entries()
    _output({"status": "ok", "count": len(entries), "entries": entries})


def cmd_check(args: argparse.Namespace) -> None:
    try:
        results = scout_all(args.name if args.name else None)
        _output({"status": "ok", "results": results})
    except ValueError as exc:
        _error(str(exc))


def cmd_remove(args: argparse.Namespace) -> None:
    removed = remove_watchlist_entry(args.name)
    if removed:
        _output({"status": "ok", "action": "removed", "name": args.name})
    else:
        _error(f"Watchlist entry '{args.name}' not found")


def cmd_shelf(args: argparse.Namespace) -> None:
    if args.shelf_action == "list":
        shelves = list_shelves()
        _output({"status": "ok", "count": len(shelves), "shelves": shelves})
    elif args.shelf_action == "install":
        if not args.shelf_name:
            _error("Shelf name is required: shelf install <name>")
        try:
            entry = install_shelf(args.shelf_name)
            _output({"status": "ok", "action": "installed", "entry": entry})
        except ValueError as exc:
            _error(str(exc))
    else:
        _error(f"Unknown shelf action: {args.shelf_action}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="watch",
        description="Watchlist management for Librarian",
    )
    sub = parser.add_subparsers(dest="command")

    # create
    p_create = sub.add_parser("create", help="Create a watchlist entry")
    p_create.add_argument("name", help="Name for the watchlist entry")
    p_create.add_argument("--topic", action="append", default=[], help="Topic to watch for (repeatable)")
    p_create.add_argument("--channel", action="append", default=[], help="Channel spec (repeatable)")

    # list
    sub.add_parser("list", help="List all watchlist entries")

    # check
    p_check = sub.add_parser("check", help="Scout for new candidates")
    p_check.add_argument("name", nargs="?", default=None, help="Entry name (all if omitted)")

    # remove
    p_remove = sub.add_parser("remove", help="Remove a watchlist entry")
    p_remove.add_argument("name", help="Entry name to remove")

    # shelf
    p_shelf = sub.add_parser("shelf", help="Manage shelf templates")
    p_shelf.add_argument("shelf_action", choices=["list", "install"], help="Shelf action")
    p_shelf.add_argument("shelf_name", nargs="?", default=None, help="Shelf ID (for install)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "create": cmd_create,
        "list": cmd_list,
        "check": cmd_check,
        "remove": cmd_remove,
        "shelf": cmd_shelf,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
