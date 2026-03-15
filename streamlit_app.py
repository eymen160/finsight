"""
FinSight — Streamlit Cloud Entrypoint
======================================
Main file path on Streamlit Cloud: streamlit_app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from config.settings import settings

st.set_page_config(
    page_title=settings.app_title,
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.markdown(f"## 📈 {settings.app_title}")
    st.caption(f"v{settings.app_version}")
    st.divider()
    st.markdown("**Navigate**")
    if st.button("📊 Stock Analysis", use_container_width=True):
        st.switch_page("pages/1_Stock_Analysis.py")
    if st.button("📄 Document Q&A", use_container_width=True):
        st.switch_page("pages/2_Document_QA.py")
    if st.button("💬 AI Chat", use_container_width=True):
        st.switch_page("pages/3_Chat.py")
    st.divider()
    st.caption("⚠️ For informational purposes only. Not investment advice.")

# ── Hero ─────────────────────────────────────────────────────
st.title("📈 FinSight")
st.subheader("AI-Powered Financial Analysis")
st.markdown(
    "Welcome to **FinSight** — your intelligent financial research assistant. "
    "Use the sidebar or the buttons below to navigate."
)
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.info(
        "**📊 Stock Analysis**\n\n"
        "Technical indicators, fundamental metrics, "
        "and AI-generated analysis for any ticker."
    )
    if st.button("Open Stock Analysis →", key="btn_stock", use_container_width=True):
        st.switch_page("pages/1_Stock_Analysis.py")

with col2:
    st.info(
        "**📄 Document Q&A**\n\n"
        "Upload 10-K, 10-Q, or earnings transcripts "
        "and ask questions grounded in the text."
    )
    if st.button("Open Document Q&A →", key="btn_doc", use_container_width=True):
        st.switch_page("pages/2_Document_QA.py")

with col3:
    st.info(
        "**💬 AI Chat**\n\n"
        "Conversational financial assistant powered "
        "by Claude. Ask anything about markets."
    )
    if st.button("Open AI Chat →", key="btn_chat", use_container_width=True):
        st.switch_page("pages/3_Chat.py")
