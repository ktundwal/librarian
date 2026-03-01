"""Twitter/X channel via syndication API + Playwright timeline scraping.

Tier 1 (syndication API): Fetches individual tweets by ID without authentication.
    Uses cdn.syndication.twimg.com with a computed token (same algorithm as
    Vercel's react-tweet package).

Tier 2 (Playwright): Discovers new tweets from user timelines using a persistent
    authenticated browser profile. Requires one-time interactive login via
    `python scripts/twitter_login.py`.
"""

from __future__ import annotations

import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from lib.channels import Candidate, register_channel
from lib.config import DATA_DIR

SYNDICATION_URL = "https://cdn.syndication.twimg.com/tweet-result"
TWITTER_PROFILE_DIR = DATA_DIR / "twitter-profile"

# Matches twitter.com or x.com status URLs
TWEET_URL_RE = re.compile(
    r"https?://(?:twitter\.com|x\.com)/(?P<user>[^/]+)/status/(?P<id>\d+)"
)


# ---------------------------------------------------------------------------
# Tier 1: Syndication API (no auth required)
# ---------------------------------------------------------------------------

def _float_to_base36(num: float) -> str:
    """Convert a float to base-36 string, matching JS Number.toString(36)."""
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"

    if num < 0:
        return "-" + _float_to_base36(-num)

    int_part = int(num)
    frac_part = num - int_part

    # Integer part
    if int_part == 0:
        result = "0"
    else:
        result = ""
        n = int_part
        while n:
            result = chars[n % 36] + result
            n //= 36

    # Fractional part (12 digits matches JS precision)
    if frac_part > 1e-10:
        result += "."
        for _ in range(12):
            frac_part *= 36
            digit = int(frac_part)
            result += chars[digit]
            frac_part -= digit
            if frac_part < 1e-10:
                break

    return result


def _compute_token(tweet_id: str) -> str:
    """Compute syndication API token from tweet ID.

    Ports the algorithm from Vercel's react-tweet package:
    ((Number(id) / 1e15) * Math.PI).toString(36).replace(/(0+|\\.)/g, '')

    Source: https://github.com/vercel/react-tweet
    """
    # float() matches JS float64 precision (large IDs exceed MAX_SAFE_INTEGER)
    num = (float(tweet_id) / 1e15) * math.pi
    base36 = _float_to_base36(num)
    return re.sub(r"0+|\.", "", base36)


