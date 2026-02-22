"""Markdown-aware chunking with configurable token budget."""

import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    section_path: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return len(text) // 4


def chunk_markdown(
    text: str,
    max_tokens: int = 512,
    source_id: str = "",
    origin: str = "",
) -> list[Chunk]:
    """Split markdown into heading-aware chunks respecting token budget.

    Strategy:
    1. Split on headings (# through ####)
    2. Track heading hierarchy as section_path
    3. If a section exceeds max_tokens, split on paragraph boundaries
    """
    lines = text.split("\n")
    chunks: list[Chunk] = []
    heading_stack: list[str] = []
    current_lines: list[str] = []
    chunk_index = 0

    def flush(section_path: str) -> None:
        nonlocal chunk_index
        content = "\n".join(current_lines).strip()
        if not content:
            return
        # Split further if over budget
        sub_chunks = _split_by_paragraphs(content, max_tokens)
        for sub in sub_chunks:
            chunks.append(Chunk(
                text=sub,
                section_path=section_path,
                chunk_index=chunk_index,
                metadata={"source_id": source_id, "origin": origin},
            ))
            chunk_index += 1

    heading_re = re.compile(r"^(#{1,4})\s+(.+)$")

    for line in lines:
        m = heading_re.match(line)
        if m:
            # Flush current section
            section_path = " > ".join(heading_stack) if heading_stack else "(top)"
            flush(section_path)
            current_lines = []

            level = len(m.group(1))
            title = m.group(2).strip()

            # Maintain heading hierarchy
            while len(heading_stack) >= level:
                heading_stack.pop()
            heading_stack.append(title)

            current_lines.append(line)
        else:
            current_lines.append(line)

    # Flush remaining
    section_path = " > ".join(heading_stack) if heading_stack else "(top)"
    flush(section_path)

    return chunks


def _split_by_paragraphs(text: str, max_tokens: int) -> list[str]:
    """Split text into chunks at paragraph boundaries, respecting token budget."""
    if estimate_tokens(text) <= max_tokens:
        return [text]

    paragraphs = re.split(r"\n\s*\n", text)
    result: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)
        if current_tokens + para_tokens > max_tokens and current:
            result.append("\n\n".join(current))
            current = []
            current_tokens = 0
        current.append(para)
        current_tokens += para_tokens

    if current:
        result.append("\n\n".join(current))

    return result
