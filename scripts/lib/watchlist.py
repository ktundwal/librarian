"""Watchlist CRUD and scout logic."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from lib.channels import Candidate, get_channel
from lib.config import load_config, save_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """Normalize URL for dedup: lowercase, strip trailing slash."""
    return url.lower().rstrip("/")


def _existing_origins(config: dict[str, Any]) -> set[str]:
    """Get normalized URLs of already-registered library sources."""
    origins: set[str] = set()
    for s in config.get("sources", []):
        origin = s.get("origin", "")
        if origin.startswith(("http://", "https://")):
            origins.add(_normalize_url(origin))
    return origins


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_watchlist_entry(
    name: str,
    topics: list[str],
    channels: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a new watchlist entry and save to config. Returns the entry."""
    config = load_config()
    watchlist = config.get("watchlist", [])

    # Check for duplicate name
    for entry in watchlist:
        if entry["name"] == name:
            raise ValueError(f"Watchlist entry '{name}' already exists")

    entry = {
        "name": name,
        "topics": topics,
        "channels": channels,
        "last_checked": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    watchlist.append(entry)
    config["watchlist"] = watchlist
    save_config(config)
    return entry


def list_watchlist_entries() -> list[dict[str, Any]]:
    """Return all watchlist entries."""
    config = load_config()
    return config.get("watchlist", [])


def get_watchlist_entry(name: str) -> dict[str, Any] | None:
    """Get a specific watchlist entry by name."""
    for entry in list_watchlist_entries():
        if entry["name"] == name:
            return entry
    return None


def remove_watchlist_entry(name: str) -> bool:
    """Remove a watchlist entry by name. Returns True if found and removed."""
    config = load_config()
    watchlist = config.get("watchlist", [])
    new_watchlist = [e for e in watchlist if e["name"] != name]
    if len(new_watchlist) == len(watchlist):
        return False
    config["watchlist"] = new_watchlist
    save_config(config)
    return True


def update_last_checked(name: str) -> None:
    """Update the last_checked timestamp for a watchlist entry."""
    config = load_config()
    watchlist = config.get("watchlist", [])
    for entry in watchlist:
        if entry["name"] == name:
            entry["last_checked"] = datetime.now(timezone.utc).isoformat()
            break
    config["watchlist"] = watchlist
    save_config(config)


# ---------------------------------------------------------------------------
# Scout
# ---------------------------------------------------------------------------

def scout(entry: dict[str, Any]) -> tuple[list[Candidate], list[str]]:
    """Scout all channels for a watchlist entry.

    Returns (candidates, errors) where errors is a list of error messages.
    """
    topics = entry["topics"]
    since = entry.get("last_checked")
    config = load_config()
    existing = _existing_origins(config)

    all_candidates: list[Candidate] = []
    errors: list[str] = []

    for ch_config in entry.get("channels", []):
        ch_type = ch_config.get("type", "")
        kwargs = {k: v for k, v in ch_config.items() if k != "type"}

        try:
            channel = get_channel(ch_type)
            candidates = channel.fetch_candidates(topics, since, **kwargs)
            all_candidates.extend(candidates)
        except Exception as exc:
            msg = f"{ch_type}: {exc}"
            print(f"Channel error ({msg})", file=sys.stderr)
            errors.append(msg)

        # Rate limit: sleep after arXiv requests
        if ch_type == "arxiv":
            time.sleep(3)

    # Dedup within results by normalized URL
    seen: set[str] = set()
    unique: list[Candidate] = []
    for c in all_candidates:
        norm = _normalize_url(c.url)
        if norm not in seen:
            seen.add(norm)
            unique.append(c)

    # Filter out already-registered sources
    new = [c for c in unique if _normalize_url(c.url) not in existing]

    return new, errors


def scout_all(
    entry_name: str | None = None,
) -> list[dict[str, Any]]:
    """Scout one or all watchlist entries.

    Returns list of result dicts: [{"name": ..., "candidates": [...], "errors": [...]}]
    """
    entries = list_watchlist_entries()
    if entry_name:
        entries = [e for e in entries if e["name"] == entry_name]
        if not entries:
            raise ValueError(f"Watchlist entry '{entry_name}' not found")

    results = []
    for entry in entries:
        candidates, errors = scout(entry)
        results.append({
            "name": entry["name"],
            "candidates": [c.to_dict() for c in candidates],
            "errors": errors,
        })
        # Update last_checked after scouting
        update_last_checked(entry["name"])

    return results
