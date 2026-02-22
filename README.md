# Librarian

A local-first research scout for coding agents.

**Zero API keys required.** Librarian indexes your docs, books, and papers for grounded retrieval — and now scouts the web for new content matching your interests.

## Who is this for?

- **Solo builders** who curate technical references and want them available during coding
- **Research-heavy engineers** tracking fast-moving fields (AI, biomedical, etc.)
- **Agentic workflows** that benefit from grounded context over generic LLM knowledge

## Quick start

```bash
pip install -e .

# Add and index your docs
/library add <path-or-url>
/library reindex

# Search your library
/library search "vector database indexing"

# Set up automated scouting
/library watch shelf install ai
/library watch check
```

## What it does

### Search & Index (v0.1)
- Add sources from file paths, directories, or URLs
- Fetch URL content with HTML-to-markdown conversion and caching
- Chunk and embed into a local vector index (no external services)
- Semantic search with source attribution in every result
- Refresh stale URL sources on demand

### Watchlist & Scouting (v0.2)
- Define **what you care about** (topics) and **where to look** (channels)
- Scout 5 channel types: **Hacker News**, **arXiv**, **PubMed**, **RSS/Atom**, **GitHub**
- Automatic deduplication (same URL from multiple channels, already-indexed sources)
- Install curated starter templates ("shelves") for instant time-to-value
- Approve candidates → feeds into the existing `/library add` pipeline

### Roadmap
- **v0.3**: MCP server mode for cross-client interoperability
- **v0.4**: Quality ranking, dismiss list, semantic topic matching

## Watchlist

The watchlist automates the discovery half of librarianship: define what you care about and where to look, and the system scouts for candidates on your behalf.

### Create a watchlist entry

```bash
/library watch create "AI advances" \
    --topic "AI agents" --topic "LLM reasoning" \
    --channel hn --channel "arxiv:cs.AI,cs.LG" \
    --channel "rss:https://www.anthropic.com/feed" \
    --channel "github:min_stars=50"
```

### Or install a starter shelf

```bash
/library watch shelf list            # see available templates
/library watch shelf install ai      # AI/ML watchlist
/library watch shelf install biomedical  # cell & gene therapy
```

### Scout for new content

```bash
/library watch check                 # check all entries
/library watch check "AI advances"   # check one entry
```

### Manage entries

```bash
/library watch list                  # list all entries
/library watch remove "AI advances"  # remove an entry
```

### Supported channels

| Channel | Source | Filtering |
|---------|--------|-----------|
| `hn` | Hacker News (Algolia API) | Server-side keyword + min points |
| `arxiv` | arXiv (Atom API) | Server-side keyword + categories |
| `pubmed` | PubMed (E-utilities) | Server-side keyword + date range |
| `rss` | Any RSS/Atom feed | Client-side topic matching |
| `github` | GitHub Search API | Server-side keyword + min stars |

### Channel argument formats

| Argument | Parsed config |
|----------|--------------|
| `hn` | `{"type": "hn"}` |
| `hn:min_points=100` | `{"type": "hn", "min_points": 100}` |
| `arxiv:cs.AI,cs.LG` | `{"type": "arxiv", "categories": ["cs.AI", "cs.LG"]}` |
| `rss:https://example.com/feed` | `{"type": "rss", "url": "https://example.com/feed"}` |
| `github:min_stars=50` | `{"type": "github", "min_stars": 50}` |
| `pubmed` | `{"type": "pubmed"}` |

## Architecture

```
watchlist entry → channels → dedup → candidates (JSON)
                                         ↓ (user approves)
                               /library add <url> → index
```

- **Embeddings:** `fastembed` with `BAAI/bge-small-en-v1.5` (ONNX, no PyTorch)
- **Vector DB:** `LanceDB` (embedded, zero-server)
- **PDF extraction:** `PyMuPDF`
- **Feed parsing:** `feedparser`

All runtime data stored locally at `~/.claude/library-skill/`.

## All commands

```bash
/library add <path-or-url>           # register a source
/library reindex [source-name]       # index registered sources
/library search "<query>"            # search the library
/library status                      # show index health
/library refresh [source-name]       # re-fetch remote docs
/library watch create ...            # create watchlist entry
/library watch list                  # list entries
/library watch check [name]          # scout for candidates
/library watch remove "<name>"       # remove entry
/library watch shelf list            # browse templates
/library watch shelf install <id>    # install template
```

## Privacy & content policy

- Local processing by default — no external vector service
- No source corpus shipped in this repo
- Watchlist channels query public APIs only (no API keys required)
- Users are responsible for adding legally obtained source materials

## License

MIT
