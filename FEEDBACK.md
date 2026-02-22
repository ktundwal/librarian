# library-skill — Implementation Feedback for Opus

## 1) What this project is trying to accomplish

`library-skill` is building a **local-first retrieval layer for coding agents**:
- index personal technical references (books, docs, papers)
- retrieve grounded excerpts during coding
- preserve privacy by keeping processing and storage local

Primary user surface is `/library` with subcommands: `add`, `reindex`, `search`, `status`, `refresh`.

---

## 2) How it works today (actual implementation)

### End-to-end flow (M1 core path)
1. `add` registers a source in config (`file`, `directory`, or `url`).
2. `reindex` collects local `.md/.txt/.pdf`, reads/normalizes text, chunks markdown by headings/paragraphs.
3. Chunks are embedded with `fastembed` (`BAAI/bge-small-en-v1.5`).
4. Vectors + metadata are stored in LanceDB table `library`.
5. `search` runs vector similarity and returns top-k with attribution metadata.
6. `status` reports source + index stats.

### Storage model
- Runtime data under `~/.claude/library-skill/`
  - `config.yaml`
  - `index/` (LanceDB)
  - `cache/sources/`

### Current metadata in index
- `chunk_id`, `source_id`, `source_name`, `source_kind`, `origin`, `section_path`, `content`, `content_hash`, `indexed_at`

### Current known limitation
- `refresh` for URL sources is intentionally stubbed (URLs register but are not fetched/indexed).

---

## 3) What is strong

- Good MVP architecture split (`config`, `sources`, `chunker`, `embedder`, `indexer`, `retriever`).
- Local/privacy-first design is coherent and correctly reflected in runtime paths.
- JSON contract for scripts is clear and consistent.
- Attribution fields are present in retrieval output.
- Uses practical stack for local execution (fastembed + LanceDB + PyMuPDF).

---

## 4) Gaps and risks (vision vs implementation)

## 4.1 Missing vs stated roadmap
Planned in docs/idea but not implemented yet:
- URL refresh/fetch pipeline
- freshness model (`fresh|stale|unknown`)
- hybrid retrieval (lexical + semantic)
- reranking and low-confidence signaling
- recommendation workflow tied to skills
- eval harness (`/library eval`)

## 4.2 Packaging/distribution gap
- `pyproject.toml` currently has `packages = []` and no console entry points.
- Usable as script calls, but not as a packaged CLI surface.

## 4.3 Robustness/quality gaps
- No automated tests.
- Config loading does not deep-merge defaults; malformed/partial configs can break assumptions.
- Chunker paragraph splitting can still exceed token budget if one paragraph is very large.
- `search` returns LanceDB `_distance` as `score` (not normalized relevance), which can be misinterpreted.

---

## 5) Prioritized implementation plan (for Opus)

## P0 — Hardening current MVP (before feature expansion)
1. **Add tests for core contracts**
   - unit tests: `sources.detect/build/collect`, `chunker.chunk_markdown`, `retriever.search` formatting
   - regression tests for edge files and empty index behavior
2. **Config safety improvements**
   - validate required keys/types
   - merge defaults with existing config on load
   - surface user-friendly errors to stderr
3. **Chunking correctness improvements**
   - enforce hard max-size fallback when a single paragraph exceeds budget (sentence/line fallback)
   - preserve section path attribution after fallback splits
4. **Score semantics cleanup**
   - rename output field to `distance` or convert to explicit relevance score
   - document sorting/interpretation in README and command docs

### P0 acceptance criteria
- Test suite exists and passes locally.
- Reindex/search works on mixed `.md/.txt/.pdf` corpus without chunk overflow regressions.
- Search output clearly communicates metric semantics.

---

## P1 — Close largest product gap: URL sources + freshness
1. **Implement URL fetch/cache pipeline**
   - fetch URL content into `cache/sources/<source-id>/`
   - convert HTML to markdown and pass through existing chunk/index path
2. **Add refresh behavior**
   - `refresh [source-name]` actually updates URL sources
   - detect unchanged content to avoid unnecessary reindex
3. **Freshness model in config/status/search**
   - fields: `fetched_at`, `last_successful_refresh_at`, `refresh_days`, derived `freshness`
   - `status` reports freshness per source

### P1 acceptance criteria
- URL source can be added, fetched, indexed, and queried.
- Refresh updates freshness state and timestamps.
- Unchanged URLs avoid full re-embedding/reindex where possible.

---

## P2 — Retrieval quality upgrades
1. **Hybrid retrieval**
   - add lexical retrieval (BM25/FTS) candidate set
   - merge + dedupe with vector candidates
2. **Reranking**
   - rerank top-N merged candidates for final top-k
3. **Low-confidence behavior**
   - confidence thresholding
   - explicit low-confidence flag in output

### P2 acceptance criteria
- Better relevance on identifier-heavy/API queries.
- Search output includes confidence signaling.

---

## P3 — Productization + evaluation
1. **Evaluation harness (`/library eval`)**
   - benchmark query set
   - report retrieval quality proxy + latency metrics
2. **Packaging improvements**
   - proper package discovery and console scripts
3. **Recommendation workflow (optional after quality baseline)**
   - skill-signal to source suggestions with rationale + user action model

### P3 acceptance criteria
- Repeatable eval command with persisted report.
- Tool install/use does not require direct script paths.

---

## 6) Concrete file-level guidance

### Likely files to touch first
- `scripts/lib/chunker.py`
- `scripts/lib/config.py`
- `scripts/lib/retriever.py`
- `scripts/refresh.py`
- `scripts/reindex.py`
- `scripts/lib/sources.py`
- `pyproject.toml`
- `README.md` and `commands/library.md` (contract updates)

### Suggested new files
- `tests/test_chunker.py`
- `tests/test_sources.py`
- `tests/test_retriever.py`
- `scripts/lib/fetcher.py` (URL retrieval + cache abstraction)
- optional: `scripts/eval.py` + `bench/queries.yaml`

---

## 7) Non-goals to preserve (avoid scope creep)

- Keep it local-first; no cloud dependency required for core workflow.
- Do not add GUI; keep command/script UX first.
- Do not broaden source crawling beyond explicitly configured origins.

---

## 8) Recommended implementation order (short)

1. P0 hardening + tests
2. P1 URL refresh/freshness
3. P2 hybrid retrieval + confidence
4. P3 eval + packaging + recommendations

This order reduces rework and creates a stable baseline before quality and product features.
