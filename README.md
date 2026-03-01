# Librarian

A local-first research scout for coding agents.

**Zero API keys required.** Librarian indexes your docs, books, and papers for grounded retrieval — and scouts the web for new content matching your interests.

Pair it with [Context7](https://github.com/upstash/context7) for official SDK/framework docs, and Librarian for everything else — your books, papers, notes, and curated web sources.

## Quick start

```bash
pip install -e .
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

## Future enhancements

- **Tweet thread expansion** — follow `in_reply_to` chain to index full threads, not just single tweets
- **Watch → bulk add** — `watch add-all` or `watch add --channel hn` to index discovered candidates without manual per-URL adds
- **HN discussion indexing** — fetch comment threads from `news.ycombinator.com/item?id=X`, not just the linked article (community discussion is often the value)
- **Better source naming** — use page title or `@author: first words` for tweet sources instead of generic domain
- MCP server mode for cross-client interoperability
- Semantic topic matching (embedding-based, replacing substring search)
- Quality ranking and dismiss list for seen candidates
- PubMed abstract fetching (currently title-only summaries)
- Hybrid retrieval (lexical + semantic) with reranking

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
