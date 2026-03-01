"""One-time interactive Twitter/X login for Playwright-based timeline scraping.

Opens a Chromium window for manual login. The browser profile is saved to
~/.claude/library-skill/twitter-profile/ and reused for headless scraping.

Usage:
    python scripts/twitter_login.py
"""

from lib.channels.twitter import twitter_login

if __name__ == "__main__":
    twitter_login()
