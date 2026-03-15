"""
FinSight — AI Chat Page
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from core.exceptions import FinSightError
from core.llm.claude_client import ClaudeClient

st.set_page_config(page_title="AI Chat · FinSight", page_icon="💬", layout="wide")

with st.sidebar:
    st.markdown("## 📈 FinSight")
    st.divider()
    st.markdown("**Suggested questions:**")
    st.caption("- Explain P/E vs P/S ratios\n- What does an inverted yield curve signal?\n- How do I read a cash flow statement?\n- What are key risks in growth investing?")
    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.chat_messages = []
        st.rerun()
    st.caption("⚠️ Not investment advice.")

if "claude_client" not in st.session_state:
    st.session_state.claude_client = ClaudeClient()
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

claude = st.session_state.claude_client

st.title("💬 AI Financial Chat")
st.caption("Ask anything about markets, stocks, economic concepts, or financial theory.")

for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask FinSight…")
if user_input:
    st.session_state.chat_messages.append({"role":"user","content":user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    api_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_messages
    ]
    with st.chat_message("assistant"):
        try:
            full = st.write_stream(claude.stream(api_messages))
            st.session_state.chat_messages.append({"role":"assistant","content":full})
        except FinSightError as exc:
            st.error(f"Error: {exc}")
