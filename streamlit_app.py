import json
import asyncio
import traceback
import streamlit as st
from langchain_mcp_adapters.client import MultiServerMCPClient

st.set_page_config(page_title="News Dashboard", page_icon="📰", layout="wide")

# ── STATE ──
DEFAULT_TOPICS = ["AI world", "Stock market", "LinkedIn", "Politics", "World news"]

if "topics" not in st.session_state:
    st.session_state.topics = DEFAULT_TOPICS.copy()

if "selected_topic" not in st.session_state:
    st.session_state.selected_topic = "AI world"

if "news_results" not in st.session_state:
    st.session_state.news_results = {}

# ── MCP CLIENT ──
@st.cache_resource
def get_client():
    return MultiServerMCPClient({
        "NewsAgent": {
            "transport": "streamable_http",
            "url": "https://coastal-salmon-parrotfish.fastmcp.app/mcp"
        }
    })

client = get_client()


# ── TOOL CALL ──
async def call_tool(topic):
    tools = await client.get_tools()
    tool = next((t for t in tools if t.name == "get_news"), None)

    if not tool:
        raise Exception("get_news tool not found")

    return await tool.ainvoke({"topic": topic, "count": 10})


def fetch_news(topic):
    return asyncio.run(call_tool(topic))


# ── PARSER ──
def extract_news(raw):
    try:
        if hasattr(raw, "content"):
            raw = raw.content

        results = []

        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    results.append(item)

        return [x for x in results if isinstance(x, dict) and x.get("title")]

    except Exception:
        return []


# ── CALLBACKS ──
def cb_select(t):
    st.session_state.selected_topic = t


def cb_delete(t):
    if t in st.session_state.topics:
        st.session_state.topics.remove(t)

    if st.session_state.selected_topic == t:
        st.session_state.selected_topic = (
            st.session_state.topics[0] if st.session_state.topics else None
        )

    st.session_state.news_results.pop(t, None)


def cb_add():
    val = st.session_state.get("new_topic_input", "").strip()
    if val and val not in st.session_state.topics:
        st.session_state.topics.append(val)
        st.session_state.selected_topic = val


# ── SIDEBAR ──
with st.sidebar:
    st.title("📰 News Dashboard")

    st.text_input("Add topic", key="new_topic_input")
    st.button("＋ Add", on_click=cb_add)

    st.divider()

    for t in list(st.session_state.topics):
        col1, col2 = st.columns([5, 1])

        with col1:
            st.button(t, key=f"sel_{t}", on_click=cb_select, args=(t,))

        with col2:
            st.button("✕", key=f"del_{t}", on_click=cb_delete, args=(t,))


# ── MAIN ──
topic = st.session_state.selected_topic

if not topic:
    st.info("Select a topic")
    st.stop()

st.title(f"📡 {topic}")

col1, col2, _ = st.columns([1, 1, 6])

with col1:
    fetch_clicked = st.button("🔍 Fetch News", type="primary")

with col2:
    if topic in st.session_state.news_results:
        if st.button("🗑 Clear"):
            del st.session_state.news_results[topic]
            st.rerun()


# ── FETCH ──
if fetch_clicked:
    try:
        with st.spinner("Fetching news..."):
            raw = fetch_news(topic)
            news = extract_news(raw)
            st.session_state.news_results[topic] = news
            st.rerun()

    except Exception:
        st.error("Fetch failed")
        st.code(traceback.format_exc())


# ── DISPLAY ──
if topic in st.session_state.news_results:
    news_list = st.session_state.news_results[topic]

    if not news_list:
        st.warning("No news found")
    else:
        st.caption(f"{len(news_list)} stories")

        for i, item in enumerate(news_list, 1):
            with st.container(border=True):
                st.markdown(f"### {item.get('title')}")
                st.write(item.get("published", ""))
                if item.get("link"):
                    st.link_button("Read", item["link"])

else:
    st.info("Click Fetch News")