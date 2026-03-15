"""
FinSight — Claude API Client
==============================
Single-responsibility wrapper around the Anthropic SDK.
Provides:
  - Synchronous completion (used by analysis pipelines)
  - Streaming completion (used by Streamlit chat UI)
  - Automatic retry with exponential back-off (via tenacity)
  - Consistent system prompt injection
  - Token usage logging

Usage:
    from core.llm.claude_client import ClaudeClient
    client = ClaudeClient()
    response = client.complete(messages=[{"role": "user", "content": "Explain P/E ratio"}])
"""

from collections.abc import Generator
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import settings
from core.exceptions import ContextWindowExceededError, LLMError
from core.logger import get_logger

logger = get_logger(__name__)

# ── System prompt ─────────────────────────────────────────────
_SYSTEM_PROMPT = """You are FinSight, an expert AI financial analyst assistant.

Your capabilities:
- Technical and fundamental stock analysis
- Interpreting SEC filings (10-K, 10-Q, earnings transcripts)
- Explaining financial metrics clearly for both novice and experienced investors
- Identifying key risks and opportunities from data

Your principles:
- Always ground claims in the data provided; do not fabricate figures
- Clearly distinguish between analysis and opinion
- Include appropriate risk disclaimers when discussing investment decisions
- Be concise but thorough — prefer structured responses with clear sections

You do NOT provide personalised investment advice or tell users to buy/sell specific securities."""


class ClaudeClient:
    """
    Thin, stateless wrapper around anthropic.Anthropic.
    Instantiate once and reuse across the app.
    """

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.api_key)
        self._model  = settings.claude_model
        logger.info("claude_client_initialised", model=self._model)

    # ── Internal helpers ──────────────────────────────────────

    @retry(
        retry=retry_if_exception_type(anthropic.RateLimitError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _create_message(self, messages: list[dict], **kwargs) -> anthropic.types.Message:
        return self._client.messages.create(
            model=self._model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            system=_SYSTEM_PROMPT,
            messages=messages,
            **kwargs,
        )

    # ── Public API ────────────────────────────────────────────

    def complete(
        self,
        messages: list[dict[str, str]],
        extra_context: str | None = None,
    ) -> str:
        """
        Non-streaming completion.

        Args:
            messages:      OpenAI-style message list (role/content dicts).
            extra_context: Optional context string prepended to the last
                           user message (used by RAG pipeline).

        Returns:
            The assistant's reply as a plain string.

        Raises:
            LLMError: on non-retryable API errors.
            ContextWindowExceededError: if prompt exceeds model limits.
        """
        if extra_context:
            messages = _inject_context(messages, extra_context)

        logger.info("llm_request", n_messages=len(messages))
        try:
            response = self._create_message(messages)
        except anthropic.BadRequestError as exc:
            if "prompt is too long" in str(exc).lower():
                raise ContextWindowExceededError(str(exc)) from exc
            raise LLMError(str(exc)) from exc
        except anthropic.APIError as exc:
            raise LLMError(str(exc)) from exc

        usage = response.usage
        logger.info(
            "llm_response",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
        return response.content[0].text

    def stream(
        self,
        messages: list[dict[str, str]],
        extra_context: str | None = None,
    ) -> Generator[str, None, None]:
        """
        Streaming completion — yields text chunks as they arrive.

        Designed for use with Streamlit's `st.write_stream`.

        Example:
            for chunk in client.stream(messages):
                st.write(chunk)
        """
        if extra_context:
            messages = _inject_context(messages, extra_context)

        logger.info("llm_stream_start", n_messages=len(messages))
        try:
            with self._client.messages.stream(
                model=self._model,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                system=_SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except anthropic.APIError as exc:
            raise LLMError(str(exc)) from exc

    def build_analysis_prompt(
        self,
        ticker: str,
        info: dict[str, Any],
        signals: dict[str, str],
        signal_summary: str,
        period: str,
    ) -> list[dict[str, str]]:
        """
        Construct a structured message list for stock analysis.
        Kept here so prompt logic is co-located with the client.
        """
        fundamentals = {
            k: info.get(k)
            for k in [
                "name", "sector", "industry", "market_cap",
                "pe_ratio", "forward_pe", "eps", "dividend_yield",
                "fifty_two_week_high", "fifty_two_week_low", "current_price",
            ]
        }
        prompt = (
            f"Analyse {ticker} based on the following data.\n\n"
            f"**Fundamentals:**\n{_dict_to_md(fundamentals)}\n\n"
            f"**Technical Signals ({period}):**\n{_dict_to_md(signals)}\n"
            f"Overall bias: **{signal_summary}**\n\n"
            "Please provide:\n"
            "1. Brief company overview\n"
            "2. Fundamental analysis (valuation, profitability)\n"
            "3. Technical analysis (trend, momentum, key levels)\n"
            "4. Key risks to monitor\n"
            "5. Summary in 2–3 sentences\n\n"
            "_Remember to include a risk disclaimer._"
        )
        return [{"role": "user", "content": prompt}]


# ── Utilities ─────────────────────────────────────────────────

def _inject_context(
    messages: list[dict[str, str]],
    context: str,
) -> list[dict[str, str]]:
    """Prepend RAG context to the last user message."""
    messages = list(messages)  # shallow copy
    last = messages[-1]
    if last["role"] == "user":
        messages[-1] = {
            "role": "user",
            "content": (
                f"**Relevant context from documents:**\n{context}\n\n"
                f"---\n\n{last['content']}"
            ),
        }
    return messages


def _dict_to_md(d: dict[str, Any]) -> str:
    lines = []
    for k, v in d.items():
        label = k.replace("_", " ").title()
        lines.append(f"- **{label}:** {v if v is not None else 'N/A'}")
    return "\n".join(lines)
