"""Channel abstraction for watchlist scouting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Candidate — a single discovery result from a channel
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    url: str
    title: str
    source_channel: str  # "hn" | "arxiv" | "pubmed" | "rss" | "github"
    published: str | None  # ISO 8601
    summary: str
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Flatten for JSON output (extra fields merged at top level)."""
        d = {
            "url": self.url,
            "title": self.title,
            "source_channel": self.source_channel,
            "published": self.published,
            "summary": self.summary,
        }
        d.update(self.extra)
        return d


# ---------------------------------------------------------------------------
# Channel protocol
# ---------------------------------------------------------------------------

class Channel(Protocol):
    def fetch_candidates(
        self,
        topics: list[str],
        since: str | None,
        **kwargs: Any,
    ) -> list[Candidate]: ...


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_CHANNELS: dict[str, type] = {}


def register_channel(name: str):
    """Decorator to register a channel class."""
    def wrapper(cls: type) -> type:
        _CHANNELS[name] = cls
        return cls
    return wrapper


def get_channel(type_str: str) -> Channel:
    """Instantiate a channel by type name."""
    if type_str not in _CHANNELS:
        # Trigger import of channel modules to populate the registry
        _import_channels()
    if type_str not in _CHANNELS:
        raise ValueError(f"Unknown channel type: {type_str}")
    return _CHANNELS[type_str]()


def _import_channels() -> None:
    """Import all channel modules to trigger @register_channel decorators."""
    from lib.channels import hn, arxiv, pubmed, rss, github, twitter  # noqa: F401
