import asyncio
import json
import traceback

import streamlit as st
from langchain_mcp_adapters.client import MultiServerMCPClient

st.set_page_config(page_title="News Dashboard", page_icon="📰", layout="wide")

# ── Constants ──────────────────────────────────────────────────────────────────
PYTHON_EXE    = r"C:\Users\user\Desktop\MCP-NEWS-CHATBOT\.venv\Scripts\python.exe"
SERVER_SCRIPT = r"C:\Users\user\Desktop\MCP-NEWS-CHATBOT\news_server.py"

DEFAULT_TOPICS = ["AI world", "Stock market"]

# ── Session state defaults ─────────────────────────────────────────────────────
st.session_state.setdefault("topics", DEFAULT_TOPICS.copy())
st.session_state.setdefault("selected_topic", DEFAULT_TOPICS[0])
st.session_state.setdefault("news_results", {})
st.session_state.setdefault("debug_raw", None)


# ── Async helper ───────────────────────────────────────────────────────────────
def run_async(coro):
    return asyncio.run(coro)


# ── MCP call ──────────────────────────────────────────────────────────────────
async def call_tool(topic: str):
    client_config = {
        "NewsAgent": {
            "transport": "stdio",
            "command": PYTHON_EXE,
            "args": [SERVER_SCRIPT],
        }
    }
    client = MultiServerMCPClient(client_config)
    tools  = await client.get_tools()
    tool   = next((t for t in tools if t.name == "get_news"), None)
    if tool is None:
        raise RuntimeError("get_news tool not found on the MCP server")
    return await tool.ainvoke({"topic": topic, "count": 10})


def fetch_news(topic: str):
    return run_async(call_tool(topic))


# ── Parser ─────────────────────────────────────────────────────────────────────
def extract_news(raw) -> list:
    """
    Unwrap whatever langchain-mcp-adapters returns into a plain list of news dicts.

    FastMCP (list return) → MCP wraps each item as a content block:
        [{'type': 'text', 'text': '{"title":...}'},
         {'type': 'text', 'text': '{"title":...}'}, ...]

    FastMCP (json.dumps str return) → single content block with full JSON:
        [{'type': 'text', 'text': '[{"title":...}, ...]'}]
    """
    if not raw:
        return []

    # Unwrap LangChain ToolMessage
    if hasattr(raw, "content"):
        raw = raw.content

    # At this point raw should be a list of MCP content blocks
    if not isinstance(raw, list):
        return []

    results = []
    for block in raw:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = block.get("text", "").strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            continue

        if isinstance(parsed, list):
            # Single block contains the full JSON array (old json.dumps path)
            for item in parsed:
                if isinstance(item, dict) and "title" in item:
                    results.append(item)
        elif isinstance(parsed, dict) and "title" in parsed:
            # Each block is one news item (native list return path)
            results.append(parsed)

    return results


# ── Callbacks ─────────────────────────────────────────────────────────────────
def cb_select(t: str):
    st.session_state.selected_topic = t


def cb_delete(t: str):
    topics: list = st.session_state.topics
    if t in topics:
        topics.remove(t)
    st.session_state.news_results.pop(t, None)
    st.session_state.selected_topic = topics[0] if topics else ""


def cb_add():
    val: str = st.session_state.get("new_topic_input", "").strip()
    if val and val not in st.session_state.topics:
        st.session_state.topics.append(val)
        st.session_state.selected_topic = val
    st.session_state["new_topic_input"] = ""


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📰 News Dashboard")

    st.text_input("Add topic", key="new_topic_input", placeholder="e.g. Climate change")
    st.button("＋ Add", on_click=cb_add)

    st.divider()

    for t in list(st.session_state.topics):
        col1, col2 = st.columns([5, 1])
        is_selected = t == st.session_state.selected_topic
        with col1:
            st.button(
                t,
                key=f"sel__{t}",
                on_click=cb_select,
                args=(t,),
                type="primary" if is_selected else "secondary",
                use_container_width=True,
            )
        with col2:
            st.button("✕", key=f"del__{t}", on_click=cb_delete, args=(t,))


# ── Main ──────────────────────────────────────────────────────────────────────
topic: str = st.session_state.selected_topic

if not topic:
    st.info("Add a topic in the sidebar to get started.")
    st.stop()

st.title(f"📡 {topic}")

col_fetch, col_debug = st.columns([3, 1])

with col_fetch:
    fetch_clicked = st.button("🔍 Fetch News", type="primary")



if fetch_clicked:
    try:
        with st.spinner(f"Fetching news for **{topic}** …"):
            raw  = fetch_news(topic)
            st.session_state.debug_raw = raw          # save for debug panel
            news = extract_news(raw)
            st.session_state.news_results[topic] = news
        st.rerun()

    except Exception:
        st.error("Fetch failed — see traceback below.")
        st.code(traceback.format_exc())



# ── Display ───────────────────────────────────────────────────────────────────
news_list: list = st.session_state.news_results.get(topic, [])

if not news_list:
    st.info("No news yet. Click **🔍 Fetch News** to load stories.")
else:
    st.caption(f"{len(news_list)} stories fetched")

    for i, item in enumerate(news_list, 1):
        with st.container(border=True):
            col_num, col_body = st.columns([1, 12])
            with col_num:
                st.markdown(f"#### {i}")
            with col_body:
                st.markdown(f"### {item.get('title', 'No title')}")
                published = item.get("published", "")
                if published:
                    try:
                        from email.utils import parsedate_to_datetime
                        from datetime import datetime, timezone
                        dt = parsedate_to_datetime(published).astimezone(timezone.utc)
                        diff = datetime.now(timezone.utc) - dt
                        hrs = int(diff.total_seconds() // 3600)
                        mins = int((diff.total_seconds() % 3600) // 60)
                        if hrs == 0:
                            age = f"{mins}m ago"
                        elif hrs < 24:
                            age = f"{hrs}h {mins}m ago"
                        else:
                            age = published
                        st.caption(f"🕐 {age}")
                    except Exception:
                        st.caption(published)
                link = item.get("link", "")
                if link:
                    st.link_button("Read article →", link)
