---
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# Library Knowledge — Proactive Documentation Retrieval

You have access to a local knowledge library that indexes documentation, books, and papers relevant to AI agent and skill development.

## When to Activate

Proactively search the library when you detect the user is:
- Writing or modifying Claude Code skills or plugins
- Implementing agentic patterns (tool use, multi-step reasoning, orchestration)
- Working with AI provider SDKs (Anthropic, OpenAI, Google, etc.)
- Designing prompt templates or system instructions
- Building MCP servers or tool integrations

## How to Search

Run a search query against the local index:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search.py "<relevant query>" --top-k 3
```

The script returns JSON with ranked results including content excerpts, source attribution, and section paths.

## How to Use Results

1. **Read the JSON output** and identify the most relevant chunks.
2. **Surface key insights** naturally in your response — don't dump raw results.
3. **Always attribute**: mention the source name, section, and origin for any information you reference.
4. **Be selective**: only surface results that are clearly relevant to the current task. If results have low relevance, don't force them into the conversation.

## When No Index Exists

If the search returns empty results or the index doesn't exist, suggest:

> It looks like the library index hasn't been set up yet. You can add sources with:
> ```
> /library add <path-to-docs>
> /library reindex
> ```

## Attribution Format

When citing library results, use this format:

> According to [Source Name] ([section path]):
> > relevant excerpt

## Constraints

- Never fabricate library results — only cite what the search actually returns.
- Don't search on every message — only when the context clearly benefits from grounded documentation.
- Keep searches focused: use specific, targeted queries rather than broad ones.
