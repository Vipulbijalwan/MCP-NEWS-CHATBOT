from fastmcp import FastMCP
import feedparser
from urllib.parse import quote_plus
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

mcp = FastMCP("NewsAgent")


def parse_published(published_str: str):
    """Parse RFC 2822 date string to UTC datetime. Returns None on failure."""
    try:
        return parsedate_to_datetime(published_str).astimezone(timezone.utc)
    except Exception:
        return None


def fetch_news(topic: str, count: int = 10):
    topic = (topic or "").strip()
    if not topic:
        return []

    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(topic)}&hl=en&gl=US&ceid=US:en"
    )

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        return [{"error": str(e)}]

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    results = []
    for entry in feed.entries:
        published_str = getattr(entry, "published", "")
        published_dt  = parse_published(published_str)

        # Skip articles older than 24 hours
        if published_dt is None or published_dt < cutoff:
            continue

        results.append({
            "title":        getattr(entry, "title",   "No title"),
            "link":         getattr(entry, "link",    ""),
            "published":    published_str,
            "published_ts": published_dt.timestamp(),   # for sorting
        })

    # Sort by newest first
    results.sort(key=lambda x: x["published_ts"], reverse=True)

    # Remove internal sort key before returning
    for r in results:
        del r["published_ts"]

    return results[:count]


@mcp.tool()
def get_news(topic: str, count: int = 10) -> list:
    """Fetch the most popular news articles from the last 24 hours for a given topic."""
    return fetch_news(topic, count)


if __name__ == "__main__":
    mcp.run(transport="stdio")
