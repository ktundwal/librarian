"""Load/save ~/.claude/library-skill/config.yaml"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path.home() / ".claude" / "library-skill"
CONFIG_PATH = DATA_DIR / "config.yaml"
INDEX_DIR = DATA_DIR / "index"
CACHE_DIR = DATA_DIR / "cache" / "sources"

DEFAULT_CONFIG: dict[str, Any] = {
    "sources": [],
    "embedding_model": "BAAI/bge-small-en-v1.5",
    "chunk_size": 512,
    "top_k": 5,
    "refresh_days": 7,
}


def ensure_dirs() -> None:
    """Create data directories if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    """Load config from disk, creating defaults if missing."""
    import sys

    ensure_dirs()
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH) as f:
            loaded = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(f"Warning: invalid config YAML, using defaults: {exc}", file=sys.stderr)
        return dict(DEFAULT_CONFIG)
    if not isinstance(loaded, dict):
        return dict(DEFAULT_CONFIG)
    merged = dict(DEFAULT_CONFIG)
    merged.update(loaded)
    return merged


def save_config(config: dict[str, Any]) -> None:
    """Write config to disk."""
    ensure_dirs()
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def add_source(source: dict[str, Any]) -> dict[str, Any]:
    """Add a source entry to config. Returns the updated config."""
    config = load_config()
    # Deduplicate by origin
    existing_origins = {s["origin"] for s in config["sources"]}
    if source["origin"] in existing_origins:
        # Update existing
        config["sources"] = [
            source if s["origin"] == source["origin"] else s
            for s in config["sources"]
        ]
    else:
        config["sources"].append(source)
    save_config(config)
    return config


def remove_source(origin: str) -> dict[str, Any]:
    """Remove a source by origin. Returns the updated config."""
    config = load_config()
    config["sources"] = [s for s in config["sources"] if s["origin"] != origin]
    save_config(config)
    return config


def get_sources() -> list[dict[str, Any]]:
    """Return all registered sources."""
    return load_config().get("sources", [])


def compute_freshness(source: dict[str, Any], refresh_days: int | None = None) -> str:
    """Compute freshness status for a source.

    Returns: "fresh" | "stale" | "never_fetched" | "n/a"
    """
    if source.get("type") != "url":
        return "n/a"

    refreshed_at = source.get("refreshed_at")
    if not refreshed_at:
        return "never_fetched"

    if refresh_days is None:
        refresh_days = load_config().get("refresh_days", DEFAULT_CONFIG["refresh_days"])

    refreshed = datetime.fromisoformat(refreshed_at)
    age = datetime.now(timezone.utc) - refreshed
    if age.total_seconds() < refresh_days * 86400:
        return "fresh"
    return "stale"
