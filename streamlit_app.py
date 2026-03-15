"""
FinSight — Home Page
=====================
Streamlit Cloud: Main file path = streamlit_app.py
Navigation is handled automatically by Streamlit's native
multi-page system (pages/ directory).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from config.settings import settings

st.set_page_config(
    page_title="FinSight · AI Financial Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 FinSight")
    st.caption(f"v{settings.app_version}")
    st.divider()
    st.caption("⚠️ For informational purposes only. Not investment advice.")

# ── Hero ─────────────────────────────────────────────────────
st.title("📈 FinSight")
st.subheader("AI-Powered Financial Analysis")
st.markdown(
    "Welcome to **FinSight** — your intelligent financial research assistant. "
    "**Use the sidebar on the left to navigate between pages.**"
)
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.info(
        "**📊 Stock Analysis**\n\n"
        "Technical indicators (RSI, MACD, Bollinger Bands), "
        "fundamental metrics, and AI-generated analysis for any ticker.\n\n"
        "👈 Click **1 Stock Analysis** in the sidebar"
    )

with col2:
    st.info(
        "**📄 Document Q&A**\n\n"
        "Upload 10-K, 10-Q, or earnings transcripts "
        "and ask questions grounded in the text via RAG.\n\n"
        "👈 Click **2 Document QA** in the sidebar"
    )

with col3:
    st.info(
        "**💬 AI Chat**\n\n"
        "Conversational financial assistant powered "
        "by Claude. Ask anything about markets, stocks, or finance.\n\n"
        "👈 Click **3 Chat** in the sidebar"
    )