def fetch_tweet(tweet_id: str) -> dict[str, Any]:
    """Fetch a single tweet via the syndication API. Returns raw JSON."""
    token = _compute_token(tweet_id)
    resp = requests.get(
        SYNDICATION_URL,
        params={"id": tweet_id, "token": token},
        headers={"User-Agent": "library-skill/0.2"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def tweet_to_markdown(data: dict[str, Any]) -> str:
    """Convert syndication API tweet JSON to readable markdown."""
    user = data.get("user", {})
    author = user.get("screen_name", "unknown")
    name = user.get("name", author)
    text = data.get("text", "")
    created = data.get("created_at", "")
    tweet_id = data.get("id_str", "")

    lines = [
        f"# @{author} ({name})",
        f"*{created}*",
        "",
        text,
    ]

    # Media
    for i, photo in enumerate(data.get("photos", []), 1):
        alt = photo.get("alt_text", "")
        url = photo.get("url", "")
        if alt:
            lines.append(f"\n![Image {i}: {alt}]({url})")
        elif url:
            lines.append(f"\n![Image {i}]({url})")

    # Quoted tweet
    quoted = data.get("quoted_tweet")
    if quoted:
        q_author = quoted.get("user", {}).get("screen_name", "")
        q_text = quoted.get("text", "")
        lines.extend(["", f"> **@{q_author}**: {q_text}"])

    # Metrics
    likes = data.get("favorite_count", 0)
    retweets = data.get("retweet_count", 0)
    replies = data.get("reply_count", 0)
    lines.extend([
        "",
        "---",
        f"Likes: {likes} | Retweets: {retweets} | Replies: {replies}",
        f"https://x.com/{author}/status/{tweet_id}",
    ])

    return "\n".join(lines)


def fetch_tweet_as_markdown(tweet_id: str) -> str:
    """Fetch a tweet and return markdown representation."""
    data = fetch_tweet(tweet_id)
    return tweet_to_markdown(data)


# ---------------------------------------------------------------------------
# Tier 2: Playwright timeline scraping (requires auth)
# ---------------------------------------------------------------------------

def _scrape_timeline(account: str, max_tweets: int = 50) -> list[dict[str, Any]]:
    """Scrape recent tweets from a user's timeline using Playwright.

    Requires prior authentication via `python scripts/twitter_login.py`.
    Uses a persistent browser profile stored at TWITTER_PROFILE_DIR.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright required for timeline scraping.\n"
            "Install: pip install 'librarian[twitter]' && playwright install chromium"
        )

    if not TWITTER_PROFILE_DIR.exists():
        raise RuntimeError(
            "Twitter not authenticated. Run: python scripts/twitter_login.py"
        )

    tweets: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            str(TWITTER_PROFILE_DIR),
            headless=True,
            channel="msedge",
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        try:
            page.goto(f"https://x.com/{account}", wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            seen_ids: set[str] = set()
            for _ in range(5):
                articles = page.query_selector_all('article[data-testid="tweet"]')
                for article in articles:
                    link = article.query_selector('a[href*="/status/"]')
                    if not link:
                        continue
                    href = link.get_attribute("href") or ""
                    # Hrefs are relative (/user/status/123) or absolute
                    parts = href.split("/status/")
                    if len(parts) < 2:
                        continue
                    tid = parts[1].split("/")[0].split("?")[0]
                    if not tid.isdigit():
                        continue
                    if tid in seen_ids:
                        continue
                    seen_ids.add(tid)
                    tweet_author = parts[0].strip("/").split("/")[-1]

                    text_el = article.query_selector('[data-testid="tweetText"]')
                    text = text_el.inner_text() if text_el else ""

                    time_el = article.query_selector("time")
                    timestamp = time_el.get_attribute("datetime") if time_el else None

                    tweets.append({
                        "tweet_id": tid,
                        "author": tweet_author or account,
                        "text": text,
                        "published": timestamp,
                        "url": f"https://x.com/{account}/status/{tid}",
                    })

                    if len(tweets) >= max_tweets:
                        break

                if len(tweets) >= max_tweets:
                    break

                page.evaluate("window.scrollBy(0, 2000)")
                page.wait_for_timeout(2000)
        finally:
            browser.close()

    return tweets


def twitter_login() -> None:
    """Open Chromium for interactive Twitter login.

    Saves persistent browser profile for reuse in subsequent headless runs.
    Profile stored at: ~/.claude/library-skill/twitter-profile/
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright required.\n"
            "Install: pip install 'librarian[twitter]' && playwright install chromium"
        )

    TWITTER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            str(TWITTER_PROFILE_DIR),
            headless=False,
            channel="msedge",
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://x.com/login")

        print("Log in to Twitter/X in the browser window.", file=sys.stderr)
        print(
            "This window will close automatically once login is detected.",
            file=sys.stderr,
        )

        try:
            page.wait_for_url("**/home", timeout=300_000)  # 5 min
            print("Login successful. Browser profile saved.", file=sys.stderr)
        except Exception:
            print("Login timed out or was cancelled.", file=sys.stderr)
        finally:
            try:
                browser.close()
            except Exception:
                pass  # Browser may already be closed by user


# ---------------------------------------------------------------------------
# Channel registration
# ---------------------------------------------------------------------------

@register_channel("twitter")
class TwitterChannel:
    """Twitter/X channel combining syndication API and Playwright discovery."""

    def fetch_candidates(
        self,
        topics: list[str],
        since: str | None,
        **kwargs: Any,
    ) -> list[Candidate]:
        accounts: list[str] = kwargs.get("accounts", [])
        tweet_ids: list[str] = kwargs.get("tweet_ids", [])

        candidates: list[Candidate] = []

        # Tier 1: Fetch known tweet IDs via syndication API
        for tid in tweet_ids:
            try:
                data = fetch_tweet(tid)
                author = data.get("user", {}).get("screen_name", "unknown")
                text = data.get("text", "")
                candidates.append(Candidate(
                    url=f"https://x.com/{author}/status/{tid}",
                    title=_truncate(f"@{author}: {text}", 80),
                    source_channel="twitter",
                    published=data.get("created_at"),
                    summary=text[:200],
                    extra={
                        "tweet_id": tid,
                        "author": author,
                        "retweet_count": data.get("retweet_count", 0),
                        "like_count": data.get("favorite_count", 0),
                    },
                ))
            except Exception as exc:
                print(
                    f"Twitter syndication error for tweet {tid}: {exc}",
                    file=sys.stderr,
                )

        # Tier 2: Discover tweets from account timelines via Playwright
        for account in accounts:
            try:
                timeline_tweets = _scrape_timeline(account)
                topics_lower = [t.lower() for t in topics]
                for tweet in timeline_tweets:
                    text_lower = tweet["text"].lower()
                    if any(topic in text_lower for topic in topics_lower):
                        # Filter by since timestamp if provided
                        if since and tweet.get("published"):
                            try:
                                pub = datetime.fromisoformat(
                                    tweet["published"].replace("Z", "+00:00")
                                )
                                cutoff = datetime.fromisoformat(since)
                                if pub < cutoff:
                                    continue
                            except (ValueError, TypeError):
                                pass

                        candidates.append(Candidate(
                            url=tweet["url"],
                            title=_truncate(f"@{account}: {tweet['text']}", 80),
                            source_channel="twitter",
                            published=tweet.get("published"),
                            summary=tweet["text"][:200],
                            extra={
                                "tweet_id": tweet["tweet_id"],
                                "author": account,
                                "retweet_count": 0,
                                "like_count": 0,
                            },
                        ))
            except Exception as exc:
                print(
                    f"Twitter timeline error for @{account}: {exc}",
                    file=sys.stderr,
                )

        return candidates


def _truncate(text: str, length: int) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."
