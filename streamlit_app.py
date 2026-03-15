"""
FinSight — Streamlit Application Entry Point
================================================
Single-file app using session_state navigation (Streamlit Cloud compatible).

Architecture:
- UI layer   : this file only. No business logic here.
- Data layer : core/data/stock_client.py
- LLM layer  : core/llm/claude_client.py
- Analysis   : core/analysis/technical.py
- RAG        : core/rag/pipeline.py
- Config     : config/settings.py

@st.cache_resource is used for all heavy singletons (StockClient,
ClaudeClient, RAGPipeline) so they are initialised once per interpreter
process, not once per rerun.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Configure logging before any other import
from core.logger import configure_logging
from config.settings import settings
configure_logging(settings.log_level)

import streamlit as st

st.set_page_config(
    page_title="FinSight · AI Financial Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design System ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
    background: #080c14 !important;
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background:
        radial-gradient(ellipse 80% 50% at 20% 10%, rgba(56,139,253,0.07) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 80%, rgba(63,185,80,0.05) 0%, transparent 60%),
        radial-gradient(ellipse 50% 60% at 50% 50%, rgba(139,92,246,0.04) 0%, transparent 60%);
}

[data-testid="stSidebar"] {
    background: rgba(13,17,28,0.97) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    backdrop-filter: blur(20px) !important;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }

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

[data-testid="stMetric"] {
    background: rgba(22,27,42,0.8) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    backdrop-filter: blur(10px) !important;
    transition: border-color 0.2s !important;
}
[data-testid="stMetric"]:hover { border-color: rgba(56,139,253,0.3) !important; }
[data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 11px !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; }
[data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 22px !important; font-weight: 600 !important; }

[data-testid="stAlert"] {
    background: rgba(22,27,42,0.7) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(12px) !important;
}
[data-testid="stChatMessage"] {
    background: rgba(22,27,42,0.6) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
}
[data-testid="stChatInput"] > div {
    background: rgba(22,27,42,0.9) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
}
[data-testid="stTextInput"] > div > div {
    background: rgba(22,27,42,0.8) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #e6edf3 !important;
}
[data-testid="stSelectbox"] > div > div {
    background: rgba(22,27,42,0.8) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
}

/* Main action buttons */
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
    box-shadow: 0 4px 20px rgba(56,139,253,0.4) !important;
    transform: translateY(-1px) !important;
}

[data-testid="stExpander"] {
    background: rgba(22,27,42,0.6) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
}
[data-testid="stSuccess"] { background: rgba(35,134,54,0.12) !important; border-color: rgba(35,134,54,0.3) !important; border-radius: 10px !important; }
[data-testid="stError"]   { background: rgba(248,81,73,0.12)  !important; border-color: rgba(248,81,73,0.3)  !important; border-radius: 10px !important; }
[data-testid="stWarning"] { background: rgba(210,153,34,0.12) !important; border-color: rgba(210,153,34,0.3) !important; border-radius: 10px !important; }

hr { border-color: rgba(255,255,255,0.06) !important; margin: 16px 0 !important; }
.js-plotly-plot { border-radius: 14px !important; overflow: hidden !important; }

h1 { font-size: 2rem !important; font-weight: 700 !important; color: #e6edf3 !important; letter-spacing: -0.02em !important; }
h2 { font-size: 1.4rem !important; font-weight: 600 !important; color: #e6edf3 !important; }
h3 { font-size: 1.1rem !important; font-weight: 600 !important; color: #c9d1d9 !important; }
p, li, .stMarkdown { color: #8b949e !important; line-height: 1.6 !important; }
code { font-family: 'JetBrains Mono', monospace !important; background: rgba(56,139,253,0.1) !important; color: #58a6ff !important; padding: 2px 6px !important; border-radius: 4px !important; font-size: 0.85em !important; }

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# ── Cached resource factory functions ─────────────────────────
# @st.cache_resource: initialised ONCE per process, shared across all
# sessions and reruns. Correct for heavy objects (API clients, indexes).

@st.cache_resource
def _get_stock_client():
    from core.data.stock_client import StockClient
    return StockClient()

@st.cache_resource
def _get_claude_client():
    from core.llm.claude_client import ClaudeClient
    return ClaudeClient()

@st.cache_resource
def _get_rag_pipeline():
    from core.rag.pipeline import RAGPipeline
    return RAGPipeline()


# ── Navigation state ──────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"

def _goto(page: str) -> None:
    st.session_state.page = page
    st.rerun()


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:8px 0 20px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <span style="font-size:24px;">📈</span>
            <span style="font-size:18px;font-weight:700;color:#e6edf3;letter-spacing:-0.02em;">FinSight</span>
        </div>
        <span style="font-size:11px;color:#484f58;letter-spacing:0.05em;">AI FINANCIAL ANALYSIS · v0.1.0</span>
    </div>
    """, unsafe_allow_html=True)

    _NAV = [("home","🏠","Home"),("stock","📊","Stock Analysis"),("docs","📄","Document Q&A"),("chat","💬","AI Chat")]
    for key, icon, label in _NAV:
        active = st.session_state.page == key
        st.markdown(f'<div class="{"nav-active" if active else ""}">', unsafe_allow_html=True)
        if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
            _goto(key)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="padding:12px;background:rgba(248,81,73,0.07);border:1px solid rgba(248,81,73,0.2);border-radius:10px;">
        <p style="font-size:11px;color:#8b949e;margin:0;line-height:1.5;">
            ⚠️ <strong style="color:#c9d1d9;">Disclaimer</strong><br>
            For informational purposes only. Not investment advice.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════
