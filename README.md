# /library

Local-first knowledge retrieval for coding agents.

`/library` turns your own technical references into grounded context an agent can use while coding—so outputs are less generic, more accurate, and easier to verify.

`library-skill` is the package/repo that powers the `/library` command.

## Why did I build this?

I curate my development references in neat folders. Think purchased books, my notes in MD format, arXiv papers I downloaded and annotated.

Now when I am coding I am constantly searching for them and copy pasting results. For instance Design data intensive application book has great explanations on distributed systems. Only last week I was working on a production system and I needed those concepts. I realized I am doing it many times over. Also, Fast-moving SDK docs (Anthropic/OpenAI/etc.) drift, causing outdated usage.

`/library` is the workflow I built for myself so the right context shows up when I need it.

- **Grounded answers from your own corpus** (`.md`, `.txt`, `.pdf`)
- **Fast local retrieval** with source attribution in every result
- **Privacy-first architecture** with no external vector service
- **Native Claude workflow** through the `/library` command

## Available now (v0.1)

- Add sources from file paths, directories, or URLs (URLs are registered for future refresh/index workflows)
- Reindex local `.md`, `.txt`, `.pdf` sources into chunks + embeddings
- Search by query with optional `--top-k` and `--source` filters
- Inspect index health and per-source status

## Quick start

```bash
/library add <path-or-url>
/library reindex [source-name]
/library search "<query>" [--top-k N] [--source book|docs|paper]
/library status
/library refresh
```

`/library refresh` is currently a Milestone 1 stub for remote docs sources.

## Architecture

- **Embeddings:** `fastembed` with `BAAI/bge-small-en-v1.5`
- **Vector DB:** `LanceDB` (embedded, no external service)
- **PDF extraction:** `PyMuPDF`
- **Config:** `PyYAML`

All runtime data is stored locally at `~/.claude/library-skill/` (config, cache, index).

## Implementation details

### Ingestion & chunking
- Source registration for files, directories, and URLs
- Local file ingestion for `.md`, `.txt`, `.pdf`
- PDF extraction via `PyMuPDF`
- Heading-aware chunking with token-budget splitting

### Retrieval path
- Semantic vector search in LanceDB
- Optional source filtering (`book|docs|paper`)
- Ranked top-k results with attribution fields

### Storage model
- Single global index table (`library`) with per-source filtering
- Source config and local index persisted under `~/.claude/library-skill/`

### Metadata currently stored per chunk
- `chunk_id`
- `source_id`
- `source_name`
- `source_kind`
- `origin`
- `section_path`
- `content`
- `content_hash`
- `indexed_at`

### Search response currently returns
- `rank`
- `score`
- `content`
- `source_name`
- `source_kind`
- `section_path`
- `origin`
- `indexed_at`
- `chunk_id`

## Roadmap

- Remote docs fetch for URL sources + real `/library refresh`
- Freshness state (`fresh|stale|unknown`) and sync policies
- Hybrid retrieval (lexical + semantic) and reranking
- Low-confidence result signaling
- Expanded metadata contract (`title`, `fetched_at`, `license_or_terms_note`)
- Evaluation harness for retrieval quality and latency (`/library eval`)
- Skill-triggered recommendation workflow

## Privacy & content policy

- Local processing by default
- No source corpus shipped in this repo
- Users are responsible for adding legally obtained source materials

## License

MIT
