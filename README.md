# Librarian

A personal knowledge layer for coding agents.

> *"I think there is room here for an incredible new product instead of a hacky collection of scripts."*
> -- [Andrej Karpathy, "LLM Knowledge Bases"](https://x.com/karpathy/status/1907535042378424452) (April 2, 2026)

Librarian implements the pattern Karpathy describes: ingest raw sources, compile an LLM-maintained wiki, query it, lint it, and let your explorations compound over time. It runs locally, requires zero API keys, and works as a Claude Code skill or standalone CLI.

| Karpathy's pattern | Librarian |
|---|---|
| Index source documents into `raw/` | `/library add` -- PDFs, URLs, arXiv, HN, RSS, GitHub, Twitter |
| LLM compiles a wiki of `.md` files | `/library compile` -- synthesized articles with cross-references |
| Q&A against the wiki | `/library search` -- hybrid retrieval with citations |
| Linting / health checks | `/library lint` -- broken links, stale sources, orphan articles |
| Filing outputs back into the wiki | Wiki auto-indexed; searches compound over time |
| Viewable in Obsidian | Wiki is plain `.md` files -- works in Obsidian, VS Code, or any editor |

**Coming soon:** [Personal agent memory](#personal-agent-memory) -- session learnings, project context, and associative recall. Two knowledge types (research + memory), one tool.

Pair it with [Context7](https://github.com/upstash/context7) for official SDK/framework docs, and Librarian for everything else -- your books, papers, notes, and curated web sources.

## Quick start

```bash
pip install -e .
/library init
```

### Index a book you own

```bash
/library add ~/Books/designing-data-intensive-applications.pdf
/library search "how does consistent hashing work"
```

Works with `.pdf`, `.md`, and `.txt` files — single files or entire directories. Adding a source automatically indexes it.

### Index a URL

```bash
/library add https://docs.anthropic.com/en/docs/build-with-claude/tool-use
/library search "tool use streaming"
```

Fetches the page, converts HTML to markdown, indexes, and caches locally. Use `/library refresh` when docs drift.

### Scout for new content

Install a starter watchlist and check what's new:

```bash
/library watch shelf install ai
/library watch shelf install biomedical
/library watch check
```

Librarian scouts Hacker News, arXiv, PubMed, RSS feeds, and GitHub — then presents candidates you can add to your library.

## Examples

### Track finance topics across the web

```bash
/library watch create "Quant finance" \
    --topic "quantitative trading" --topic "portfolio optimization" \
    --channel hn:min_points=50 \
    --channel "rss:https://blog.quantopian.com/feed" \
    --channel github:min_stars=20

/library watch check "Quant finance"
```

See something interesting? Add it:

```bash
/library add https://arxiv.org/abs/2401.12345
```

### Index a book from your local drive

```bash
/library add ~/Books/designing-data-intensive-applications.pdf

# Now search across everything — books, docs, and web sources together
/library search "leader election in distributed systems"
```

Any `.pdf`, `.md`, or `.txt` file works. Point at a directory to index everything inside it:

```bash
/library add ~/notes/architecture/
```

## Creating a watchlist

Define what you care about (topics) and where to look (channels):

```bash
/library watch create "Cell therapy" \
    --topic "CAR-T" --topic "CRISPR" --topic "gene editing" \
    --channel pubmed \
    --channel "rss:https://www.nature.com/subjects/gene-therapy.rss"
```

### Supported channels

| Channel | Source | Filtering |
|---------|--------|-----------|
| `hn` | Hacker News (Algolia API) | Server-side keyword + min points |
| `arxiv` | arXiv (Atom API) | Server-side keyword + categories |
| `pubmed` | PubMed (E-utilities) | Server-side keyword + date range |
| `rss` | Any RSS/Atom feed | Client-side topic matching |
| `github` | GitHub Search API | Server-side keyword + min stars |
| `twitter` | Twitter/X (syndication API + Playwright) | Known tweet IDs + timeline discovery |

### Channel argument formats

| Argument | Example |
|----------|---------|
| `hn` | Default settings |
| `hn:min_points=100` | Only high-signal stories |
| `arxiv:cs.AI,cs.LG` | Filter by arXiv categories |
| `rss:https://example.com/feed` | Any RSS or Atom feed (including Substack) |
| `github:min_stars=50` | Repos above a star threshold |
| `pubmed` | Default settings |
| `twitter` | Fetch specific tweets by ID (no auth) |
| `twitter:accounts=bcherny,karpathy` | Discover tweets from timelines (requires auth) |

#### Twitter setup

Tweet fetching by ID works out of the box via the syndication API (no auth). Timeline discovery requires a one-time Playwright login:

```bash
pip install 'librarian[twitter]'
playwright install chromium
python scripts/twitter_login.py   # opens Edge, log in once, profile is saved
```

### Managing entries

```bash
/library watch list                  # list all entries
/library watch check                 # scout all entries
/library watch check "Cell therapy"  # scout one entry
/library watch remove "Cell therapy" # remove an entry
```

### Starter shelves

Pre-built watchlists you can install in one command:

```bash
/library watch shelf list                # see what's available
/library watch shelf install ai              # AI/ML: HN + arXiv + GitHub
/library watch shelf install ai-engineering  # agentic coding: HN + arXiv + GitHub + Twitter
/library watch shelf install biomedical      # cell & gene therapy: PubMed
```

## Compile a wiki from your sources

Once you've indexed a few sources on a topic, compile them into a wiki — authored concept articles that synthesize knowledge across sources with cross-references.

```bash
/library compile "distributed systems"
/library compile "distributed systems" --query "consensus protocols"
```

The LLM gathers relevant chunks from your index, identifies distinct concepts, and writes wiki articles to `~/.claude/library-skill/wiki/<topic>/`. The wiki is automatically indexed back into the library, so future searches return both raw source chunks and synthesized wiki articles. Your explorations compound.

Wiki structure:
```
~/.claude/library-skill/wiki/
├── _index.md
└── distributed-systems/
    ├── _index.md
    ├── consensus-protocols.md
    ├── replication.md
    └── partitioning.md
```

Run compile again on the same topic to update existing articles with new material — it won't recreate from scratch.

## Health checks

Run structural health checks across your library and wiki:

```bash
/library lint                  # check everything
/library lint --scope wiki     # wiki only
/library lint --scope sources  # sources only
```

Catches: broken wiki links, orphan articles, stale URL sources, unindexed sources, and cross-reference issues. Each finding includes a suggested fix command.

## All commands

```bash
/library init                        # interactive setup for this machine
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
/library compile <topic>             # compile wiki from indexed material
/library lint                        # run health checks
```

## Architecture

```
watchlist entry → channels → dedup → candidates (JSON)
                                         ↓ (user approves)
                               /library add <url> → index
                                                      ↓
                               /library compile → wiki articles
                                         ↑               ↓
                                    (compounding)   /library add wiki/
                                         ↑               ↓
                                    /library search ← ← index
```

- **Embeddings:** `fastembed` with `BAAI/bge-small-en-v1.5` (ONNX, no PyTorch)
- **Vector DB:** `LanceDB` (embedded, zero-server)
- **PDF extraction:** `PyMuPDF`
- **Feed parsing:** `feedparser`

All runtime data stored locally at `~/.claude/library-skill/`:
```
~/.claude/library-skill/
├── config.yaml          # sources, watchlist, settings
├── index/               # LanceDB vector index (local, not synced)
├── cache/sources/       # fetched URL content
└── wiki/                # compiled wiki articles (default, configurable)
```

## Cross-device wiki sync

The wiki is just `.md` files — safe to sync via any cloud folder. Point `wiki_dir` in your config to a shared location:

```yaml
# ~/.claude/library-skill/config.yaml

# macOS
wiki_dir: ~/Library/CloudStorage/OneDrive-Microsoft/000-ai/wiki

# Windows
wiki_dir: ~/OneDrive - Microsoft/000-ai/wiki
```

The vector index stays local (LanceDB binary files don't sync safely). Each machine rebuilds its own index. After syncing to a new machine:

```bash
# Wiki .md files are already there via OneDrive
# Reindex locally so /library search finds them
/library add ~/Library/CloudStorage/OneDrive-Microsoft/000-ai/wiki
```

## Personal agent memory

*Planned -- merging capabilities from [memvec](https://github.com/ktundwal/memvec).*

Librarian currently handles **external knowledge** (books, papers, docs, web). The next major addition is **personal knowledge** -- the things your coding agent learns about you, your projects, and your preferences across sessions.

Two knowledge types, one unified search:

| | Research (current) | Memory (planned) |
|---|---|---|
| **Source** | Books, papers, URLs, web scouts | Session learnings, feedback, project context |
| **Written by** | You (add) + LLM (compile) | LLM (auto-memory from sessions) |
| **Lifecycle** | Mostly static, periodic refresh | Evolves every session |
| **Example query** | "consensus protocols in distributed systems" | "what did I learn about auth in the Teams codebase?" |

Planned memory commands:

```bash
/library remember "Teams uses OBO auth for Cortex APIs"  # explicit memory
/library recall "auth patterns in this project"           # associative recall
/library memory lint                                      # find stale/conflicting memories
```

The key differentiator: **associative recall** -- "what else should I remember?" When you ask about auth, it surfaces related memories about token refresh, service principals, and that one debugging session where OBO scopes were wrong. Not just keyword matching, but semantic connection.

Cross-device sync works the same way as wiki sync -- memory is `.md` files in a configurable directory, safe to sync via OneDrive/Dropbox/iCloud. Vector index stays local.

## MCP server

*Planned.*

Librarian currently runs as a Claude Code skill (slash commands). An MCP server mode will expose the same capabilities to any MCP-compatible client -- Cursor, Windsurf, custom agents, or CI pipelines.

```json
{
  "mcpServers": {
    "librarian": {
      "command": "librarian",
      "args": ["serve", "--mcp"]
    }
  }
}
```

This means your knowledge base becomes a shared resource across tools. Index once, query from anywhere.

## Roadmap

- **Personal agent memory** -- session learnings, associative recall, cross-device sync (see [above](#personal-agent-memory))
- **MCP server mode** -- cross-client interoperability (see [above](#mcp-server))
- **Tweet thread expansion** -- follow `in_reply_to` chain to index full threads, not just single tweets
- **Watch bulk add** -- `watch add-all` or `watch add --channel hn` to index discovered candidates without manual per-URL adds
- **HN discussion indexing** -- fetch comment threads from `news.ycombinator.com/item?id=X`, not just the linked article (community discussion is often the value)
- **Better source naming** -- use page title or `@author: first words` for tweet sources instead of generic domain
- **Semantic topic matching** -- embedding-based, replacing substring search
- **Quality ranking** -- dismiss list for seen candidates
- **PubMed abstract fetching** -- currently title-only summaries
- **Hybrid retrieval** -- lexical + semantic with reranking

## Make it your own

The `Channel` protocol makes it straightforward to add new sources. Each channel implements one method:

```python
def fetch_candidates(self, topics: list[str], since: str | None, **kwargs) -> list[Candidate]: ...
```

To add a channel (e.g., Reddit, Dev.to, YouTube):

1. Create `scripts/lib/channels/your_channel.py`
2. Implement `fetch_candidates` — hit a public API, return `Candidate` objects
3. Decorate your class with `@register_channel("your_channel")`
4. That's it — it's immediately usable in `--channel your_channel`

See any of the existing channels (`hn.py`, `rss.py`, etc.) for a working example in under 60 lines.

## Privacy & content policy

- Local processing by default — no external vector service
- No source corpus shipped in this repo
- Watchlist channels query public APIs only (no API keys required)
- Users are responsible for adding legally obtained source materials

## License

MIT
