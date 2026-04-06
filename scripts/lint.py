#!/usr/bin/env python3
"""Health checks across wiki articles and library sources."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from lib import config as _config
from lib.config import compute_freshness, load_config
from lib.indexer import get_table_stats

# Matches [[article-name]] or [[topic/article-name]] wiki-style links
_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _lint_wiki() -> list[dict]:
    """Check wiki directory for structural issues."""
    findings: list[dict] = []

    if not _config.WIKI_DIR.exists():
        findings.append({
            "category": "wiki",
            "severity": "info",
            "message": "No wiki directory exists yet. Run /library compile to create one.",
        })
        return findings

    # Collect all wiki articles and cache their content (single read pass)
    all_articles: dict[str, Path] = {}
    article_contents: dict[str, str] = {}
    for md_file in _config.WIKI_DIR.rglob("*.md"):
        rel = md_file.relative_to(_config.WIKI_DIR)
        key = str(rel.with_suffix(""))
        all_articles[key] = md_file
        article_contents[key] = md_file.read_text(encoding="utf-8", errors="replace")

    if not all_articles:
        findings.append({
            "category": "wiki",
            "severity": "info",
            "message": "Wiki directory is empty.",
        })
        return findings

    # Check for topic dirs without _index.md
    for topic_dir in sorted(_config.WIKI_DIR.iterdir()):
        if topic_dir.is_dir():
            index_path = topic_dir / "_index.md"
            if not index_path.exists():
                findings.append({
                    "category": "wiki",
                    "severity": "warning",
                    "message": f"Topic '{topic_dir.name}' has no _index.md",
                    "fix": f"Run /library compile {topic_dir.name} to generate one.",
                })

    # Check for broken wiki links (using cached content)
    for key, content in article_contents.items():
        for match in _WIKI_LINK_RE.finditer(content):
            link_target = match.group(1).strip()
            # Resolve relative to article's topic dir
            topic = str(Path(key).parent) if "/" in key else ""
            candidates = [
                link_target,
                f"{topic}/{link_target}" if topic else link_target,
            ]
            if not any(c in all_articles for c in candidates):
                findings.append({
                    "category": "wiki",
                    "severity": "warning",
                    "message": f"Broken link [[{link_target}]] in {key}.md",
                    "fix": "Create the article or remove the link.",
                })

    # Check for orphan articles (not linked from any _index.md)
    index_contents = "\n".join(
        content for key, content in article_contents.items()
        if all_articles[key].name == "_index.md"
    )

    for key, path in all_articles.items():
        if path.name == "_index.md":
            continue
        article_name = path.stem
        if article_name not in index_contents:
            findings.append({
                "category": "wiki",
                "severity": "info",
                "message": f"Orphan article: {key}.md (not referenced in any _index.md)",
                "fix": "Add it to the topic index or delete if outdated.",
            })

    return findings


def _lint_sources(config: dict[str, Any]) -> list[dict]:
    """Check library sources for health issues."""
    findings: list[dict] = []
    sources = config.get("sources", [])

    if not sources:
        findings.append({
            "category": "sources",
            "severity": "info",
            "message": "No sources registered.",
        })
        return findings

    stats = get_table_stats()
    indexed_source_ids = set(stats.get("sources", {}).keys())

    for source in sources:
        sid = source["source_id"]
        name = source["name"]

        # Unindexed sources
        if not source.get("indexed_at"):
            findings.append({
                "category": "sources",
                "severity": "warning",
                "message": f"Source '{name}' has never been indexed.",
                "fix": f"/library reindex {name}",
            })
            continue

        # Source in config but missing from index
        if sid not in indexed_source_ids:
            findings.append({
                "category": "sources",
                "severity": "warning",
                "message": f"Source '{name}' is registered but has no chunks in the index.",
                "fix": f"/library reindex {name}",
            })

        # Stale URL sources
        freshness = compute_freshness(source)
        if freshness == "stale":
            findings.append({
                "category": "sources",
                "severity": "warning",
                "message": f"Source '{name}' is stale (last refreshed: {source.get('refreshed_at', 'unknown')}).",
                "fix": f"/library refresh {name}",
            })
        elif freshness == "never_fetched":
            findings.append({
                "category": "sources",
                "severity": "warning",
                "message": f"URL source '{name}' has never been fetched.",
                "fix": f"/library refresh {name}",
            })

        # Empty sources (indexed but 0 chunks)
        source_stats = stats.get("sources", {}).get(sid, {})
        if source_stats.get("chunks", 0) == 0 and sid in indexed_source_ids:
            findings.append({
                "category": "sources",
                "severity": "info",
                "message": f"Source '{name}' has 0 chunks after indexing.",
            })

    return findings


def _lint_cross_references(config: dict[str, Any]) -> list[dict]:
    """Check wiki articles reference sources that still exist."""
    findings: list[dict] = []

    if not _config.WIKI_DIR.exists():
        return findings

    source_names = {s["name"] for s in config.get("sources", [])}

    for md_file in _config.WIKI_DIR.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for line in content.split("\n"):
            if line.strip().startswith("Source:") or line.strip().startswith("*Source:"):
                ref = line.split(":", 1)[1].strip().strip("*").strip()
                if ref and ref not in source_names and not ref.startswith("http"):
                    rel = md_file.relative_to(_config.WIKI_DIR)
                    findings.append({
                        "category": "cross-ref",
                        "severity": "warning",
                        "message": f"Wiki article '{rel}' references unknown source '{ref}'.",
                        "fix": "Update the article or re-add the source.",
                    })

    return findings


def main():
    parser = argparse.ArgumentParser(description="Library health checks")
    parser.add_argument(
        "--scope",
        choices=["wiki", "sources", "all"],
        default="all",
        help="What to check (default: all)",
    )
    args = parser.parse_args()

    config = load_config()
    findings: list[dict] = []

    if args.scope in ("wiki", "all"):
        findings.extend(_lint_wiki())

    if args.scope in ("sources", "all"):
        findings.extend(_lint_sources(config))

    if args.scope in ("all",):
        findings.extend(_lint_cross_references(config))

    # Summary counts
    severity_counts = {"warning": 0, "info": 0}
    for f in findings:
        severity_counts[f["severity"]] = severity_counts.get(f["severity"], 0) + 1

    print(json.dumps({
        "status": "ok",
        "total_findings": len(findings),
        "summary": severity_counts,
        "findings": findings,
    }, indent=2))


if __name__ == "__main__":
    main()
