"""
FinSight — Stock Analysis Page
================================
Fetches data, computes indicators, renders charts,
and runs a Claude analysis — all in one Streamlit page.
"""

import sys
from pathlib import Path

# Allow imports from project root when running as a page
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.analysis.technical import add_indicators, get_signals, signal_summary
from core.data.stock_client import StockClient
from core.exceptions import FinSightError
from core.llm.claude_client import ClaudeClient

st.set_page_config(page_title="Stock Analysis · FinSight", page_icon="📊", layout="wide")

# ── Session-state singletons (instantiated once per session) ──
if "stock_client" not in st.session_state:
    st.session_state.stock_client = StockClient()
if "claude_client" not in st.session_state:
    st.session_state.claude_client = ClaudeClient()

stock_client: StockClient = st.session_state.stock_client
claude_client: ClaudeClient = st.session_state.claude_client

# ── UI ────────────────────────────────────────────────────────
st.title("📊 Stock Analysis")

with st.sidebar:
    st.markdown("### Settings")
    ticker = st.text_input("Ticker Symbol", value="AAPL", max_chars=10).upper().strip()
    period = st.selectbox(
        "Time Period",
        options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=3,
    )
    run_ai = st.toggle("AI Analysis", value=True)
    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        stock_client.clear_cache()
        st.rerun()

if not ticker:
    st.info("Enter a ticker symbol in the sidebar to get started.")
    st.stop()

# ── Data fetch ────────────────────────────────────────────────
with st.spinner(f"Fetching data for **{ticker}**…"):
    try:
        info = stock_client.get_info(ticker)
        df_raw = stock_client.get_history(ticker, period=period)
    except FinSightError as exc:
        st.error(str(exc))
        st.stop()

df = add_indicators(df_raw)
signals = get_signals(df)
bias = signal_summary(signals)

# ── Header metrics ────────────────────────────────────────────
st.markdown(f"## {info.name} `{ticker}`")
st.caption(f"{info.sector} · {info.industry}")

col_price, col_high, col_low, col_pe, col_mktcap, col_bias = st.columns(6)

def _fmt_large(val: int | float | None) -> str:
    if val is None:
        return "N/A"
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.2f}B"
    if val >= 1e6:
        return f"${val/1e6:.2f}M"
    return f"${val:,.0f}"

col_price.metric("Price", f"${info.current_price:,.2f}" if info.current_price else "N/A")
col_high.metric("52W High", f"${info.fifty_two_week_high:,.2f}" if info.fifty_two_week_high else "N/A")
col_low.metric("52W Low", f"${info.fifty_two_week_low:,.2f}" if info.fifty_two_week_low else "N/A")
col_pe.metric("P/E (TTM)", f"{info.pe_ratio:.1f}" if info.pe_ratio else "N/A")
col_mktcap.metric("Market Cap", _fmt_large(info.market_cap))

bias_color = {"BULLISH": "🟢", "BEARISH": "🔴", "MIXED": "🟡", "NEUTRAL": "⚪"}.get(bias, "⚪")
col_bias.metric("Signal Bias", f"{bias_color} {bias}")

st.divider()

# ── Charts ────────────────────────────────────────────────────
close = df["Close"].squeeze()

fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    row_heights=[0.55, 0.25, 0.20],
    vertical_spacing=0.03,
    subplot_titles=("Price & Moving Averages", "RSI (14)", "MACD"),
)

# Candlestick
fig.add_trace(
    go.Candlestick(
        x=df.index, open=df["Open"].squeeze(),
        high=df["High"].squeeze(), low=df["Low"].squeeze(),
        close=close, name="OHLC", showlegend=False,
    ),
    row=1, col=1,
)

# Bollinger Bands
fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], name="BB Upper",
    line=dict(color="rgba(173,216,230,0.5)", width=1), showlegend=False), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], name="BB Lower",
    line=dict(color="rgba(173,216,230,0.5)", width=1),
    fill="tonexty", fillcolor="rgba(173,216,230,0.1)", showlegend=False), row=1, col=1)

# SMAs
for sma, color in [("sma_20","#f39c12"), ("sma_50","#3498db"), ("sma_200","#e74c3c")]:
    fig.add_trace(go.Scatter(x=df.index, y=df[sma],
        name=sma.upper().replace("_", " "), line=dict(color=color, width=1.2)), row=1, col=1)

# RSI
fig.add_trace(go.Scatter(x=df.index, y=df["rsi_14"], name="RSI",
    line=dict(color="#9b59b6", width=1.5)), row=2, col=1)
fig.add_hline(y=70, line_color="red",   line_dash="dash", row=2, col=1)
fig.add_hline(y=30, line_color="green", line_dash="dash", row=2, col=1)

# MACD
fig.add_trace(go.Scatter(x=df.index, y=df["macd"], name="MACD",
    line=dict(color="#3498db", width=1.2)), row=3, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"], name="Signal",
    line=dict(color="#e74c3c", width=1.2)), row=3, col=1)
fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"], name="Histogram",
    marker_color=df["macd_hist"].apply(lambda v: "#2ecc71" if v >= 0 else "#e74c3c")),
    row=3, col=1)

fig.update_layout(
    height=680,
    template="plotly_dark",
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
)
fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
fig.update_yaxes(title_text="RSI",  row=2, col=1)
fig.update_yaxes(title_text="MACD", row=3, col=1)

st.plotly_chart(fig, use_container_width=True)

# ── Signal table ──────────────────────────────────────────────
with st.expander("📡 Technical Signals", expanded=True):
    cols = st.columns(len(signals))
    emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡", "MIXED": "🟡"}
    for col, (name, val) in zip(cols, signals.items()):
        col.metric(name, f"{emoji.get(val, '')} {val}")

# ── AI Analysis ───────────────────────────────────────────────
if run_ai:
    st.divider()
    st.markdown("### 🤖 AI Analysis")
    with st.spinner("Generating analysis with Claude…"):
        try:
            messages = claude_client.build_analysis_prompt(
                ticker=ticker,
                info=info.__dict__,
                signals=signals,
                signal_summary=bias,
                period=period,
            )
            st.write_stream(claude_client.stream(messages))
        except FinSightError as exc:
            st.error(f"AI analysis failed: {exc}")
