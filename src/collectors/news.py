from __future__ import annotations

import asyncio
import time
from calendar import timegm
from typing import Any

import feedparser

MAX_ARTICLES_PER_CATEGORY = 6

RSS_FEEDS: dict[str, list[str]] = {
    "headlines": [
        "https://www.abc.net.au/news/feed/2942460/rss.xml",
        "https://www.sbs.com.au/news/feed",
    ],
    "ai": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    ],
    "movies": [
        "https://collider.com/feed/",
        "https://screenrant.com/feed/",
    ],
    "tesla": [
        "https://electrek.co/feed/",
        "https://www.teslarati.com/feed/",
    ],
    "stremio": [
        "https://blog.stremio.com/feed/",
    ],
}


def _parse_feed(url: str) -> list[dict[str, Any]]:
    """Parse a single RSS feed and return normalised articles."""
    feed = feedparser.parse(url)
    source = feed.feed.get("title", url)
    articles: list[dict[str, Any]] = []
    for entry in feed.entries:
        published_ts: float | None = None
        if entry.published_parsed is not None:
            published_ts = float(timegm(entry.published_parsed))
        articles.append(
            {
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get("summary", ""),
                "source": source,
                "published_ts": published_ts,
            }
        )
    return articles


async def fetch_news() -> dict[str, list[dict[str, Any]]]:
    """Fetch and aggregate RSS feeds for all categories.

    Returns:
        Dict mapping category name to a list of article dicts,
        sorted newest-first and capped at MAX_ARTICLES_PER_CATEGORY.
    """
    loop = asyncio.get_running_loop()
    result: dict[str, list[dict[str, Any]]] = {}

    for category, urls in RSS_FEEDS.items():
        all_articles: list[dict[str, Any]] = []
        tasks = [loop.run_in_executor(None, _parse_feed, url) for url in urls]
        feed_results = await asyncio.gather(*tasks)
        for articles in feed_results:
            all_articles.extend(articles)

        # Sort newest first; entries without a timestamp go to the end
        all_articles.sort(
            key=lambda a: a.get("published_ts") or 0,
            reverse=True,
        )
        result[category] = all_articles[:MAX_ARTICLES_PER_CATEGORY]

    return result
