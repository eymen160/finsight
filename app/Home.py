"""
FinSight — Home
================
Entry point for the Streamlit multi-page app.
Run with: streamlit run app/Home.py
"""

import streamlit as st

from config.settings import settings

st.set_page_config(
    page_title=settings.app_title,
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"## 📈 {settings.app_title}")
    st.caption(f"v{settings.app_version} · {settings.app_env.value}")
    st.divider()
    st.markdown(
        "**Pages**\n"
        "- 📊 Stock Analysis\n"
        "- 📄 Document Q&A\n"
        "- 💬 AI Chat\n"
    )
    st.divider()
    st.caption(
        "⚠️ FinSight is for informational purposes only. "
        "Nothing here constitutes investment advice."
    )

# ── Hero ──────────────────────────────────────────────────────
st.title("📈 FinSight")
st.subheader("AI-Powered Financial Analysis")

st.markdown(
    """
    Welcome to **FinSight** — your intelligent financial research assistant.
    Use the sidebar to navigate between features.
    """
)

col1, col2, col3 = st.columns(3)

with col1:
    st.info(
        "### 📊 Stock Analysis\n"
        "Technical indicators, fundamental metrics, "
        "and AI-generated analysis for any ticker."
    )

with col2:
    st.info(
        "### 📄 Document Q&A\n"
        "Upload 10-K, 10-Q, or earnings transcripts "
        "and ask questions grounded in the text."
    )

with col3:
    st.info(
        "### 💬 AI Chat\n"
        "Conversational financial assistant powered "
        "by Claude. Ask anything about markets."
    )
