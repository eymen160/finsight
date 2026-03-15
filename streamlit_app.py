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
    st.info("### 📊 Stock Analysis\nTechnical indicators, fundamental metrics, and AI-generated analysis for any ticker.")
with col2:
    st.info("### 📄 Document Q&A\nUpload 10-K, 10-Q, or earnings transcripts and ask questions grounded in the text.")
with col3:
    st.info("### 💬 AI Chat\nConversational financial assistant powered by Claude. Ask anything about markets.")