if st.session_state.page == "home":
    st.markdown("""
    <div style="padding:40px 0 24px;">
        <h1 style="font-size:2.8rem!important;background:linear-gradient(135deg,#58a6ff,#79c0ff,#a5d6ff);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:8px;">
            AI-Powered Financial Analysis
        </h1>
        <p style="font-size:16px;color:#8b949e;max-width:560px;line-height:1.7;">
            Institutional-grade stock analysis, SEC document intelligence,
            and conversational finance — all in one platform.
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3, gap="medium")
    _CARDS = [
        ("stock","📊","Stock Analysis","Technical indicators (RSI, MACD, Bollinger Bands), fundamental metrics, and streaming AI analysis for any ticker.","#1f6feb","Open Stock Analysis"),
        ("docs", "📄","Document Q&A",  "Upload 10-K, 10-Q, or earnings transcripts. Ask questions grounded in the actual text via RAG.",                 "#238636","Open Document Q&A"),
        ("chat", "💬","AI Chat",        "Conversational financial assistant powered by Claude. Ask anything about markets, valuation, or macro trends.",     "#6e40c9","Open AI Chat"),
    ]
    for col, (page, icon, title, desc, color, btn) in zip([c1,c2,c3], _CARDS):
        with col:
            st.markdown(f"""
            <div style="background:rgba(22,27,42,0.8);border:1px solid rgba(255,255,255,0.07);
                        border-top:3px solid {color};border-radius:16px;padding:24px;margin-bottom:12px;min-height:160px;">
                <div style="font-size:28px;margin-bottom:12px;">{icon}</div>
                <h3 style="color:#e6edf3!important;font-size:15px!important;margin:0 0 8px;font-weight:600;">{title}</h3>
                <p style="font-size:13px;color:#8b949e;margin:0;line-height:1.5;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(btn, key=f"h_{page}", use_container_width=True):
                _goto(page)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:rgba(22,27,42,0.5);border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:20px 24px;">
        <p style="font-size:11px;color:#484f58;letter-spacing:0.08em;text-transform:uppercase;margin:0 0 16px;">⚡ Platform Capabilities</p>
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
# PAGE: STOCK ANALYSIS
# ══════════════════════════════════════════════════════════════
elif st.session_state.page == "stock":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from core.analysis.technical import add_indicators, get_signals, signal_summary
    from core.exceptions import FinSightError, RateLimitError, TickerNotFoundError

    stock_client  = _get_stock_client()
    claude_client = _get_claude_client()

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:#484f58;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:12px;">⚙️ Settings</p>', unsafe_allow_html=True)
        ticker = st.text_input("Ticker Symbol", value="AAPL", max_chars=10).upper().strip()
        period = st.selectbox("Time Period", ["1mo","3mo","6mo","1y","2y","5y"], index=3)
        run_ai = st.toggle("🤖 AI Analysis", value=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Data", use_container_width=True):
            stock_client.clear_cache()
            st.cache_data.clear()
            st.rerun()

    st.markdown('<h1 style="margin-bottom:4px;">📊 Stock Analysis</h1>', unsafe_allow_html=True)

    if not ticker:
        st.info("Enter a ticker symbol in the sidebar to begin.")
        st.stop()

    # ── Data fetch with specific error handling ───────────────
    with st.spinner(f"Fetching market data for **{ticker}**…"):
        try:
            info   = stock_client.get_info(ticker)
            df_raw = stock_client.get_history(ticker, period=period)
        except RateLimitError as exc:
            st.warning(
                f"⚠️ **Yahoo Finance Rate Limit** — {exc}\n\n"
                "Wait 30–60 seconds, then click **🔄 Refresh Data** in the sidebar.\n"
                "Data is cached for 10 minutes once loaded successfully."
            )
            st.stop()
        except TickerNotFoundError as exc:
            st.error(f"**Ticker Not Found:** {exc}")
            st.stop()
        except FinSightError as exc:
            st.error(f"**Data Error:** {exc}")
            st.stop()

    df      = add_indicators(df_raw)
    signals = get_signals(df)
    bias    = signal_summary(signals)

    # ── Header ────────────────────────────────────────────────
    _BIAS_COLOR = {"BULLISH":"#3fb950","BEARISH":"#f85149","MIXED":"#d29922","NEUTRAL":"#8b949e"}
    bc = _BIAS_COLOR.get(bias, "#8b949e")

    st.markdown(f"""
    <div style="display:flex;align-items:baseline;gap:16px;margin-bottom:20px;flex-wrap:wrap;">
        <h2 style="color:#e6edf3!important;font-size:1.6rem!important;margin:0;">{info.name}</h2>
        <code style="font-size:14px!important;">{ticker}</code>
        <span style="font-size:12px;color:#8b949e;background:rgba(255,255,255,0.05);padding:3px 10px;border-radius:20px;">{info.sector}</span>
        <span style="font-size:13px;color:{bc};font-weight:600;background:rgba(255,255,255,0.04);padding:3px 12px;border-radius:20px;border:1px solid {bc}40;">⬤ {bias}</span>
    </div>
    """, unsafe_allow_html=True)

    def _fmt_cap(v: float | int | None) -> str:
        if v is None: return "N/A"
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9:  return f"${v/1e9:.2f}B"
        if v >= 1e6:  return f"${v/1e6:.2f}M"
        return f"${v:,.2f}"

    mc1,mc2,mc3,mc4,mc5,mc6 = st.columns(6)
    mc1.metric("Current Price",  f"${info.current_price:,.2f}"        if info.current_price        else "N/A")
    mc2.metric("52W High",       f"${info.fifty_two_week_high:,.2f}"  if info.fifty_two_week_high  else "N/A")
    mc3.metric("52W Low",        f"${info.fifty_two_week_low:,.2f}"   if info.fifty_two_week_low   else "N/A")
    mc4.metric("P/E (TTM)",      f"{info.pe_ratio:.1f}x"              if info.pe_ratio             else "N/A")
    mc5.metric("Fwd P/E",        f"{info.forward_pe:.1f}x"            if info.forward_pe           else "N/A")
    mc6.metric("Market Cap",     _fmt_cap(info.market_cap))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Chart ─────────────────────────────────────────────────
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.58,0.22,0.20], vertical_spacing=0.02,
        subplot_titles=("Price · Moving Averages · Bollinger Bands","RSI (14)","MACD"),
    )
    close = df["Close"].squeeze()

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"].squeeze(), high=df["High"].squeeze(),
        low=df["Low"].squeeze(), close=close, name="Price",
        increasing_line_color="#3fb950", decreasing_line_color="#f85149",
        increasing_fillcolor="rgba(63,185,80,0.8)", decreasing_fillcolor="rgba(248,81,73,0.8)",
        showlegend=False,
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"],
        line=dict(color="rgba(88,166,255,0.3)", width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"],
        line=dict(color="rgba(88,166,255,0.3)", width=1),
        fill="tonexty", fillcolor="rgba(88,166,255,0.05)", showlegend=False), row=1, col=1)

    for col_n, color, lbl in [("sma_20","#f0a500","SMA 20"),("sma_50","#58a6ff","SMA 50"),("sma_200","#f85149","SMA 200")]:
        fig.add_trace(go.Scatter(x=df.index, y=df[col_n], name=lbl, line=dict(color=color, width=1.3)), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["rsi_14"], name="RSI", line=dict(color="#a371f7", width=1.5)), row=2, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(248,81,73,0.06)",  line_width=0, row=2, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(63,185,80,0.06)",  line_width=0, row=2, col=1)
    fig.add_hline(y=70, line=dict(color="#f85149", dash="dot", width=1), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="#3fb950", dash="dot", width=1), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["macd"],        name="MACD",   line=dict(color="#58a6ff",width=1.3)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"], name="Signal", line=dict(color="#f0a500",width=1.3)), row=3, col=1)
    hist_c = ["rgba(63,185,80,0.7)" if v >= 0 else "rgba(248,81,73,0.7)" for v in df["macd_hist"].fillna(0)]
    fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"], name="Hist", marker_color=hist_c, showlegend=False), row=3, col=1)

    _GRID = dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)")
    fig.update_layout(
        height=700, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(22,27,42,0.6)",
        font=dict(family="Inter", color="#8b949e", size=11),
        margin=dict(l=0,r=0,t=28,b=0), xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(13,17,28,0.8)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1),
        yaxis= dict(**_GRID, side="right"),
        yaxis2=dict(**_GRID, side="right", range=[0,100]),
        yaxis3=dict(**_GRID, side="right"),
    )
    for i in range(1,4):
        fig.update_xaxes(**_GRID, row=i, col=1)

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Signal Dashboard ──────────────────────────────────────
    with st.expander("📡 Technical Signals", expanded=True):
        if signals:
            _SC = {"BULLISH":"#3fb950","BEARISH":"#f85149","NEUTRAL":"#d29922"}
            sig_cols = st.columns(len(signals))
            for col, (name, val) in zip(sig_cols, signals.items()):
                c = _SC.get(val,"#8b949e")
                col.markdown(f"""
                <div style="background:rgba(22,27,42,0.8);border:1px solid {c}30;border-radius:10px;padding:12px;text-align:center;">
                    <div style="font-size:10px;color:#8b949e;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">{name}</div>
                    <div style="font-size:13px;font-weight:600;color:{c};">{'🟢' if val=='BULLISH' else '🔴' if val=='BEARISH' else '🟡'} {val}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── AI Analysis ───────────────────────────────────────────
    if run_ai:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <span style="font-size:18px;">🤖</span>
            <h3 style="color:#e6edf3!important;font-size:15px!important;margin:0;">Claude AI Analysis</h3>
            <span style="font-size:11px;color:#8b949e;background:rgba(56,139,253,0.1);padding:2px 8px;border-radius:20px;border:1px solid rgba(56,139,253,0.2);">Streaming</span>
        </div>
        """, unsafe_allow_html=True)
        from core.exceptions import LLMError, LLMRateLimitError
        with st.spinner("Generating analysis with Claude…"):
            try:
                msgs = claude_client.build_analysis_prompt(
                    ticker=ticker, info=info.__dict__,
                    signals=signals, signal_summary=bias, period=period,
                )
                with st.container():
                    st.markdown('<div style="background:rgba(22,27,42,0.6);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:20px;">', unsafe_allow_html=True)
                    st.write_stream(claude_client.stream(msgs))
                    st.markdown("</div>", unsafe_allow_html=True)
            except LLMRateLimitError as exc:
                st.warning(f"⚠️ Claude API rate limit. {exc}")
            except LLMError as exc:
                st.error(f"AI analysis failed: {exc}")


