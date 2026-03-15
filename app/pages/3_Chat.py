"""
FinSight — AI Chat Page
========================
Free-form conversational interface with Claude.
Full conversation history is maintained in session state.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from core.exceptions import FinSightError
from core.llm.claude_client import ClaudeClient

st.set_page_config(page_title="AI Chat · FinSight", page_icon="💬", layout="wide")

if "claude_client" not in st.session_state:
    st.session_state.claude_client = ClaudeClient()
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

claude: ClaudeClient = st.session_state.claude_client

# ── UI ────────────────────────────────────────────────────────
st.title("💬 AI Financial Chat")
st.caption("Ask anything about markets, stocks, economic concepts, or financial theory.")

with st.sidebar:
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.chat_messages = []
        st.rerun()
    st.divider()
    st.markdown(
        "**Suggested questions:**\n"
        "- Explain the difference between P/E and P/S ratios\n"
        "- What does an inverted yield curve signal?\n"
        "- How do I read a cash flow statement?\n"
        "- What are the key risks of growth investing in 2026?\n"
    )

# Render history
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input
user_input = st.chat_input("Ask FinSight…")

if user_input:
    st.session_state.chat_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build message list (full history for multi-turn context)
    api_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_messages
    ]

    with st.chat_message("assistant"):
        try:
            full_response = st.write_stream(claude.stream(api_messages))
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": full_response}
            )
        except FinSightError as exc:
            st.error(f"Error: {exc}")
