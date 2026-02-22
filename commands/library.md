---
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# /library — Personal Knowledge Layer

You are the `/library` command handler. Parse the user's arguments and dispatch to the appropriate Python script.

## Arguments

The user invoked: `/library $ARGUMENTS`

## Subcommands

### `add <path-or-url>`
Register a local file, directory, or URL as a library source. Automatically indexes after adding (no separate `reindex` needed).
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/add.py "<path-or-url>"
```

### `reindex [source-name]`
Chunk, embed, and index registered sources. If a source name is given, only reindex that source.
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/reindex.py [source-name]
```

### `search <query> [--top-k N] [--source book|docs|paper]`
Search the indexed library for relevant chunks.
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search.py "<query>" [--top-k N] [--source <kind>]
```

### `status`
Show index health: total chunks, per-source status, last indexed time.
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py
```

### `refresh [source-name] [--force]`
Re-fetch remote documentation sources. Skips sources that are still fresh (within `refresh_days`, default 7). Use `--force` to re-fetch regardless of freshness. If content changed, automatically reindexes.
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/refresh.py [source-name] [--force]
```

### `watch create "<name>" --topic "<topic>" --channel <spec>`
Create a watchlist entry to monitor channels for new content matching your topics.
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/watch.py create "<name>" --topic "<topic1>" --topic "<topic2>" --channel <channel-spec> --channel <channel-spec>
```
Channel spec formats: `hn`, `hn:min_points=100`, `arxiv:cs.AI,cs.LG`, `rss:<feed-url>`, `github:min_stars=50`, `pubmed`

### `watch list`
List all watchlist entries.
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/watch.py list
```

### `watch check [name]`
Scout all channels for new content matching watchlist topics. If a name is given, only check that entry.
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/watch.py check [name]
```
Present candidates conversationally. If the user wants to add any, call `/library add <url>` for each.

### `watch remove "<name>"`
Remove a watchlist entry.
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/watch.py remove "<name>"
```

### `watch shelf list`
List available pre-built watchlist templates.
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/watch.py shelf list
```

### `watch shelf install <id>`
Install a shelf template as a watchlist entry.
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/watch.py shelf install <id>
```

## Dispatch Rules

1. Parse `$ARGUMENTS` to identify the subcommand (first word) and remaining args.
2. For `watch` subcommands, the second word is the watch action (`create`, `list`, `check`, `remove`, `shelf`).
3. Run the corresponding script via Bash. Always quote user-provided paths and queries.
4. The scripts output JSON. Read the JSON and format a clear, human-readable response:
   - For **add**: Confirm what was added with source name and origin.
   - For **reindex**: Show per-source results (files processed, chunks created).
   - For **search**: Display results as a numbered list with excerpts, section paths, and source attribution.
   - For **status**: Show a summary table of sources and their health.
   - For **refresh**: Show refresh status or the M1 stub message.
   - For **watch create**: Confirm the entry was created with its topics and channels.
   - For **watch list**: Show entries with their topics, channels, and last checked time.
   - For **watch check**: Present candidates as a numbered list with title, URL, channel, and summary. Offer to add any the user likes.
   - For **watch remove**: Confirm removal.
   - For **watch shelf list**: Show available shelves with their topics.
   - For **watch shelf install**: Confirm the shelf was installed.
5. If the subcommand is missing or unrecognized, show available subcommands.
6. If a script returns an error, display the error message clearly.

## Error Handling

If `$ARGUMENTS` is empty, respond with:

> **Usage:** `/library <subcommand> [args]`
>
> **Subcommands:**
> - `add <path-or-url>` — Register a source
> - `reindex [source-name]` — Index registered sources
> - `search <query>` — Search the library
> - `status` — Show index health
> - `refresh` — Re-fetch remote docs
> - `watch create` — Create a watchlist entry
> - `watch list` — List watchlist entries
> - `watch check` — Scout for new content
> - `watch remove` — Remove a watchlist entry
> - `watch shelf list` — Browse starter templates
> - `watch shelf install` — Install a template
