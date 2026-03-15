"""
FinSight — Document Q&A Page
==============================
Upload financial PDFs and ask questions grounded in the text.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from core.exceptions import FinSightError
from core.llm.claude_client import ClaudeClient
from core.rag.pipeline import RAGPipeline

st.set_page_config(page_title="Document Q&A · FinSight", page_icon="📄", layout="wide")

# ── Singletons ────────────────────────────────────────────────
if "rag_pipeline" not in st.session_state:
    st.session_state.rag_pipeline = RAGPipeline()
if "claude_client" not in st.session_state:
    st.session_state.claude_client = ClaudeClient()

rag: RAGPipeline = st.session_state.rag_pipeline
claude: ClaudeClient = st.session_state.claude_client

# ── UI ────────────────────────────────────────────────────────
st.title("📄 Document Q&A")
st.caption("Upload 10-K, 10-Q, or earnings transcripts and ask questions grounded in the text.")

col_upload, col_qa = st.columns([1, 2], gap="large")

# ── Upload panel ──────────────────────────────────────────────
with col_upload:
    st.markdown("### 📁 Documents")

    uploaded = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        accept_multiple_files=True,
        help="Supported: SEC filings, earnings transcripts, annual reports",
    )

    if uploaded:
        for file in uploaded:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file.read())
                tmp_path = tmp.name

            with st.spinner(f"Indexing **{file.name}**…"):
                try:
                    n_chunks = rag.ingest(tmp_path)
                    st.success(f"✅ {file.name} — {n_chunks} chunks indexed")
                except FinSightError as exc:
                    st.error(str(exc))

    st.divider()
    st.markdown("**Indexed documents:**")
    docs = rag.list_documents()
    if docs:
        for d in docs:
            st.markdown(f"- 📄 {d}")
    else:
        st.caption("No documents indexed yet.")

# ── Q&A panel ─────────────────────────────────────────────────
with col_qa:
    st.markdown("### 💬 Ask a Question")

    # Chat history
    if "doc_messages" not in st.session_state:
        st.session_state.doc_messages = []

    for msg in st.session_state.doc_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    query = st.chat_input("e.g. What are the main risk factors in this 10-K?")

    if query:
        st.session_state.doc_messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            try:
                context = rag.retrieve(query)
                messages = [{"role": "user", "content": query}]
                response = st.write_stream(claude.stream(messages, extra_context=context))
                st.session_state.doc_messages.append(
                    {"role": "assistant", "content": response}
                )
            except FinSightError as exc:
                st.error(str(exc))
