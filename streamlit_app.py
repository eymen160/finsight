"""
FinSight — AI-Powered Financial Analysis
Single-file Streamlit app with session_state navigation.
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

# ── 2026 Design System ────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"] {
    background: #080c14 !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Gradient mesh background ── */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 50% at 20% 10%, rgba(56,139,253,0.08) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 80%, rgba(63,185,80,0.06) 0%, transparent 60%),
        radial-gradient(ellipse 50% 60% at 50% 50%, rgba(139,92,246,0.04) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(13,17,28,0.95) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    backdrop-filter: blur(20px) !important;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }

/* ── Nav buttons ── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    color: #8b949e !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 10px 14px !important;
    text-align: left !important;
    width: 100% !important;
    margin-bottom: 4px !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.01em !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(56,139,253,0.12) !important;
    border-color: rgba(56,139,253,0.4) !important;
    color: #e6edf3 !important;
    transform: translateX(2px) !important;
}
.nav-active button {
    background: rgba(56,139,253,0.15) !important;
    border-color: rgba(56,139,253,0.5) !important;
    color: #58a6ff !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: rgba(22,27,42,0.8) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    backdrop-filter: blur(10px) !important;
    transition: border-color 0.2s !important;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(56,139,253,0.3) !important;
}
[data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 11px !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; }
[data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 22px !important; font-weight: 600 !important; }

/* ── Info / expander cards ── */
[data-testid="stAlert"] {
    background: rgba(22,27,42,0.7) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(12px) !important;
    color: #c9d1d9 !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: rgba(22,27,42,0.6) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] > div {
    background: rgba(22,27,42,0.9) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
}

/* ── Text inputs ── */
[data-testid="stTextInput"] > div > div {
    background: rgba(22,27,42,0.8) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #e6edf3 !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: rgba(22,27,42,0.8) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
}

/* ── Buttons (main) ── */
.stButton > button {
    background: linear-gradient(135deg, #1f6feb, #388bfd) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.02em !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 12px rgba(56,139,253,0.25) !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #388bfd, #58a6ff) !important;
    box-shadow: 0 4px 20px rgba(56,139,253,0.4) !important;
    transform: translateY(-1px) !important;
}

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.06) !important; margin: 16px 0 !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] { color: #58a6ff !important; }

/* ── Plotly dark bg ── */
.js-plotly-plot { border-radius: 14px !important; overflow: hidden !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(22,27,42,0.6) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
}

/* ── Success / error ── */
[data-testid="stSuccess"] { background: rgba(35,134,54,0.15) !important; border-color: rgba(35,134,54,0.3) !important; border-radius: 10px !important; }
[data-testid="stError"]   { background: rgba(248,81,73,0.15)  !important; border-color: rgba(248,81,73,0.3)  !important; border-radius: 10px !important; }

/* ── Typography ── */
h1 { font-size: 2rem !important; font-weight: 700 !important; color: #e6edf3 !important; letter-spacing: -0.02em !important; }
h2 { font-size: 1.4rem !important; font-weight: 600 !important; color: #e6edf3 !important; }
h3 { font-size: 1.1rem !important; font-weight: 600 !important; color: #c9d1d9 !important; }
p, li, .stMarkdown { color: #8b949e !important; line-height: 1.6 !important; }
code { font-family: 'JetBrains Mono', monospace !important; background: rgba(56,139,253,0.1) !important; color: #58a6ff !important; padding: 2px 6px !important; border-radius: 4px !important; font-size: 0.85em !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
</style>
""", unsafe_allow_html=True)

# ── State ─────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"

