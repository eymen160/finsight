"""
FinSight — Streamlit Cloud Entrypoint
======================================
This IS the main page. Pages live in /pages/ at the repo root.
Streamlit Cloud deploy setting:
  Main file path: streamlit_app.py
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
    st.page_link("streamlit_app.py",         label="🏠 Home",            icon="🏠")
    st.page_link("pages/1_Stock_Analysis.py", label="Stock Analysis",    icon="📊")
    st.page_link("pages/2_Document_QA.py",    label="Document Q&A",      icon="📄")
    st.page_link("pages/3_Chat.py",           label="AI Chat",           icon="💬")
    st.divider()
    st.caption(
        "⚠️ For informational purposes only. "
        "Not investment advice."
    )

st.title("📈 FinSight")
st.subheader("AI-Powered Financial Analysis")
st.markdown(
    "Welcome to **FinSight** — your intelligent financial research assistant. "
    "Use the sidebar to navigate between features."
)

col1, col2, col3 = st.columns(3)

with col1:
    st.info(
        "**📊 Stock Analysis**\n\n"
        "Technical indicators, fundamental metrics, "
        "and AI-generated analysis for any ticker."
    )
    st.page_link("pages/1_Stock_Analysis.py", label="Open Stock Analysis →", icon="📊")

with col2:
    st.info(
        "**📄 Document Q&A**\n\n"
        "Upload 10-K, 10-Q, or earnings transcripts "
        "and ask questions grounded in the text."
    )
    st.page_link("pages/2_Document_QA.py", label="Open Document Q&A →", icon="📄")

with col3:
    st.info(
        "**💬 AI Chat**\n\n"
        "Conversational financial assistant powered "
        "by Claude. Ask anything about markets."
    )
    st.page_link("pages/3_Chat.py", label="Open AI Chat →", icon="💬")
