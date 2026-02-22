# /library — Personal Knowledge Layer for Coding Agents

## 1) Problem

Technical books, peer-reviewed papers, and official docs are high-value coding references, but they are rarely consulted during active implementation. Coding agents therefore miss established design principles, use weak patterns, or rely on stale API knowledge.

**Observed gap examples**
- "Clean Code" principles are not applied unless explicitly prompted.
- arXiv methods are unavailable unless manually surfaced.
- Fast-moving SDK docs (Anthropic/OpenAI/etc.) drift, causing outdated usage.
- Book/paper guidance without current docs grounding can send the agent in the wrong direction.

## 2) Vision

`/library` is a local-first Claude Code skill that indexes the user’s personal references (books, papers, docs) and returns grounded excerpts during coding.

It also proactively recommends which references from the library should be brought into the current workspace context after the user adds/enables skills.

All processing is local. No source content is uploaded.

## 3) Product Outcomes

### Primary outcomes
- Improve coding-agent output quality via trusted grounding.
- Reduce user effort by recommending relevant references automatically when skills are added.

### Success metrics (v1)
- **Retrieval quality:** Top-5 includes at least one clearly relevant chunk for >= 80% of benchmark queries.
- **Attribution quality:** 100% of returned results include source, section, and timestamp metadata.
- **Latency:** P95 search latency <= 1.5s on typical laptop corpus (up to ~50k chunks).
- **Freshness:** configured docs sources can be refreshed and stale state is visible.
- **Recommendation utility:** skill-triggered suggestions are presented with reason + accept/modify controls.

## 4) Scope & Non-Goals

### In-scope (v1)
- Local books: `md`, `txt`, `pdf`
- Official docs: user-configured URL sources
- Papers: optional, explicit arXiv IDs
- Search + recommendation workflows with citations and freshness

### Non-goals (v1)
- Cloud sync/team sharing
- OCR-heavy scanned PDFs as primary path
- Broad autonomous crawling outside configured docs roots
- Rich GUI beyond command-based interaction

## 5) Source Types

| Source | Example | Acquisition | Freshness |
|---|---|---|---|
| **Books** | Clean Code, DDIA, Pragmatic Programmer | Local files/folders | Mostly static |
| **Papers** | arXiv IDs | arXiv API | Static after fetch |
| **Official docs** | Anthropic, OpenAI, Microsoft, Google | Configured URLs | Periodic refresh |

Official docs are the **grounding layer** so principles from books/papers are paired with current APIs and idioms.

## 6) Commands (v1)

- `/library add <path-or-url>`
  - Register local source(s) or docs source URL.
- `/library reindex [source-name|all]`
  - Convert, chunk, embed, and index.
- `/library search <query> [--top-k N] [--source books|docs|papers]`
  - Hybrid retrieval + rerank + cited excerpts.
- `/library refresh [source-name|all]`
  - Refresh docs and update freshness state.
- `/library status`
  - Show source health: chunks, last indexed, freshness.
- `/library eval`
  - Run retrieval/latency benchmark harness.

## 7) Skill-Triggered Recommendation Workflow

### Trigger
- User adds or enables skills in the workspace.

### Behavior
1. `/library` maps skill signals to candidate references in its index.
2. Returns a shortlist with rationale and freshness.
3. User chooses one action:
   - **Accept all**
   - **Modify** selection (remove/add suggestions)
   - **Skip**
4. Accepted references are marked active for the workspace session and prioritized in subsequent retrieval.

### Recommendation response contract
- source title
- source type
- relevance reason (skill-to-reference mapping)
- freshness (`fresh|stale|unknown`)
- suggested action (`accept|modify|skip`)

## 8) System Design

### 8.1 Conversion & ingestion
All sources normalized to Markdown for uniform processing.

| Format | Approach |
|---|---|
| PDF | `pymupdf` or `pdfplumber` |
| ePub | deferred from v1 |
| HTML docs | `beautifulsoup` + `markdownify` |
| Markdown/text | direct |

Pipeline:
1. Read source
2. Convert/normalize markdown
3. Parse section hierarchy
4. Chunk by semantic boundaries + token budget
5. Embed chunks
6. Store text + metadata + vectors

### 8.2 Retrieval
1. Normalize query
2. Run hybrid candidate generation:
   - lexical (BM25/FTS)
   - semantic (vector similarity)
