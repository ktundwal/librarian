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
Register a local file, directory, or URL as a library source.
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

## Dispatch Rules

1. Parse `$ARGUMENTS` to identify the subcommand (first word) and remaining args.
2. Run the corresponding script via Bash. Always quote user-provided paths and queries.
3. The scripts output JSON. Read the JSON and format a clear, human-readable response:
   - For **add**: Confirm what was added with source name and origin.
   - For **reindex**: Show per-source results (files processed, chunks created).
   - For **search**: Display results as a numbered list with excerpts, section paths, and source attribution.
   - For **status**: Show a summary table of sources and their health.
   - For **refresh**: Show refresh status or the M1 stub message.
4. If the subcommand is missing or unrecognized, show available subcommands.
5. If a script returns an error, display the error message clearly.

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
