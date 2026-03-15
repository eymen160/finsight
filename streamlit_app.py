"""
FinSight — Single-file Streamlit App
Handles all navigation via session_state to avoid multi-page issues.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="FinSight · AI Financial Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inline CSS ────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { min-width: 220px; }
.nav-btn > button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #e8eaf0 !important;
    text-align: left !important;
    margin-bottom: 4px !important;
    transition: all 0.2s;
}
.nav-btn > button:hover {
    background: rgba(52,152,219,0.2) !important;
    border-color: #3498db !important;
}
</style>
""", unsafe_allow_html=True)

# ── Page state ────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"

# ── Sidebar navigation ────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 FinSight")
    st.caption("v0.1.0")
    st.divider()

    pages = {
        "home":     ("🏠", "Home"),
        "stock":    ("📊", "Stock Analysis"),
        "docs":     ("📄", "Document Q&A"),
        "chat":     ("💬", "AI Chat"),
    }
    for key, (icon, label) in pages.items():
        active = "**" if st.session_state.page == key else ""
        if st.button(f"{icon} {active}{label}{active}", key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.divider()
    st.caption("⚠️ For informational purposes only. Not investment advice.")

# ══════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════
if st.session_state.page == "home":
    st.title("📈 FinSight")
    st.subheader("AI-Powered Financial Analysis")
    st.markdown("Your intelligent financial research assistant. Choose a feature below.")
    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**📊 Stock Analysis**\n\nTechnical indicators (RSI, MACD, Bollinger Bands), fundamental metrics, and AI-generated analysis for any ticker.")
        if st.button("Open Stock Analysis →", key="h_stock", use_container_width=True):
            st.session_state.page = "stock"; st.rerun()
    with c2:
        st.info("**📄 Document Q&A**\n\nUpload 10-K, 10-Q, or earnings transcripts and ask questions grounded in the text via RAG.")
        if st.button("Open Document Q&A →", key="h_docs", use_container_width=True):
            st.session_state.page = "docs"; st.rerun()
    with c3:
        st.info("**💬 AI Chat**\n\nConversational financial assistant powered by Claude. Ask anything about markets, stocks, or finance.")
        if st.button("Open AI Chat →", key="h_chat", use_container_width=True):
            st.session_state.page = "chat"; st.rerun()

# ══════════════════════════════════════════════════════════════
# STOCK ANALYSIS
# ══════════════════════════════════════════════════════════════
elif st.session_state.page == "stock":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from core.analysis.technical import add_indicators, get_signals, signal_summary
    from core.data.stock_client import StockClient
    from core.exceptions import FinSightError
    from core.llm.claude_client import ClaudeClient

    if "stock_client" not in st.session_state:
        st.session_state.stock_client = StockClient()
    if "claude_client" not in st.session_state:
        st.session_state.claude_client = ClaudeClient()

    stock_client = st.session_state.stock_client
    claude_client = st.session_state.claude_client

    with st.sidebar:
        st.divider()
        st.markdown("### ⚙️ Settings")
        ticker = st.text_input("Ticker Symbol", value="AAPL", max_chars=10).upper().strip()
        period = st.selectbox("Time Period", ["1mo","3mo","6mo","1y","2y","5y"], index=3)
        run_ai = st.toggle("AI Analysis", value=True)
        if st.button("🔄 Refresh", use_container_width=True):
            stock_client.clear_cache()
            st.rerun()

    st.title("📊 Stock Analysis")
    if not ticker:
        st.info("Enter a ticker symbol in the sidebar.")
        st.stop()

    with st.spinner(f"Fetching **{ticker}**…"):
        try:
            info   = stock_client.get_info(ticker)
            df_raw = stock_client.get_history(ticker, period=period)
        except FinSightError as exc:
            st.error(str(exc)); st.stop()

    df      = add_indicators(df_raw)
    signals = get_signals(df)
    bias    = signal_summary(signals)

    st.markdown(f"## {info.name} `{ticker}`")
    st.caption(f"{info.sector} · {info.industry}")

    def _fmt(v):
        if v is None: return "N/A"
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9:  return f"${v/1e9:.2f}B"
        if v >= 1e6:  return f"${v/1e6:.2f}M"
        return f"${v:,.0f}"

    bias_icon = {"BULLISH":"🟢","BEARISH":"🔴","MIXED":"🟡","NEUTRAL":"⚪"}.get(bias,"⚪")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Price",      f"${info.current_price:,.2f}"       if info.current_price       else "N/A")
    c2.metric("52W High",   f"${info.fifty_two_week_high:,.2f}" if info.fifty_two_week_high else "N/A")
    c3.metric("52W Low",    f"${info.fifty_two_week_low:,.2f}"  if info.fifty_two_week_low  else "N/A")
    c4.metric("P/E (TTM)",  f"{info.pe_ratio:.1f}"              if info.pe_ratio            else "N/A")
    c5.metric("Market Cap", _fmt(info.market_cap))
    c6.metric("Signal",     f"{bias_icon} {bias}")
    st.divider()

    close = df["Close"].squeeze()
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.55,0.25,0.20], vertical_spacing=0.03,
        subplot_titles=("Price & Moving Averages","RSI (14)","MACD"))

    fig.add_trace(go.Candlestick(x=df.index,
        open=df["Open"].squeeze(), high=df["High"].squeeze(),
        low=df["Low"].squeeze(), close=close, name="OHLC", showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"],
        line=dict(color="rgba(173,216,230,0.4)",width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"],
        line=dict(color="rgba(173,216,230,0.4)",width=1),
        fill="tonexty", fillcolor="rgba(173,216,230,0.08)", showlegend=False), row=1, col=1)
    for col_name, color, label in [("sma_20","#f39c12","SMA 20"),("sma_50","#3498db","SMA 50"),("sma_200","#e74c3c","SMA 200")]:
        fig.add_trace(go.Scatter(x=df.index, y=df[col_name], name=label,
            line=dict(color=color, width=1.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["rsi_14"], name="RSI",
        line=dict(color="#9b59b6",width=1.5)), row=2, col=1)
    fig.add_hline(y=70, line_color="red",   line_dash="dash", row=2, col=1)
    fig.add_hline(y=30, line_color="green", line_dash="dash", row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["macd"],        name="MACD",   line=dict(color="#3498db",width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"], name="Signal", line=dict(color="#e74c3c",width=1.2)), row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"], name="Hist",
        marker_color=["#2ecc71" if v>=0 else "#e74c3c" for v in df["macd_hist"].fillna(0)]), row=3, col=1)
    fig.update_layout(height=680, template="plotly_dark",
        margin=dict(l=0,r=0,t=30,b=0), xaxis_rangeslider_visible=False,
        legend=dict(orientation="h",yanchor="bottom",y=1.01,xanchor="right",x=1))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📡 Technical Signals", expanded=True):
        if signals:
            cols = st.columns(len(signals))
            emo = {"BULLISH":"🟢","BEARISH":"🔴","NEUTRAL":"🟡"}
            for col, (name, val) in zip(cols, signals.items()):
                col.metric(name, f"{emo.get(val,'')} {val}")

    if run_ai:
        st.divider()
        st.markdown("### 🤖 AI Analysis")
        with st.spinner("Generating analysis…"):
            try:
                msgs = claude_client.build_analysis_prompt(
                    ticker=ticker, info=info.__dict__,
                    signals=signals, signal_summary=bias, period=period)
                st.write_stream(claude_client.stream(msgs))
            except FinSightError as exc:
                st.error(f"AI analysis failed: {exc}")

# ══════════════════════════════════════════════════════════════
# DOCUMENT Q&A
# ══════════════════════════════════════════════════════════════
elif st.session_state.page == "docs":
    import tempfile
    from core.exceptions import FinSightError
    from core.llm.claude_client import ClaudeClient
    from core.rag.pipeline import RAGPipeline

    if "rag_pipeline"   not in st.session_state: st.session_state.rag_pipeline   = RAGPipeline()
    if "claude_client"  not in st.session_state: st.session_state.claude_client  = ClaudeClient()
    if "doc_messages"   not in st.session_state: st.session_state.doc_messages   = []

    rag    = st.session_state.rag_pipeline
    claude = st.session_state.claude_client

    st.title("📄 Document Q&A")
    st.caption("Upload 10-K, 10-Q, or earnings transcripts and ask questions grounded in the text.")

    col_up, col_qa = st.columns([1, 2], gap="large")

    with col_up:
        st.markdown("### 📁 Upload Document")
        uploaded = st.file_uploader("Upload PDF", type=["pdf"], accept_multiple_files=True)
        if uploaded:
            for file in uploaded:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(file.read())
                    tmp_path = tmp.name
                with st.spinner(f"Indexing **{file.name}**…"):
                    try:
                        n = rag.ingest(tmp_path)
                        st.success(f"✅ {file.name} — {n} chunks indexed")
                    except FinSightError as exc:
                        st.error(str(exc))
        st.divider()
        st.markdown("**Indexed:**")
        for d in rag.list_documents():
            st.markdown(f"- 📄 {d}")
        if not rag.list_documents():
            st.caption("No documents yet.")

    with col_qa:
        st.markdown("### 💬 Ask a Question")
        for msg in st.session_state.doc_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        query = st.chat_input("e.g. What are the main risk factors?")
        if query:
            st.session_state.doc_messages.append({"role":"user","content":query})
            with st.chat_message("user"): st.markdown(query)
            with st.chat_message("assistant"):
                try:
                    ctx  = rag.retrieve(query)
                    resp = st.write_stream(claude.stream([{"role":"user","content":query}], extra_context=ctx))
                    st.session_state.doc_messages.append({"role":"assistant","content":resp})
                except FinSightError as exc:
                    st.error(str(exc))

# ══════════════════════════════════════════════════════════════
# AI CHAT
# ══════════════════════════════════════════════════════════════
elif st.session_state.page == "chat":
    from core.exceptions import FinSightError
    from core.llm.claude_client import ClaudeClient

    if "claude_client"  not in st.session_state: st.session_state.claude_client  = ClaudeClient()
    if "chat_messages"  not in st.session_state: st.session_state.chat_messages  = []

    claude = st.session_state.claude_client

    with st.sidebar:
        st.divider()
        st.markdown("**💡 Try asking:**")
        st.caption("- Explain P/E vs P/S ratios\n- What is an inverted yield curve?\n- How do I read a cash flow statement?\n- What are risks of growth investing?")
        st.divider()
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()

    st.title("💬 AI Financial Chat")
    st.caption("Ask anything about markets, stocks, economic concepts, or financial theory.")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask FinSight…")
    if user_input:
        st.session_state.chat_messages.append({"role":"user","content":user_input})
        with st.chat_message("user"): st.markdown(user_input)
        api_msgs = [{"role":m["role"],"content":m["content"]} for m in st.session_state.chat_messages]
        with st.chat_message("assistant"):
            try:
                full = st.write_stream(claude.stream(api_msgs))
                st.session_state.chat_messages.append({"role":"assistant","content":full})
            except FinSightError as exc:
                st.error(f"Error: {exc}")