3. Merge and deduplicate
4. Rerank top-N
5. Return top-K with attribution + freshness + match reason

Low-confidence behavior:
- return fewer results and explicitly mark low confidence.

### 8.3 Storage model
Prefer one global index + source filters for simpler cross-corpus ranking.

```
~/.claude/library-skill/
  config.yaml
  cache/
    sources/<source-id>/source.md
  index/
    library.db
```

## 9) Metadata Contract (required per chunk)

- `chunk_id`
- `source_id`
- `source_type` (`book|docs|paper`)
- `title`
- `section_path`
- `origin` (path or URL)
- `fetched_at` (remote only)
- `indexed_at`
- `content_hash`
- `license_or_terms_note`

## 10) Search Response Contract

Each result includes:
- rank/score
- short excerpt (2-6 lines)
- attribution (title + section + origin)
- freshness (`fresh|stale|unknown`)
- match explanation (keyword/semantic/rerank signal)

## 11) Freshness & Sync Rules

- Use conditional HTTP (`ETag`, `Last-Modified`) when available.
- Fall back to `refresh_days` policy when not available.
- Mark source stale when overdue or repeated refresh failures occur.
- Keep last successful snapshot to avoid index loss during transient failures.

## 12) Configuration (example)

```yaml
# ~/.claude/library-skill/config.yaml
libraries:
  - path: /path/to/books
    formats: [pdf, md, txt]

docs:
  - name: anthropic
    url: https://docs.anthropic.com
    refresh_days: 7

embedding_model: all-MiniLM-L6-v2
chunk_size: 512
top_k: 5
recommendations:
  enable_on_skill_add: true
  default_action: prompt
```

## 13) Evaluation Harness

Benchmark file: `bench/queries.yaml`
- representative coding queries
- expected source family and/or anchors

`/library eval` reports:
- recall@k proxy
- attribution completeness
- latency percentiles

## 14) Delivery Milestones (no timeline)

### Milestone 1: Core Search Path
- config + source registration
- markdown ingestion (`md/txt/pdf`)
- chunking/embedding/index
- basic `/library search` with citations

**Exit criteria**
- end-to-end indexing + search on multiple local sources
- citations always present

### Milestone 2: Quality + Freshness
- hybrid retrieval + reranking
- docs refresh + stale state
- `/library status` + `/library refresh`

**Exit criteria**
- retrieval quality threshold met
- freshness state visible and accurate

### Milestone 3: Hardening + Recommendations
- incremental reindex + retry/error handling
- optional arXiv fetch path
- skill-triggered recommendation flow with accept/modify/skip
- evaluation/reporting polish

**Exit criteria**
- stable refresh/reindex cycles
- recommendations usable and actionable

## 15) Acceptance Criteria (v1)

1. `/library add` + `/library reindex` yields searchable indexed chunks.
2. `/library search` returns top-k with complete attribution metadata.
3. Docs freshness is surfaced and changes after `/library refresh`.
4. Source content never leaves local machine during ingest/search.
5. Low-confidence search output is explicitly flagged.
6. `/library eval` reports retrieval + latency metrics.
7. After skills are added, `/library` recommends references with reasons and freshness.
8. User can accept all, modify, or skip before references become active in workspace context.

## 16) Privacy, Security, Copyright

- Local-only processing by default.
- No telemetry by default.
- Cache/index paths excluded from git by default.
- Users provide legally obtained books.
- Open-source repo contains code only, not copyrighted source content.
- Source-level terms notes supported in config.

## 17) Risks & Mitigations

- **Weak relevance on API identifiers** → hybrid retrieval + rerank + token-aware query handling.
- **Docs structure changes** → per-site adapters + fallback snapshot retention.
- **Laptop performance constraints** → incremental indexing + embedding cache + configurable candidate depth.
- **Compliance ambiguity** → per-source allow/deny + terms notes.

## 18) Example Success Case

User query:

```
/library search "consistency guarantees in distributed databases"
```

Returned grounding includes:
1. DDIA sections on linearizability/eventual consistency
2. relevant arXiv CRDT paper previously fetched
3. current official docs snippets for the target SDK/API

User adds a new distributed-systems skill; `/library` then recommends related references from its indexed corpus, and the user accepts/modifies before those references are prioritized for this workspace.
