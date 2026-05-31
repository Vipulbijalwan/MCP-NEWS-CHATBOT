import feedparser
from urllib.parse import quote_plus
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("NewsAgent")


@mcp.tool()
def get_news(topic: str, count: int = 10):
    topic = (topic or "").strip()
    if not topic:
        return []

    count = max(1, min(count, 20))

    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(topic)}&hl=en&gl=US&ceid=US:en"
    )

    feed = feedparser.parse(url)

    return [
        {
            "title": e.get("title", "No title"),
            "link": e.get("link", ""),
            "published": e.get("published", "N/A"),
        }
        for e in feed.entries[:count]
    ]


@mcp.tool()
def ping():
    return {"status": "ok"}