def _goto(p):
    st.session_state.page = p
    st.rerun()

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 20px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <span style="font-size:24px;">📈</span>
            <span style="font-size:18px;font-weight:700;color:#e6edf3;letter-spacing:-0.02em;">FinSight</span>
        </div>
        <span style="font-size:11px;color:#484f58;letter-spacing:0.05em;">AI FINANCIAL ANALYSIS · v0.1.0</span>
    </div>
    """, unsafe_allow_html=True)

    nav_items = [
        ("home",  "🏠", "Home"),
        ("stock", "📊", "Stock Analysis"),
        ("docs",  "📄", "Document Q&A"),
        ("chat",  "💬", "AI Chat"),
    ]
    for key, icon, label in nav_items:
        is_active = st.session_state.page == key
        css_class = "nav-active" if is_active else ""
        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
        if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
            _goto(key)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="padding:12px;background:rgba(248,81,73,0.08);border:1px solid rgba(248,81,73,0.2);border-radius:10px;">
        <p style="font-size:11px;color:#8b949e;margin:0;line-height:1.5;">
            ⚠️ <strong style="color:#c9d1d9;">Disclaimer</strong><br>
            For informational purposes only. Not investment advice.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════
if st.session_state.page == "home":
    st.markdown("""
    <div style="padding: 40px 0 24px;">
        <h1 style="font-size:2.8rem!important;background:linear-gradient(135deg,#58a6ff,#79c0ff,#a5d6ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:8px;">
            AI-Powered Financial Analysis
        </h1>
        <p style="font-size:16px;color:#8b949e;max-width:560px;line-height:1.6;">
            Institutional-grade stock analysis, SEC document intelligence, and conversational finance — all in one platform.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Bento grid cards
    c1, c2, c3 = st.columns(3, gap="medium")
    cards = [
        ("stock", "📊", "Stock Analysis",
         "Technical indicators (RSI, MACD, Bollinger Bands), fundamental metrics, and streaming AI analysis for any ticker.",
         "#1f6feb", "Open Stock Analysis"),
        ("docs",  "📄", "Document Q&A",
         "Upload 10-K, 10-Q, or earnings call transcripts. Ask questions grounded in the actual text via RAG.",
         "#238636", "Open Document Q&A"),
        ("chat",  "💬", "AI Chat",
         "Conversational financial assistant powered by Claude. Ask anything about markets, valuation, or macro trends.",
         "#6e40c9", "Open AI Chat"),
    ]
    for col, (page, icon, title, desc, color, btn_label) in zip([c1,c2,c3], cards):
        with col:
            st.markdown(f"""
            <div style="background:rgba(22,27,42,0.8);border:1px solid rgba(255,255,255,0.07);
                        border-radius:16px;padding:24px;margin-bottom:12px;
                        border-top:3px solid {color};min-height:160px;">
                <div style="font-size:28px;margin-bottom:12px;">{icon}</div>
                <h3 style="color:#e6edf3!important;font-size:15px!important;margin:0 0 8px;font-weight:600;">{title}</h3>
                <p style="font-size:13px;color:#8b949e;margin:0;line-height:1.5;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(btn_label, key=f"hero_{page}", use_container_width=True):
                _goto(page)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:rgba(22,27,42,0.5);border:1px solid rgba(255,255,255,0.06);
                border-radius:14px;padding:20px 24px;">
        <h3 style="color:#e6edf3!important;font-size:13px!important;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 16px;">
            ⚡ Quick Stats
        </h3>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">
            <div style="text-align:center;">
                <div style="font-size:24px;font-weight:700;color:#58a6ff;">15+</div>
                <div style="font-size:11px;color:#8b949e;">Technical Indicators</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:24px;font-weight:700;color:#3fb950;">RAG</div>
                <div style="font-size:11px;color:#8b949e;">Document Intelligence</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:24px;font-weight:700;color:#a371f7;">Claude</div>
                <div style="font-size:11px;color:#8b949e;">AI Analysis Engine</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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

    if "stock_client"  not in st.session_state: st.session_state.stock_client  = StockClient()
    if "claude_client" not in st.session_state: st.session_state.claude_client = ClaudeClient()
    stock_client  = st.session_state.stock_client
    claude_client = st.session_state.claude_client

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:#484f58;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:12px;">⚙️ Analysis Settings</p>', unsafe_allow_html=True)
        ticker = st.text_input("Ticker Symbol", value="AAPL", max_chars=10).upper().strip()
        period = st.selectbox("Time Period", ["1mo","3mo","6mo","1y","2y","5y"], index=3)
        run_ai = st.toggle("🤖 AI Analysis", value=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Data", use_container_width=True):
            stock_client.clear_cache()
            st.rerun()

    st.markdown('<h1 style="margin-bottom:4px;">📊 Stock Analysis</h1>', unsafe_allow_html=True)

    if not ticker:
        st.info("Enter a ticker symbol in the sidebar to begin.")
        st.stop()

    with st.spinner(f"Fetching market data for **{ticker}**…"):
        try:
            info   = stock_client.get_info(ticker)
            df_raw = stock_client.get_history(ticker, period=period)
        except FinSightError as exc:
            st.error(f"**Data Error:** {exc}")
            st.stop()

    df      = add_indicators(df_raw)
    signals = get_signals(df)
    bias    = signal_summary(signals)

    # Header
    bias_colors = {"BULLISH":"#3fb950","BEARISH":"#f85149","MIXED":"#d29922","NEUTRAL":"#8b949e"}
    bias_color  = bias_colors.get(bias, "#8b949e")
    st.markdown(f"""
    <div style="display:flex;align-items:baseline;gap:16px;margin-bottom:20px;flex-wrap:wrap;">
        <h2 style="color:#e6edf3!important;font-size:1.6rem!important;margin:0;">{info.name}</h2>
        <code style="font-size:14px!important;">{ticker}</code>
        <span style="font-size:12px;color:#8b949e;background:rgba(255,255,255,0.05);padding:3px 10px;border-radius:20px;">{info.sector}</span>
        <span style="font-size:13px;color:{bias_color};font-weight:600;background:rgba(255,255,255,0.04);padding:3px 12px;border-radius:20px;border:1px solid {bias_color}40;">⬤ {bias}</span>
    </div>
    """, unsafe_allow_html=True)

    def _fmt(v):
        if v is None: return "N/A"
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9:  return f"${v/1e9:.2f}B"
        if v >= 1e6:  return f"${v/1e6:.2f}M"
        return f"${v:,.2f}"

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Current Price",  f"${info.current_price:,.2f}"        if info.current_price        else "N/A")
    c2.metric("52W High",       f"${info.fifty_two_week_high:,.2f}"  if info.fifty_two_week_high  else "N/A")
    c3.metric("52W Low",        f"${info.fifty_two_week_low:,.2f}"   if info.fifty_two_week_low   else "N/A")
    c4.metric("P/E (TTM)",      f"{info.pe_ratio:.1f}x"              if info.pe_ratio             else "N/A")
    c5.metric("Fwd P/E",        f"{info.forward_pe:.1f}x"            if info.forward_pe           else "N/A")
    c6.metric("Market Cap",     _fmt(info.market_cap))

    st.markdown("<br>", unsafe_allow_html=True)

    # Chart
    close = df["Close"].squeeze()
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.58,0.22,0.20], vertical_spacing=0.02,
        subplot_titles=("Price  ·  Moving Averages  ·  Bollinger Bands", "RSI (14)", "MACD"),
    )
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"].squeeze(), high=df["High"].squeeze(),
        low=df["Low"].squeeze(), close=close, name="Price",
        increasing_line_color="#3fb950", decreasing_line_color="#f85149",
        increasing_fillcolor="rgba(63,185,80,0.8)", decreasing_fillcolor="rgba(248,81,73,0.8)",
        showlegend=False,
    ), row=1, col=1)
    # BB
    fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], line=dict(color="rgba(88,166,255,0.3)",width=1), showlegend=False, name="BB Upper"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], line=dict(color="rgba(88,166,255,0.3)",width=1),
        fill="tonexty", fillcolor="rgba(88,166,255,0.05)", showlegend=False, name="BB Lower"), row=1, col=1)
    # SMAs
    for col_name, color, label in [("sma_20","#f0a500","SMA 20"),("sma_50","#58a6ff","SMA 50"),("sma_200","#f85149","SMA 200")]:
        fig.add_trace(go.Scatter(x=df.index, y=df[col_name], name=label, line=dict(color=color, width=1.3)), row=1, col=1)
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df["rsi_14"], name="RSI", line=dict(color="#a371f7",width=1.5)), row=2, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(248,81,73,0.06)", line_width=0, row=2, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(63,185,80,0.06)", line_width=0, row=2, col=1)
    fig.add_hline(y=70, line=dict(color="#f85149",dash="dot",width=1), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="#3fb950",dash="dot",width=1), row=2, col=1)
    # MACD
    fig.add_trace(go.Scatter(x=df.index, y=df["macd"],        name="MACD",   line=dict(color="#58a6ff",width=1.3)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"], name="Signal", line=dict(color="#f0a500",width=1.3)), row=3, col=1)
    hist_colors = ["rgba(63,185,80,0.7)" if v>=0 else "rgba(248,81,73,0.7)" for v in df["macd_hist"].fillna(0)]
    fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"], name="Hist", marker_color=hist_colors, showlegend=False), row=3, col=1)

    fig.update_layout(
        height=700,
        paper_bgcolor="rgba(13,17,28,0)",
        plot_bgcolor ="rgba(22,27,42,0.6)",
        font=dict(family="Inter", color="#8b949e", size=11),
        margin=dict(l=0,r=0,t=28,b=0),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(13,17,28,0.8)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1),
        xaxis3=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)"),
        yaxis= dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", side="right"),
        yaxis2=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", side="right", range=[0,100]),
        yaxis3=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", side="right"),
    )
    for i in range(1,4):
        fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", row=i, col=1)

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    # Signals
    with st.expander("📡 Technical Signal Dashboard", expanded=True):
        if signals:
            sig_cols = st.columns(len(signals))
            colors = {"BULLISH":"#3fb950","BEARISH":"#f85149","NEUTRAL":"#d29922"}
            for col, (name, val) in zip(sig_cols, signals.items()):
                c = colors.get(val,"#8b949e")
                col.markdown(f"""
                <div style="background:rgba(22,27,42,0.8);border:1px solid {c}30;border-radius:10px;padding:12px;text-align:center;">
                    <div style="font-size:10px;color:#8b949e;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">{name}</div>
                    <div style="font-size:13px;font-weight:600;color:{c};">{'🟢' if val=='BULLISH' else '🔴' if val=='BEARISH' else '🟡'} {val}</div>
                </div>
                """, unsafe_allow_html=True)

    # AI Analysis
    if run_ai:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <span style="font-size:18px;">🤖</span>
            <h3 style="color:#e6edf3!important;font-size:15px!important;margin:0;">Claude AI Analysis</h3>
            <span style="font-size:11px;color:#8b949e;background:rgba(56,139,253,0.1);padding:2px 8px;border-radius:20px;border:1px solid rgba(56,139,253,0.2);">Streaming</span>
        </div>
        """, unsafe_allow_html=True)
        with st.spinner("Generating analysis…"):
            try:
                msgs = claude_client.build_analysis_prompt(
                    ticker=ticker, info=info.__dict__,
                    signals=signals, signal_summary=bias, period=period)
                with st.container():
                    st.markdown('<div style="background:rgba(22,27,42,0.6);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:20px;">', unsafe_allow_html=True)
                    st.write_stream(claude_client.stream(msgs))
                    st.markdown("</div>", unsafe_allow_html=True)
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

    if "rag_pipeline"  not in st.session_state: st.session_state.rag_pipeline  = RAGPipeline()
    if "claude_client" not in st.session_state: st.session_state.claude_client = ClaudeClient()
    if "doc_messages"  not in st.session_state: st.session_state.doc_messages  = []
    rag    = st.session_state.rag_pipeline
    claude = st.session_state.claude_client

    st.markdown('<h1 style="margin-bottom:4px;">📄 Document Q&A</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e;margin-bottom:24px;">Upload SEC filings or earnings transcripts — ask questions grounded in the actual text.</p>', unsafe_allow_html=True)

    col_up, col_qa = st.columns([1, 2], gap="large")

    with col_up:
        st.markdown("""
        <div style="background:rgba(22,27,42,0.6);border:1px solid rgba(255,255,255,0.07);
                    border-radius:14px;padding:20px;margin-bottom:16px;">
            <p style="font-size:11px;color:#484f58;letter-spacing:0.08em;text-transform:uppercase;margin:0 0 12px;">📁 Upload Document</p>
        </div>
        """, unsafe_allow_html=True)
        uploaded = st.file_uploader("", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
        if uploaded:
            for file in uploaded:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(file.read())
                with st.spinner(f"Indexing **{file.name}**…"):
                    try:
                        n = rag.ingest(tmp.name)
                        st.success(f"✅ {file.name} · {n} chunks indexed")
                    except FinSightError as exc:
                        st.error(str(exc))

        docs = rag.list_documents()
        if docs:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p style="font-size:11px;color:#484f58;letter-spacing:0.08em;text-transform:uppercase;">📚 Indexed Documents</p>', unsafe_allow_html=True)
            for d in docs:
                st.markdown(f'<div style="background:rgba(35,134,54,0.08);border:1px solid rgba(35,134,54,0.2);border-radius:8px;padding:8px 12px;margin-bottom:6px;font-size:12px;color:#3fb950;">📄 {d}</div>', unsafe_allow_html=True)

            if st.button("🗑️ Clear Index", use_container_width=True):
                rag.clear()
                st.session_state.doc_messages = []
                st.rerun()

    with col_qa:
        st.markdown('<p style="font-size:11px;color:#484f58;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:12px;">💬 Ask Questions</p>', unsafe_allow_html=True)

        if not docs:
            st.markdown("""
            <div style="background:rgba(22,27,42,0.5);border:1px dashed rgba(255,255,255,0.1);border-radius:14px;padding:40px;text-align:center;">
                <div style="font-size:32px;margin-bottom:12px;">📄</div>
                <p style="color:#8b949e;margin:0;">Upload a PDF document to start asking questions</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in st.session_state.doc_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            query = st.chat_input("e.g. What are the key risk factors? What was revenue growth?")
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

    if "claude_client" not in st.session_state: st.session_state.claude_client = ClaudeClient()
    if "chat_messages" not in st.session_state: st.session_state.chat_messages = []
    claude = st.session_state.claude_client

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:#484f58;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px;">💡 Suggested Questions</p>', unsafe_allow_html=True)
        suggestions = [
            "Explain P/E vs EV/EBITDA",
            "What signals an inverted yield curve?",
            "How do I read a cash flow statement?",
            "Compare growth vs value investing",
            "What is dollar-cost averaging?",
        ]
        for s in suggestions:
            if st.button(f"→ {s}", key=f"sug_{s[:20]}", use_container_width=True):
                st.session_state.chat_messages.append({"role":"user","content":s})
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()

    st.markdown('<h1 style="margin-bottom:4px;">💬 AI Financial Chat</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e;margin-bottom:20px;">Conversational financial intelligence powered by Claude. Ask anything about markets, valuation, or macroeconomics.</p>', unsafe_allow_html=True)

    # Chat history
    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_messages:
            st.markdown("""
            <div style="background:rgba(22,27,42,0.4);border:1px dashed rgba(255,255,255,0.08);border-radius:16px;padding:48px;text-align:center;margin:24px 0;">
                <div style="font-size:40px;margin-bottom:16px;">💬</div>
                <h3 style="color:#e6edf3;font-size:16px;margin:0 0 8px;">Start a conversation</h3>
                <p style="color:#8b949e;font-size:13px;margin:0;">Ask about stocks, markets, financial concepts, or investment strategies</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

    user_input = st.chat_input("Ask FinSight anything about finance…")
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
