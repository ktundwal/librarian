#!/usr/bin/env python3
"""Interactive onboarding: show configurable options or apply chosen values."""

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from lib.config import (
    DEFAULT_CONFIG,
    CONFIG_PATH,
    _DEFAULT_WIKI_DIR,
    load_config,
    save_config,
)

# Options exposed during init (embedding_model deliberately excluded).
INIT_OPTIONS = [
    {
        "key": "wiki_dir",
        "label": "Wiki directory",
        "description": (
            "Custom path for compiled wiki articles "
            "(e.g. cloud-synced folder for cross-device access)"
        ),
        "type": "path",
        "default": None,
        "default_label": str(_DEFAULT_WIKI_DIR).replace(
            str(__import__("pathlib").Path.home()), "~"
        ),
    },
    {
        "key": "top_k",
        "label": "Default search results",
        "description": "Number of results returned by /library search",
        "type": "int",
        "default": DEFAULT_CONFIG["top_k"],
        "default_label": str(DEFAULT_CONFIG["top_k"]),
    },
    {
        "key": "chunk_size",
        "label": "Chunk size (tokens)",
        "description": "Token budget per chunk when indexing sources",
        "type": "int",
        "default": DEFAULT_CONFIG["chunk_size"],
        "default_label": str(DEFAULT_CONFIG["chunk_size"]),
    },
    {
        "key": "refresh_days",
        "label": "Refresh interval (days)",
        "description": "Days before URL sources are considered stale",
        "type": "int",
        "default": DEFAULT_CONFIG["refresh_days"],
        "default_label": str(DEFAULT_CONFIG["refresh_days"]),
    },
]

# Keys that can differ from DEFAULT_CONFIG without meaning the user customised them.
_NON_SETTING_KEYS = {"sources", "watchlist"}


def _is_customised(config: dict) -> bool:
    """Return True if config has any non-default *setting* values."""
    for key, default_val in DEFAULT_CONFIG.items():
        if key in _NON_SETTING_KEYS:
            continue
        if config.get(key) != default_val:
            return True
    return False


def _show_options() -> dict:
    config = load_config()
    existing = _is_customised(config)

    options = []
    for opt in INIT_OPTIONS:
        entry = dict(opt)
        entry["current"] = config.get(opt["key"])
        options.append(entry)

    config_path_display = str(CONFIG_PATH).replace(
        str(__import__("pathlib").Path.home()), "~"
    )

    return {
        "status": "ok",
        "existing": existing,
        "config_path": config_path_display,
        "options": options,
    }


def _apply(raw_json: str) -> dict:
    try:
        values = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        return {"status": "error", "message": f"Invalid JSON: {exc}"}

    if not isinstance(values, dict):
        return {"status": "error", "message": "Expected a JSON object"}

    allowed_keys = {opt["key"] for opt in INIT_OPTIONS}
    bad_keys = set(values.keys()) - allowed_keys
    if bad_keys:
        return {
            "status": "error",
            "message": f"Unknown keys: {', '.join(sorted(bad_keys))}",
        }

    # Validate types
    for opt in INIT_OPTIONS:
        if opt["key"] not in values:
            continue
        val = values[opt["key"]]
        if opt["type"] == "int":
            if not isinstance(val, int):
                return {
                    "status": "error",
                    "message": f"'{opt['key']}' must be an integer",
                }
        elif opt["type"] == "path":
            if val is not None and not isinstance(val, str):
                return {
                    "status": "error",
                    "message": f"'{opt['key']}' must be a string path or null",
                }

    config = load_config()
    config.update(values)
    save_config(config)

    config_path_display = str(CONFIG_PATH).replace(
        str(__import__("pathlib").Path.home()), "~"
    )

    return {
        "status": "ok",
        "action": "configured",
        "config_path": config_path_display,
        "applied": values,
    }


def main():
    parser = argparse.ArgumentParser(description="Library init / onboarding")
    parser.add_argument(
        "--apply",
        default=None,
        metavar="JSON",
        help="JSON string of config values to apply",
    )
    args = parser.parse_args()

    if args.apply is not None:
        result = _apply(args.apply)
    else:
        result = _show_options()

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
