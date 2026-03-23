import pytest
from unittest.mock import patch, MagicMock
from src.collectors.news import fetch_news, RSS_FEEDS

def test_rss_feeds_has_all_categories():
    assert "headlines" in RSS_FEEDS
    assert "ai" in RSS_FEEDS
    assert "movies" in RSS_FEEDS
    assert "tesla" in RSS_FEEDS
    assert "stremio" in RSS_FEEDS

@pytest.mark.asyncio
async def test_fetch_news_returns_structured_data():
    mock_feed = MagicMock()
    mock_entry = MagicMock()
    mock_entry.title = "AI Breakthrough"
    mock_entry.link = "https://example.com/1"
    mock_entry.get.return_value = "Big news"
    mock_entry.published_parsed = None
    mock_feed.entries = [mock_entry]
    mock_feed.feed = MagicMock()
    mock_feed.feed.get.return_value = "Test Feed"

    with patch("src.collectors.news.feedparser.parse", return_value=mock_feed):
        result = await fetch_news()

    assert "headlines" in result
