# library-skill — Dev Conventions

## Project
Local-first personal knowledge layer for coding agents. Indexes docs/books/papers and provides grounded retrieval via `/library` commands.

## Tech Stack
- Python 3.10+
- fastembed (ONNX, no PyTorch) for embeddings
- LanceDB (embedded, zero-server) for vector storage
- PyMuPDF for PDF extraction
- PyYAML for config

## Structure
- `scripts/lib/` — shared modules (config, chunker, embedder, indexer, retriever, sources)
- `scripts/*.py` — CLI entry points (argparse + JSON stdout)
- `commands/library.md` — slash command definition
- `skills/library-knowledge/SKILL.md` — proactive skill

## Conventions
- All scripts output JSON to stdout; errors go to stderr
- User data lives at `~/.claude/library-skill/` — never in the repo
- Embedding model: `BAAI/bge-small-en-v1.5` via fastembed
- Default chunk size: 512 tokens
- Default top_k: 5

## Running
```bash
pip install -e .
python3 scripts/add.py <path-or-url>
python3 scripts/reindex.py
python3 scripts/search.py "query"
python3 scripts/status.py
```
