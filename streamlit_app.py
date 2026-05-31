import json
import asyncio
import traceback
import streamlit as st
from langchain_mcp_adapters.client import MultiServerMCPClient

st.set_page_config(page_title="News Dashboard", page_icon="📰", layout="wide")

# ── STATE ──
DEFAULT_TOPICS = ["AI world", "Stock market", "LinkedIn", "Politics", "World news"]

if "topics"         not in st.session_state: st.session_state.topics         = DEFAULT_TOPICS.copy()
if "selected_topic" not in st.session_state: st.session_state.selected_topic = "AI world"
if "news_results"   not in st.session_state: st.session_state.news_results   = {}

# ── MCP CLIENT ──
@st.cache_resource
def get_client():
    return MultiServerMCPClient({
        "NewsAgent": {
            "transport": "http",
            "command": "uv",
            "args": ["https://coastal-salmon-parrotfish.fastmcp.app/mcp"]
        }
    })
client = get_client()

async def call_tool(topic):
    tools = await client.get_tools()
    tool  = next((t for t in tools if t.name == "get_news"), None)
    if not tool:
        raise Exception("get_news tool not found")
    return await tool.ainvoke({"topic": topic, "count": 10})

def fetch_news(topic):
    return asyncio.run(call_tool(topic))

def extract_news(raw):
    try:
        if hasattr(raw, "content"):
            raw = raw.content
        results = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and "text" in item:
                    try:
                        data = json.loads(item["text"])
                        if isinstance(data, list):   results.extend(data)
                        elif isinstance(data, dict): results.append(data)
                    except: continue
                elif isinstance(item, dict):
                    results.append(item)
        return [x for x in results if isinstance(x, dict) and x.get("title")]
    except:
        return []

# ── CALLBACKS ──
def cb_select(t):   st.session_state.selected_topic = t
def cb_delete(t):
    if t in st.session_state.topics:
        st.session_state.topics.remove(t)
    if st.session_state.selected_topic == t:
        st.session_state.selected_topic = st.session_state.topics[0] if st.session_state.topics else None
    st.session_state.news_results.pop(t, None)

def cb_add():
    val = st.session_state.get("new_topic_input", "").strip()
    if val and val not in st.session_state.topics:
        st.session_state.topics.append(val)
        st.session_state.selected_topic = val

# ════════════════════════════
# SIDEBAR
# ════════════════════════════
with st.sidebar:
    st.title("📰 News Dashboard")
    st.divider()

    st.caption("ADD TOPIC")
    st.text_input("Add topic", placeholder="e.g. Crypto, Sports…",
                  label_visibility="collapsed", key="new_topic_input")
    st.button("＋ Add", use_container_width=True, on_click=cb_add)

    st.divider()
    st.caption("YOUR TOPICS")

    for t in list(st.session_state.topics):
        is_active = t == st.session_state.selected_topic
        col_t, col_d = st.columns([5, 1])
        with col_t:
            label = f"**→ {t}**" if is_active else t
            st.button(label, key=f"sel_{t}", use_container_width=True,
                      on_click=cb_select, args=(t,))
        with col_d:
            st.button("✕", key=f"del_{t}", on_click=cb_delete, args=(t,))

    st.divider()
    st.caption("Powered by DuckDuckGo · MCP · Groq")

# ════════════════════════════
# MAIN
# ════════════════════════════
topic = st.session_state.selected_topic

if not topic:
    st.info("Select a topic from the sidebar to get started.")
    st.stop()

st.title(f"📡 {topic}")

col_fetch, col_clear, _ = st.columns([1, 1, 6])
with col_fetch:
    fetch_clicked = st.button("🔍 Fetch news", type="primary", use_container_width=True)
with col_clear:
    if topic in st.session_state.news_results:
        if st.button("🗑 Clear", use_container_width=True):
            del st.session_state.news_results[topic]
            st.rerun()

st.divider()

# ── Fetch ──
if fetch_clicked:
    with st.spinner(f"Fetching {topic} news…"):
        try:
            raw  = fetch_news(topic)
            news = extract_news(raw)
            st.session_state.news_results[topic] = news
            st.rerun()
        except Exception:
            st.error("Fetch failed — is your MCP server running?")
            st.code(traceback.format_exc())

# ── Display ──
if topic in st.session_state.news_results:
    news_list = st.session_state.news_results[topic]

    if not news_list:
        st.warning("No stories found. Try fetching again.")
    else:
        st.caption(f"{len(news_list)} stories")
        for i, item in enumerate(news_list, 1):
            title  = item.get("title", "No title")
            link   = item.get("link", item.get("url", ""))
            date   = item.get("date", item.get("published", ""))
            source = item.get("source", "")
            body   = item.get("body", "")

            with st.container(border=True):
                meta = " · ".join(filter(None, [source, date]))
                if meta:
                    st.caption(f"#{i:02d} · {meta}")
                else:
                    st.caption(f"#{i:02d}")
                st.markdown(f"**{title}**")
                if body:
                    st.write(body)
                if link:
                    st.link_button("Read story →", link)
else:
    st.info(f"Press **Fetch news** to load {topic} headlines.")
