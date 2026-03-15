"""
FinSight — Production Streamlit App
Bloomberg Terminal × Stripe Design System
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

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

# ══════════════════════════════════════════════════════════════
# DESIGN SYSTEM — Bloomberg Terminal × Stripe 2026
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;1,14..32,400&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; }

/* ── Root background + mesh gradient ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #05080f !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: #e2e8f0 !important;
}
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background:
        radial-gradient(ellipse 900px 600px at 15% 0%,   rgba(56,139,253,0.06) 0%, transparent 70%),
        radial-gradient(ellipse 700px 500px at 85% 100%, rgba(63,185,80,0.04)  0%, transparent 70%),
        radial-gradient(ellipse 600px 800px at 50% 50%,  rgba(110,64,201,0.03) 0%, transparent 70%);
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(8,11,20,0.98) !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
    backdrop-filter: blur(24px) !important;
}
[data-testid="stSidebar"] > div { padding-top: 0 !important; }

/* ── Sidebar buttons (nav) ── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    color: #64748b !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 9px 12px !important;
    text-align: left !important;
    width: 100% !important;
    margin-bottom: 2px !important;
    transition: all 0.15s ease !important;
    letter-spacing: 0.01em !important;
    box-shadow: none !important;
    transform: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(56,139,253,0.08) !important;
    border-color: rgba(56,139,253,0.2) !important;
    color: #94a3b8 !important;
    transform: none !important;
    box-shadow: none !important;
}
.nav-active [data-testid="stSidebar"] .stButton > button,
.nav-active .stButton > button {
    background: rgba(56,139,253,0.12) !important;
    border-color: rgba(56,139,253,0.35) !important;
    color: #60a5fa !important;
}

/* ── Main action buttons ── */
.stButton > button {
    background: rgba(56,139,253,0.1) !important;
    border: 1px solid rgba(56,139,253,0.25) !important;
    border-radius: 8px !important;
    color: #60a5fa !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.02em !important;
    padding: 9px 18px !important;
    transition: all 0.15s ease !important;
    box-shadow: 0 0 0 0 rgba(56,139,253,0) !important;
}
.stButton > button:hover {
    background: rgba(56,139,253,0.18) !important;
    border-color: rgba(56,139,253,0.5) !important;
    box-shadow: 0 0 16px rgba(56,139,253,0.15) !important;
    transform: none !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: rgba(12,16,28,0.9) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
    padding: 14px 16px !important;
    position: relative !important;
    overflow: hidden !important;
}
[data-testid="stMetric"]::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(56,139,253,0.4), transparent);
}
[data-testid="stMetricLabel"] {
    color: #475569 !important;
    font-size: 10px !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-size: 20px !important;
    font-weight: 600 !important;
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: -0.02em !important;
}

/* ── Inputs ── */
[data-testid="stTextInput"] > div > div,
[data-testid="stSelectbox"] > div > div {
    background: rgba(12,16,28,0.8) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}
[data-testid="stTextInput"] > div > div:focus-within {
    border-color: rgba(56,139,253,0.5) !important;
    box-shadow: 0 0 0 3px rgba(56,139,253,0.1) !important;
}

/* ── Chat ── */
[data-testid="stChatMessage"] {
    background: rgba(12,16,28,0.7) !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 10px !important;
    margin-bottom: 6px !important;
}
[data-testid="stChatInput"] > div {
    background: rgba(12,16,28,0.95) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: rgba(56,139,253,0.4) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(12,16,28,0.7) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
    color: #64748b !important;
    font-size: 12px !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [data-testid="stTab"] {
    background: transparent !important;
    border-bottom: 2px solid transparent !important;
    color: #64748b !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    padding: 8px 16px !important;
    border-radius: 0 !important;
    transition: all 0.15s !important;
}
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {
    color: #60a5fa !important;
    border-bottom-color: #3b82f6 !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid rgba(255,255,255,0.06) !important;
    gap: 4px !important;
}

/* ── Alerts ── */
[data-testid="stAlert"]   { background: rgba(12,16,28,0.8) !important; border-radius: 8px !important; }
[data-testid="stSuccess"] { background: rgba(34,197,94,0.08)  !important; border: 1px solid rgba(34,197,94,0.2)  !important; border-radius: 8px !important; }
[data-testid="stError"]   { background: rgba(239,68,68,0.08)  !important; border: 1px solid rgba(239,68,68,0.2)  !important; border-radius: 8px !important; }
[data-testid="stWarning"] { background: rgba(234,179,8,0.08)  !important; border: 1px solid rgba(234,179,8,0.2)  !important; border-radius: 8px !important; }

/* ── Toggle ── */
[data-testid="stToggle"] label { color: #64748b !important; font-size: 12px !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: rgba(12,16,28,0.6) !important;
    border: 1px dashed rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    padding: 12px !important;
}

/* ── Plotly container ── */
.js-plotly-plot { border-radius: 10px !important; }
.stPlotlyChart { border-radius: 10px !important; overflow: hidden !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] > div { border-top-color: #3b82f6 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }

/* ── Divider ── */
hr { border: none !important; border-top: 1px solid rgba(255,255,255,0.05) !important; margin: 20px 0 !important; }

/* ── Typography ── */
h1, h2, h3 { font-family: 'Inter', sans-serif !important; letter-spacing: -0.02em !important; }
p, li, .stMarkdown p { color: #94a3b8 !important; line-height: 1.65 !important; font-size: 14px !important; }
code, .stMarkdown code {
    font-family: 'JetBrains Mono', monospace !important;
    background: rgba(56,139,253,0.1) !important;
    color: #93c5fd !important;
    padding: 1px 6px !important;
    border-radius: 4px !important;
    font-size: 12px !important;
}

/* ── Status bar ── */
.status-bar {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 12px;
    background: rgba(12,16,28,0.8);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 6px;
    font-size: 11px; color: #475569;
    font-family: 'JetBrains Mono', monospace;
}
.status-dot { width: 6px; height: 6px; border-radius: 50%; animation: pulse 2s infinite; }
.status-dot.green  { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
.status-dot.yellow { background: #eab308; box-shadow: 0 0 6px #eab308; }
.status-dot.red    { background: #ef4444; box-shadow: 0 0 6px #ef4444; }
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ── Bento card ── */
.bento {
    background: rgba(12,16,28,0.85);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 20px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.bento:hover { border-color: rgba(56,139,253,0.2); }
.bento-accent {
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, var(--accent-start), var(--accent-end));
}

/* ── Signal badge ── */
.signal-badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.04em;
    font-family: 'JetBrains Mono', monospace;
}
.signal-bullish { background: rgba(34,197,94,0.1);  border: 1px solid rgba(34,197,94,0.3);  color: #4ade80; }
.signal-bearish { background: rgba(239,68,68,0.1);  border: 1px solid rgba(239,68,68,0.3);  color: #f87171; }
.signal-neutral { background: rgba(234,179,8,0.1);  border: 1px solid rgba(234,179,8,0.3);  color: #fbbf24; }
.signal-mixed   { background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.3); color: #c4b5fd; }

/* ── Stat chip ── */
.stat-chip {
    background: rgba(12,16,28,0.9);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px; padding: 10px 14px;
    font-family: 'JetBrains Mono', monospace;
}
.stat-chip .label { font-size: 10px; color: #475569; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 4px; }
.stat-chip .value { font-size: 16px; color: #f1f5f9; font-weight: 600; }

/* ── Ticker header ── */
.ticker-header {
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
    padding: 16px 0; border-bottom: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 20px;
}
.ticker-name { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.02em; }
.ticker-sym  { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #475569;
               background: rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 5px; }
.ticker-tag  { font-size: 11px; color: #94a3b8; background: rgba(255,255,255,0.04);
               padding: 3px 10px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.08); }

/* ── Section header ── */
.section-header {
    display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
    padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.04);
}
.section-header .icon { font-size: 14px; }
.section-header .title {
    font-size: 11px; font-weight: 600; color: #475569;
    letter-spacing: 0.08em; text-transform: uppercase;
}
.section-header .badge {
    margin-left: auto; font-size: 10px; color: #3b82f6;
    background: rgba(59,130,246,0.1); padding: 2px 8px;
    border-radius: 20px; border: 1px solid rgba(59,130,246,0.2);
    font-family: 'JetBrains Mono', monospace;
}

/* ── AI panel ── */
.ai-panel {
    background: rgba(12,16,28,0.7);
    border: 1px solid rgba(56,139,253,0.15);
    border-radius: 10px; padding: 20px;
    position: relative; overflow: hidden;
}
.ai-panel::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(56,139,253,0.5), transparent);
}

/* ── Doc list item ── */
.doc-item {
    display: flex; align-items: center; gap: 8px;
    background: rgba(34,197,94,0.05); border: 1px solid rgba(34,197,94,0.15);
    border-radius: 7px; padding: 8px 12px; margin-bottom: 5px;
    font-size: 12px; color: #4ade80;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Empty state ── */
.empty-state {
    text-align: center; padding: 48px 20px;
    background: rgba(12,16,28,0.5);
    border: 1px dashed rgba(255,255,255,0.07);
    border-radius: 12px;
}
.empty-state .icon { font-size: 36px; margin-bottom: 12px; opacity: 0.5; }
.empty-state .title { font-size: 15px; font-weight: 600; color: #475569; margin-bottom: 6px; }
.empty-state .sub   { font-size: 13px; color: #334155; }

/* ── Remove Streamlit branding ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* ── Main content padding ── */
[data-testid="stMain"] > div { padding-top: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# CACHED RESOURCE FACTORIES
# ══════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════
# NAVIGATION STATE
# ══════════════════════════════════════════════════════════════
if "page" not in st.session_state:
    st.session_state.page = "home"

def _goto(p: str) -> None:
    st.session_state.page = p
    st.rerun()


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    # Logo + wordmark
    st.markdown("""
    <div style="padding:20px 16px 16px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
            <div style="width:28px;height:28px;background:linear-gradient(135deg,#1d4ed8,#3b82f6);
                        border-radius:7px;display:flex;align-items:center;justify-content:center;
                        font-size:14px;flex-shrink:0;">📈</div>
            <div>
                <div style="font-size:15px;font-weight:700;color:#f1f5f9;letter-spacing:-0.02em;line-height:1;">FinSight</div>
                <div style="font-size:10px;color:#334155;letter-spacing:0.06em;text-transform:uppercase;margin-top:2px;">AI Financial Intelligence</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="padding:0 8px;">', unsafe_allow_html=True)
    st.markdown('<p style="font-size:10px;color:#1e293b;letter-spacing:0.08em;text-transform:uppercase;padding:4px 4px 6px;font-weight:600;">Navigation</p>', unsafe_allow_html=True)

    _NAV = [("home","🏠","Home"),("stock","📊","Stock Analysis"),("docs","📄","Document Q&A"),("chat","💬","AI Chat")]
    for key, icon, label in _NAV:
        active = st.session_state.page == key
        css = "nav-active" if active else ""
        st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
        if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
            _goto(key)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # System status
    st.markdown("""
    <div style="padding:0 8px 12px;">
        <div class="status-bar">
            <div class="status-dot green"></div>
            <span>Markets · NYSE/NASDAQ</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Disclaimer
    st.markdown("""
    <div style="margin:0 8px 16px;padding:10px 12px;background:rgba(239,68,68,0.05);
                border:1px solid rgba(239,68,68,0.12);border-radius:8px;">
        <p style="font-size:10px;color:#475569;margin:0;line-height:1.5;">
            ⚠️ <strong style="color:#64748b;">Disclaimer</strong> — Informational only.
            Not investment advice. Always consult a qualified financial professional.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════
if st.session_state.page == "home":
    # Hero
    st.markdown("""
    <div style="padding:8px 0 32px;">
        <div style="display:inline-flex;align-items:center;gap:6px;padding:4px 12px;
                    background:rgba(56,139,253,0.08);border:1px solid rgba(56,139,253,0.2);
                    border-radius:20px;font-size:11px;color:#60a5fa;margin-bottom:16px;
                    font-family:'JetBrains Mono',monospace;letter-spacing:0.04em;">
            ● LIVE  ·  Claude AI  ·  v0.1.0
        </div>
        <h1 style="font-size:2.4rem;font-weight:700;color:#f1f5f9;line-height:1.15;margin-bottom:12px;letter-spacing:-0.03em;">
            Institutional-grade<br>financial intelligence
        </h1>
        <p style="font-size:15px;color:#64748b;max-width:500px;line-height:1.7;margin:0;">
            Real-time stock analysis, SEC document Q&A via RAG,
            and conversational finance — powered by Claude AI.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Feature cards — bento grid
    c1, c2, c3 = st.columns(3, gap="small")

    _CARDS = [
        ("stock","📊","Stock Analysis",
         "Candlestick charts, RSI, MACD, Bollinger Bands, SMA 20/50/200. Real-time fundamentals with streaming AI analysis.",
         "#1d4ed8","#3b82f6","Open Analysis"),
        ("docs","📄","Document Q&A",
         "Upload 10-K, 10-Q, or earnings transcripts. Ask questions grounded in the exact text via FAISS vector search.",
         "#15803d","#22c55e","Open Q&A"),
        ("chat","💬","AI Chat",
         "Conversational financial assistant. Ask about markets, valuation methods, macro trends, or explain any concept.",
         "#6d28d9","#8b5cf6","Open Chat"),
    ]

    for col, (page, icon, title, desc, c_start, c_end, btn) in zip([c1,c2,c3], _CARDS):
        with col:
            st.markdown(f"""
            <div class="bento" style="--accent-start:{c_start};--accent-end:{c_end};min-height:180px;">
                <div class="bento-accent"></div>
                <div style="font-size:22px;margin-bottom:12px;">{icon}</div>
                <div style="font-size:14px;font-weight:600;color:#e2e8f0;margin-bottom:8px;letter-spacing:-0.01em;">{title}</div>
                <div style="font-size:12px;color:#475569;line-height:1.6;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(btn, key=f"h_{page}", use_container_width=True):
                _goto(page)

    st.markdown("<br>", unsafe_allow_html=True)

    # Stats row
    st.markdown("""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
        <div class="stat-chip">
            <div class="label">Indicators</div>
            <div class="value">15+</div>
        </div>
        <div class="stat-chip">
            <div class="label">AI Engine</div>
            <div class="value">Claude</div>
        </div>
        <div class="stat-chip">
            <div class="label">Vector DB</div>
            <div class="value">FAISS</div>
        </div>
        <div class="stat-chip">
            <div class="label">Data</div>
            <div class="value">Yahoo Finance</div>
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

    # Sidebar controls
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="padding:0 8px;">
            <div class="section-header">
                <span class="icon">⚙️</span>
                <span class="title">Analysis Settings</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div style="padding:0 4px;">', unsafe_allow_html=True)
        ticker = st.text_input(
            "Ticker",
            value="AAPL",
            max_chars=10,
            help="Enter any NYSE/NASDAQ/global ticker (e.g. AAPL, MSFT, TSLA, BTC-USD)",
            placeholder="e.g. AAPL",
        ).upper().strip()
        period = st.selectbox(
            "Time Period",
            ["1mo","3mo","6mo","1y","2y","5y"],
            index=3,
            help="Historical price range for chart and technical indicators",
        )
        run_ai = st.toggle(
            "AI Analysis",
            value=True,
            help="Stream a Claude-powered analysis using current data and signals",
        )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⟳  Refresh Data", use_container_width=True,
                     help="Clear cache and re-fetch from Yahoo Finance"):
            stock_client.clear_cache()
            st.rerun()

    # Page header
    st.markdown("""
    <div class="section-header" style="margin-bottom:20px;">
        <span class="icon">📊</span>
        <span class="title">Stock Analysis</span>
    </div>
    """, unsafe_allow_html=True)

    if not ticker:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">📊</div>
            <div class="title">No ticker entered</div>
            <div class="sub">Type a symbol in the sidebar to begin analysis</div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # Data fetch
    with st.spinner(f"Fetching {ticker} from Yahoo Finance…"):
        try:
            info   = stock_client.get_info(ticker)
            df_raw = stock_client.get_history(ticker, period=period)
        except RateLimitError:
            st.warning(
                "**Yahoo Finance Rate Limit** — Streamlit Cloud shares IPs with thousands of apps.\n\n"
                "✅ **What to do:** Wait 30–60 seconds, then click ⟳ Refresh Data in the sidebar. "
                "Data is cached for 10 minutes once fetched."
            )
            st.stop()
        except TickerNotFoundError:
            st.error(
                f"**'{ticker}' not found** — Double-check the symbol. "
                "Try `AAPL`, `MSFT`, `BTC-USD`, or `^GSPC` for the S&P 500."
            )
            st.stop()
        except FinSightError as exc:
            st.error(f"**Data error:** {exc}")
            st.stop()

    df      = add_indicators(df_raw)
    signals = get_signals(df)
    bias    = signal_summary(signals)

    # ── Ticker header ─────────────────────────────────────────
    _bias_class = {"BULLISH":"signal-bullish","BEARISH":"signal-bearish","MIXED":"signal-mixed","NEUTRAL":"signal-neutral"}.get(bias,"signal-neutral")
    _bias_dot   = {"BULLISH":"●","BEARISH":"●","MIXED":"◐","NEUTRAL":"○"}.get(bias,"○")

    st.markdown(f"""
    <div class="ticker-header">
        <span class="ticker-name">{info.name}</span>
        <span class="ticker-sym">{ticker}</span>
        <span class="ticker-tag">{info.sector}</span>
        <span class="ticker-tag">{info.industry}</span>
        <span class="signal-badge {_bias_class}" style="margin-left:auto;">{_bias_dot} {bias}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Key metrics ───────────────────────────────────────────
    def _fmt_cap(v: float | int | None) -> str:
        if v is None: return "—"
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9:  return f"${v/1e9:.2f}B"
        if v >= 1e6:  return f"${v/1e6:.2f}M"
        return f"${v:,.0f}"

    def _fmt_price(v: float | None) -> str:
        return f"${v:,.2f}" if v is not None else "—"

    def _fmt_ratio(v: float | None, suffix: str = "x") -> str:
        return f"{v:.2f}{suffix}" if v is not None else "—"

    mc = st.columns(6, gap="small")
    mc[0].metric("Price",      _fmt_price(info.current_price),
                 help="Most recent market price (real-time or prior close)")
    mc[1].metric("52W High",   _fmt_price(info.fifty_two_week_high))
    mc[2].metric("52W Low",    _fmt_price(info.fifty_two_week_low))
    mc[3].metric("P/E (TTM)",  _fmt_ratio(info.pe_ratio),
                 help="Trailing 12-month price-to-earnings ratio")
    mc[4].metric("Fwd P/E",    _fmt_ratio(info.forward_pe),
                 help="Forward P/E based on next 12 months' consensus EPS estimate")
    mc[5].metric("Market Cap", _fmt_cap(info.market_cap))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Chart via tabs ────────────────────────────────────────
    chart_tab, fund_tab = st.tabs(["📈  PRICE & INDICATORS", "📋  FUNDAMENTALS"])

    with chart_tab:
        close = df["Close"].squeeze()

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            row_heights=[0.58, 0.22, 0.20],
            vertical_spacing=0.015,
            subplot_titles=("", "", ""),
        )

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"].squeeze(), high=df["High"].squeeze(),
            low=df["Low"].squeeze(),   close=close,
            name="OHLC",
            increasing=dict(line=dict(color="#22c55e", width=1), fillcolor="rgba(34,197,94,0.75)"),
            decreasing=dict(line=dict(color="#ef4444", width=1), fillcolor="rgba(239,68,68,0.75)"),
            showlegend=False,
            hovertemplate=(
                "<b>%{x|%b %d, %Y}</b><br>"
                "Open:  $%{open:,.2f}<br>"
                "High:  $%{high:,.2f}<br>"
                "Low:   $%{low:,.2f}<br>"
                "Close: $%{close:,.2f}<extra></extra>"
            ),
        ), row=1, col=1)

        # Bollinger Bands
        fig.add_trace(go.Scatter(
            x=df.index, y=df["bb_upper"],
            line=dict(color="rgba(96,165,250,0.25)", width=1, dash="dot"),
            name="BB Upper", showlegend=False,
            hovertemplate="BB Upper: $%{y:,.2f}<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["bb_lower"],
            line=dict(color="rgba(96,165,250,0.25)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(96,165,250,0.04)",
            name="BB", showlegend=False,
            hovertemplate="BB Lower: $%{y:,.2f}<extra></extra>",
        ), row=1, col=1)

        # SMAs
        _smas = [("sma_20","#f59e0b","SMA 20"),("sma_50","#60a5fa","SMA 50"),("sma_200","#f87171","SMA 200")]
        for col_n, color, lbl in _smas:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_n], name=lbl,
                line=dict(color=color, width=1.5),
                hovertemplate=f"{lbl}: $%{{y:,.2f}}<extra></extra>",
            ), row=1, col=1)

        # Volume bars (mini, row 1 overlay — skip, too cluttered)
        # RSI
        fig.add_trace(go.Scatter(
            x=df.index, y=df["rsi_14"], name="RSI",
            line=dict(color="#a78bfa", width=1.5),
            fill="tozeroy", fillcolor="rgba(167,139,250,0.04)",
            hovertemplate="RSI: %{y:.1f}<extra></extra>",
        ), row=2, col=1)
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.05)",  line_width=0, row=2, col=1)
        fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(34,197,94,0.05)",  line_width=0, row=2, col=1)
        fig.add_hline(y=70, line=dict(color="#ef4444", dash="dot", width=0.8), row=2, col=1)
        fig.add_hline(y=30, line=dict(color="#22c55e", dash="dot", width=0.8), row=2, col=1)

        # MACD
        fig.add_trace(go.Scatter(
            x=df.index, y=df["macd"],        name="MACD",
            line=dict(color="#60a5fa", width=1.4),
            hovertemplate="MACD: %{y:.3f}<extra></extra>",
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["macd_signal"], name="Signal",
            line=dict(color="#f59e0b", width=1.4),
            hovertemplate="Signal: %{y:.3f}<extra></extra>",
        ), row=3, col=1)
        hist_vals = df["macd_hist"].fillna(0)
        hist_c = ["rgba(34,197,94,0.6)" if v >= 0 else "rgba(239,68,68,0.6)" for v in hist_vals]
        fig.add_trace(go.Bar(
            x=df.index, y=hist_vals, name="Hist",
            marker_color=hist_c, showlegend=False,
            hovertemplate="Hist: %{y:.3f}<extra></extra>",
        ), row=3, col=1)

        # Layout
        _grid = dict(showgrid=True, gridcolor="rgba(255,255,255,0.03)", gridwidth=1, zeroline=False)
        fig.update_layout(
            height=640,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor ="rgba(8,12,20,0.6)",
            font=dict(family="Inter", color="#475569", size=10),
            margin=dict(l=0, r=60, t=12, b=0),
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="rgba(8,11,20,0.95)",
                bordercolor="rgba(255,255,255,0.1)",
                font=dict(color="#e2e8f0", size=11, family="JetBrains Mono"),
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.01,
                xanchor="right", x=1,
                bgcolor="rgba(8,11,20,0.8)",
                bordercolor="rgba(255,255,255,0.08)", borderwidth=1,
                font=dict(size=10),
            ),
            yaxis= dict(**_grid, side="right", tickprefix="$", tickformat=",.0f"),
            yaxis2=dict(**_grid, side="right", range=[0,100], ticksuffix=""),
            yaxis3=dict(**_grid, side="right"),
        )
        for i in range(1,4):
            fig.update_xaxes(**_grid, row=i, col=1, showticklabels=(i==3))

        # Annotations for RSI bands
        fig.add_annotation(x=df.index[5], y=70, text="OB", row=2, col=1,
            showarrow=False, font=dict(size=9, color="#ef4444"), xanchor="left")
        fig.add_annotation(x=df.index[5], y=30, text="OS", row=2, col=1,
            showarrow=False, font=dict(size=9, color="#22c55e"), xanchor="left")

        st.plotly_chart(fig, use_container_width=True, config={
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["lasso2d","select2d","autoScale2d"],
            "displaylogo": False,
            "toImageButtonOptions": {"format":"svg","filename":f"finsight_{ticker}"},
        })

    with fund_tab:
        f1, f2, f3 = st.columns(3, gap="small")
        _fund_items = [
            ("Trailing EPS",   f"${info.eps:.2f}"                  if info.eps             else "—"),
            ("Dividend Yield", f"{info.dividend_yield*100:.2f}%"   if info.dividend_yield  else "—"),
            ("P/E (TTM)",      _fmt_ratio(info.pe_ratio)),
            ("Forward P/E",    _fmt_ratio(info.forward_pe)),
            ("Market Cap",     _fmt_cap(info.market_cap)),
            ("Currency",       info.currency),
        ]
        for col, (label, value) in zip([f1,f2,f3,f1,f2,f3], _fund_items):
            col.markdown(f"""
            <div class="stat-chip" style="margin-bottom:8px;">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Technical Signal Dashboard ────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📡  TECHNICAL SIGNALS", expanded=True):
        if signals:
            _SC = {"BULLISH":"signal-bullish","BEARISH":"signal-bearish","NEUTRAL":"signal-neutral"}
            sig_cols = st.columns(len(signals), gap="small")
            for col, (name, val) in zip(sig_cols, signals.items()):
                cls = _SC.get(val, "signal-neutral")
                dot = "●" if val in ("BULLISH","BEARISH") else "○"
                col.markdown(f"""
                <div style="text-align:center;padding:12px 6px;background:rgba(8,12,20,0.6);
                            border:1px solid rgba(255,255,255,0.05);border-radius:8px;">
                    <div style="font-size:9px;color:#334155;letter-spacing:0.1em;
                                text-transform:uppercase;margin-bottom:8px;font-weight:600;">{name}</div>
                    <span class="signal-badge {cls}">{dot} {val}</span>
                </div>
                """, unsafe_allow_html=True)

    # ── AI Analysis ───────────────────────────────────────────
    if run_ai:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="section-header">
            <span class="icon">🤖</span>
            <span class="title">Claude AI Analysis</span>
            <span class="badge">Streaming · claude-sonnet-4-6</span>
        </div>
        """, unsafe_allow_html=True)

        from core.exceptions import LLMError, LLMRateLimitError

        with st.spinner("Generating analysis…"):
            try:
                msgs = claude_client.build_analysis_prompt(
                    ticker=ticker, info=info.__dict__,
                    signals=signals, signal_summary=bias, period=period,
                )
                st.markdown('<div class="ai-panel">', unsafe_allow_html=True)
                st.write_stream(claude_client.stream(msgs))
                st.markdown("</div>", unsafe_allow_html=True)
            except LLMRateLimitError:
                st.warning("⚠️ Claude API rate limit reached. Wait ~60 seconds and refresh.")
            except LLMError as exc:
                st.error(
                    f"**AI analysis unavailable** — {exc}\n\n"
                    "Check your `ANTHROPIC_API_KEY` in Streamlit Cloud Secrets."
                )


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

    st.markdown("""
    <div class="section-header" style="margin-bottom:4px;">
        <span class="icon">📄</span>
        <span class="title">Document Q&A</span>
        <span class="badge">RAG · FAISS Vector Search</span>
    </div>
    <p style="font-size:13px;color:#334155;margin-bottom:20px;">
        Upload SEC filings, earnings transcripts, or annual reports.
        Ask questions grounded in the exact document text.
    </p>
    """, unsafe_allow_html=True)

    col_up, col_qa = st.columns([5, 8], gap="large")

    # ── Upload panel ──────────────────────────────────────────
    with col_up:
        st.markdown("""
        <div class="section-header">
            <span class="icon">📁</span>
            <span class="title">Upload Document</span>
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "",
            type=["pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            help="Upload PDF financial documents. Max ~10 MB per file.",
        )

        if uploaded:
            for file in uploaded:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(file.read())
                    tmp_path = tmp.name
                with st.spinner(f"Indexing {file.name}…"):
                    try:
                        n = rag.ingest(tmp_path)
                        st.success(f"✅ **{file.name}** — {n} chunks indexed")
                    except DocumentParseError:
                        st.error(
                            f"⚠️ **{file.name}** appears to be a scanned image PDF with no text layer. "
                            "Please use a text-searchable PDF."
                        )
                    except DocumentLoadError as exc:
                        st.error(f"❌ Cannot read **{file.name}**: {exc.reason}")
                    except FinSightError as exc:
                        st.error(str(exc))

        # Indexed documents list
        docs = rag.list_documents()
        if docs:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div class="section-header">
                <span class="icon">📚</span>
                <span class="title">Indexed Documents</span>
            </div>
            """, unsafe_allow_html=True)
            for d in docs:
                st.markdown(f'<div class="doc-item">📄 {d}</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️  Clear All Documents", use_container_width=True):
                rag.clear()
                st.session_state.doc_messages = []
                st.success("Index cleared.")
                st.rerun()
        else:
            st.markdown("""
            <div style="padding:16px;background:rgba(8,12,20,0.5);border:1px dashed rgba(255,255,255,0.06);
                        border-radius:8px;margin-top:12px;">
                <p style="font-size:12px;color:#1e293b;margin:0;line-height:1.6;">
                    📋 <strong style="color:#334155;">Tips:</strong><br>
                    • Use text-layer PDFs (not scanned)<br>
                    • 10-K and 10-Q filings work great<br>
                    • Earnings call transcripts supported
                </p>
            </div>
            """, unsafe_allow_html=True)

    # ── Q&A panel ─────────────────────────────────────────────
    with col_qa:
        st.markdown("""
        <div class="section-header">
            <span class="icon">💬</span>
            <span class="title">Ask Questions</span>
        </div>
        """, unsafe_allow_html=True)

        if not docs:
            st.markdown("""
            <div class="empty-state">
                <div class="icon">📄</div>
                <div class="title">No documents indexed</div>
                <div class="sub">Upload a PDF on the left to start asking questions about it</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Suggested questions
            with st.expander("💡  Suggested questions", expanded=False):
                _suggestions = [
                    "What are the primary risk factors disclosed?",
                    "Summarise the revenue growth over the reported period.",
                    "What is the company's cash position and liquidity?",
                    "What are management's key strategic priorities?",
                    "Were there any material legal proceedings disclosed?",
                ]
                for s in _suggestions:
                    if st.button(f"→ {s}", key=f"sug_doc_{hash(s)}", use_container_width=True):
                        st.session_state.doc_messages.append({"role":"user","content":s})
                        st.rerun()

            # Chat history
            for msg in st.session_state.doc_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            query = st.chat_input(
                "Ask about the document…",
                key="doc_chat_input",
            )
            if query:
                st.session_state.doc_messages.append({"role":"user","content":query})
                with st.chat_message("user"):
                    st.markdown(query)
                with st.chat_message("assistant"):
                    try:
                        ctx  = rag.retrieve(query)
                        resp = st.write_stream(
                            claude.stream([{"role":"user","content":query}], extra_context=ctx)
                        )
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

    # Sidebar quick prompts
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="padding:0 8px;">
            <div class="section-header">
                <span class="icon">💡</span>
                <span class="title">Quick Prompts</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        _prompts = [
            "Explain P/E vs EV/EBITDA",
            "What signals an inverted yield curve?",
            "How to read a cash flow statement?",
            "Growth vs value investing — key differences",
            "What is dollar-cost averaging?",
            "Explain the Fed funds rate impact on equities",
        ]
        st.markdown('<div style="padding:0 4px;">', unsafe_allow_html=True)
        for p in _prompts:
            if st.button(f"→ {p}", key=f"qp_{hash(p)}", use_container_width=True):
                st.session_state.chat_messages.append({"role":"user","content":p})
                st.rerun()
        st.markdown("</div><br>", unsafe_allow_html=True)
        if st.button("🗑️  Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()

    # Page header
    st.markdown("""
    <div class="section-header" style="margin-bottom:4px;">
        <span class="icon">💬</span>
        <span class="title">AI Financial Chat</span>
        <span class="badge">claude-sonnet-4-6</span>
    </div>
    <p style="font-size:13px;color:#334155;margin-bottom:20px;">
        Ask anything about markets, investment strategies, financial concepts, or economic theory.
    </p>
    """, unsafe_allow_html=True)

    # Empty state
    if not st.session_state.chat_messages:
        st.markdown("""
        <div class="empty-state" style="margin-bottom:20px;">
            <div class="icon">💬</div>
            <div class="title">Start a conversation</div>
            <div class="sub">Use the quick prompts in the sidebar or type your own question below</div>
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

        api_msgs = [{"role":m["role"],"content":m["content"]} for m in st.session_state.chat_messages]
        with st.chat_message("assistant"):
            try:
                full = st.write_stream(claude.stream(api_msgs))
                st.session_state.chat_messages.append({"role":"assistant","content":full})
            except LLMRateLimitError:
                st.warning("⚠️ Claude API rate limited. Wait ~60 seconds and try again.")
            except LLMError as exc:
                st.error(
                    f"**Claude unavailable** — {exc}\n\n"
                    "Check `ANTHROPIC_API_KEY` in Streamlit Cloud Secrets."
                )
