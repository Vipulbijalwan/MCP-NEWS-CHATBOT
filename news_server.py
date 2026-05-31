import feedparser
from urllib.parse import quote_plus
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("NewsAgent")


@mcp.tool()
def get_news(topic: str, count: int = 10):
    """Fetch latest Google News RSS safely"""

    try:
        # ---------------- SAFE INPUT ----------------
        topic = (topic or "").strip()
        if not topic:
            return []

        count = max(1, min(count, 20))  # safety limit

        query = quote_plus(topic)

        url = (
            "https://news.google.com/rss/search"
            f"?q={query}&hl=en&gl=US&ceid=US:en"
        )

        feed = feedparser.parse(url)

        if not hasattr(feed, "entries") or not feed.entries:
            return []

        results = []

        for entry in feed.entries[:count]:
            results.append({
                "title": getattr(entry, "title", "No title"),
                "link": getattr(entry, "link", ""),
                "published": getattr(entry, "published", "N/A")
            })

        return results

    except Exception as e:
        # NEVER crash MCP server
        return [{
            "title": "Error fetching news",
            "link": "",
            "published": str(e)
        }]


@mcp.tool()
def ping():
    return {
        "status": "ok",
        "message": "News MCP running"
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")