# ══════════════════════════════════════════════════════════════
# PAGE: DOCUMENT Q&A
# ══════════════════════════════════════════════════════════════
elif st.session_state.page == "docs":
    import tempfile
    from core.exceptions import (
        DocumentLoadError, DocumentParseError,
        IndexNotFoundError, FinSightError, LLMError,
    )

    rag    = _get_rag_pipeline()
    claude = _get_claude_client()

    if "doc_messages" not in st.session_state:
        st.session_state.doc_messages = []

    st.markdown('<h1 style="margin-bottom:4px;">📄 Document Q&A</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e;margin-bottom:24px;">Upload SEC filings or earnings transcripts — ask questions grounded in the actual text.</p>', unsafe_allow_html=True)

    col_up, col_qa = st.columns([1, 2], gap="large")

    with col_up:
        st.markdown('<p style="font-size:11px;color:#484f58;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">📁 Upload Document</p>', unsafe_allow_html=True)
        uploaded = st.file_uploader("", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")

        if uploaded:
            for file in uploaded:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(file.read())
                    tmp_path = tmp.name
                with st.spinner(f"Indexing **{file.name}**…"):
                    try:
                        n = rag.ingest(tmp_path)
                        st.success(f"✅ {file.name} · {n} chunks indexed")
                    except DocumentParseError as exc:
                        st.error(f"Parse failed: {exc}")
                    except DocumentLoadError as exc:
                        st.error(f"Load failed: {exc}")
                    except FinSightError as exc:
                        st.error(str(exc))

        docs = rag.list_documents()
        if docs:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p style="font-size:11px;color:#484f58;letter-spacing:0.08em;text-transform:uppercase;">📚 Indexed</p>', unsafe_allow_html=True)
            for d in docs:
                st.markdown(f'<div style="background:rgba(35,134,54,0.08);border:1px solid rgba(35,134,54,0.2);border-radius:8px;padding:8px 12px;margin-bottom:6px;font-size:12px;color:#3fb950;">📄 {d}</div>', unsafe_allow_html=True)
            if st.button("🗑️ Clear Index", use_container_width=True):
                rag.clear()
                st.session_state.doc_messages = []
                st.rerun()

    with col_qa:
        st.markdown('<p style="font-size:11px;color:#484f58;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:12px;">💬 Ask a Question</p>', unsafe_allow_html=True)

        if not docs:
            st.markdown("""
            <div style="background:rgba(22,27,42,0.5);border:1px dashed rgba(255,255,255,0.1);border-radius:14px;padding:40px;text-align:center;">
                <div style="font-size:32px;margin-bottom:12px;">📄</div>
                <p style="color:#8b949e;margin:0;">Upload a PDF to start asking questions</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in st.session_state.doc_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            query = st.chat_input("e.g. What are the key risk factors? What was revenue growth?")
            if query:
                st.session_state.doc_messages.append({"role":"user","content":query})
                with st.chat_message("user"):
                    st.markdown(query)
                with st.chat_message("assistant"):
                    try:
                        ctx  = rag.retrieve(query)
                        resp = st.write_stream(claude.stream([{"role":"user","content":query}], extra_context=ctx))
                        st.session_state.doc_messages.append({"role":"assistant","content":resp})
                    except IndexNotFoundError:
                        st.error("No documents indexed. Upload a PDF first.")
                    except LLMError as exc:
                        st.error(f"AI error: {exc}")
                    except FinSightError as exc:
                        st.error(str(exc))


# ══════════════════════════════════════════════════════════════
# PAGE: AI CHAT
# ══════════════════════════════════════════════════════════════
elif st.session_state.page == "chat":
    from core.exceptions import LLMError, LLMRateLimitError

    claude = _get_claude_client()

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:#484f58;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px;">💡 Quick Prompts</p>', unsafe_allow_html=True)
        _SUGGESTIONS = [
            "Explain P/E vs EV/EBITDA",
            "What is an inverted yield curve?",
            "How to read a cash flow statement?",
            "Growth vs value investing",
            "What is dollar-cost averaging?",
        ]
        for s in _SUGGESTIONS:
            if st.button(f"→ {s}", key=f"sug_{hash(s)}", use_container_width=True):
                st.session_state.chat_messages.append({"role":"user","content":s})
                st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()

    st.markdown('<h1 style="margin-bottom:4px;">💬 AI Financial Chat</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e;margin-bottom:20px;">Conversational financial intelligence powered by Claude.</p>', unsafe_allow_html=True)

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
        with st.chat_message("user"):
            st.markdown(user_input)

        api_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages]
        with st.chat_message("assistant"):
            try:
                full = st.write_stream(claude.stream(api_msgs))
                st.session_state.chat_messages.append({"role":"assistant","content":full})
            except LLMRateLimitError as exc:
                st.warning(f"⚠️ Rate limited: {exc}")
            except LLMError as exc:
                st.error(f"Error: {exc}")
