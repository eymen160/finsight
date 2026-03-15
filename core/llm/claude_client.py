"""
FinSight — Claude API Client
================================
Stateless wrapper around the Anthropic Messages API.

Responsibilities (Single Responsibility Principle):
- Own all prompt engineering (system prompt + templates).
- Handle API retries, rate limits, and streaming.
- Inject RAG context without polluting call sites.
- Raise typed LLM exceptions — never bare anthropic SDK errors.

Usage::

    from core.llm.claude_client import ClaudeClient
    client = ClaudeClient()
    for chunk in client.stream([{"role": "user", "content": "Explain DCF"}]):
        print(chunk, end="", flush=True)
"""
from __future__ import annotations

import logging
import time
from collections.abc import Generator
from typing import Any

import anthropic

from config.settings import settings
from core.exceptions import (
    ContextWindowExceededError,
    LLMError,
    LLMRateLimitError,
)

log = logging.getLogger(__name__)

# ── System Prompt ─────────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are FinSight, a senior AI financial analyst assistant.

## Capabilities
- Technical analysis: price action, momentum indicators, chart patterns.
- Fundamental analysis: valuation multiples, profitability, balance-sheet health.
- Document analysis: SEC filings, earnings transcripts, research reports.
- Financial education: clear explanations for retail and institutional audiences.

## Strict Rules
1. Ground every claim in the data provided. Do not fabricate prices, ratios, or dates.
2. If data is insufficient, say so explicitly rather than guessing.
3. Distinguish analysis from opinion: use "the data suggests" or "one interpretation is."
4. Format responses with clear Markdown headings and bullet points.
5. Append a one-sentence risk disclaimer to any analysis that could influence investment decisions.
6. Never recommend specific buy, sell, or hold actions on individual securities.\
"""

MessageList = list[dict[str, str]]


# ── Prompt builders ───────────────────────────────────────────

def _build_analysis_prompt(
    ticker: str,
    fundamentals: dict[str, Any],
    signals: dict[str, str],
    bias: str,
    period: str,
) -> str:
    def _fmt(v: Any) -> str:
        if v is None: return "N/A"
        if isinstance(v, float): return f"{v:,.2f}"
        if isinstance(v, int) and v > 1_000_000:
            if v >= 1e12: return f"${v/1e12:.2f}T"
            if v >= 1e9:  return f"${v/1e9:.2f}B"
            return f"${v/1e6:.2f}M"
        return str(v)

    fund_md = "\n".join(
        f"- **{k.replace('_', ' ').title()}:** {_fmt(v)}"
        for k, v in fundamentals.items()
    )
    sig_md = "\n".join(f"- **{k}:** {v}" for k, v in signals.items())

    return (
        f"Analyse **{ticker}** using the data provided below.\n\n"
        f"### Fundamental Data\n{fund_md}\n\n"
        f"### Technical Signals ({period})\n{sig_md}\n"
        f"**Aggregate Bias:** {bias}\n\n"
        "### Required Output Structure\n"
        "1. **Company Overview** — one paragraph.\n"
        "2. **Fundamental Analysis** — valuation vs. sector peers, red flags.\n"
        "3. **Technical Analysis** — trend, momentum, key price levels.\n"
        "4. **Key Risks** — 3–5 bullet points.\n"
        "5. **Summary** — 2–3 sentences.\n"
        "6. **Risk Disclaimer** — one sentence.\n\n"
        "_Use only the data above. Note any N/A metrics explicitly._"
    )


def _inject_context(messages: MessageList, context: str) -> MessageList:
    """Prepend RAG context to the last user turn (non-mutating)."""
    msgs = list(messages)
    if msgs and msgs[-1].get("role") == "user":
        msgs[-1] = {
            "role": "user",
            "content": (
                "## Retrieved Context (ground your answer in this)\n\n"
                f"{context}\n\n---\n\n"
                f"## Question\n\n{msgs[-1]['content']}"
            ),
        }
    return msgs


# ── Client ────────────────────────────────────────────────────

class ClaudeClient:
    """Stateless Anthropic Messages API wrapper with retry and streaming.

    Thread-safe. Instantiate once per process via @st.cache_resource.

    Args:
        api_key: Override ``settings.api_key``.
        model:   Override ``settings.claude_model``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model:   str | None = None,
    ) -> None:
        self._client = anthropic.Anthropic(api_key=api_key or settings.api_key)
        self._model  = model or settings.claude_model
        log.info("claude_client_init model=%s", self._model)

    def _base_kwargs(self, messages: MessageList) -> dict[str, Any]:
        """Build the base kwargs dict for both create and stream calls."""
        return dict(
            model      = self._model,
            max_tokens = settings.max_tokens,
            system     = _SYSTEM_PROMPT,
            messages   = messages,
            # temperature omitted intentionally — defaults to model's optimal value
            # Passing temperature=0.2 can cause issues on newer model versions
        )

    def _create_with_retry(self, messages: MessageList) -> anthropic.types.Message:
        """Non-streaming completion with exponential-backoff retry.

        Raises:
            LLMRateLimitError, ContextWindowExceededError, LLMError.
        """
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                return self._client.messages.create(**self._base_kwargs(messages))

            except anthropic.RateLimitError as exc:
                if attempt == max_attempts:
                    raise LLMRateLimitError() from exc
                wait = 2 ** attempt
                log.warning("llm_rate_limit attempt=%d wait=%ds", attempt, wait)
                time.sleep(wait)

            except anthropic.BadRequestError as exc:
                if "prompt is too long" in str(exc).lower():
                    raise ContextWindowExceededError() from exc
                raise LLMError(str(exc), status_code=400) from exc

            except anthropic.APIStatusError as exc:
                raise LLMError(str(exc), status_code=exc.status_code) from exc

            except anthropic.APIConnectionError as exc:
                raise LLMError(f"Connection error: {exc}") from exc

        raise LLMError("All retry attempts exhausted")  # pragma: no cover

    def complete(
        self,
        messages: MessageList,
        extra_context: str | None = None,
    ) -> str:
        """Non-streaming completion.

        Args:
            messages:      Conversation history.
            extra_context: RAG context prepended to last user turn.

        Returns:
            Assistant's full response as plain string.
        """
        if extra_context:
            messages = _inject_context(messages, extra_context)
        log.info("llm_complete n=%d", len(messages))
        resp = self._create_with_retry(messages)
        log.info("llm_ok in=%d out=%d", resp.usage.input_tokens, resp.usage.output_tokens)
        return resp.content[0].text

    def stream(
        self,
        messages: MessageList,
        extra_context: str | None = None,
    ) -> Generator[str, None, None]:
        """Streaming completion — yields text chunks for ``st.write_stream``.

        Uses ``messages.create(stream=True)`` which is the most compatible
        approach across all SDK versions (0.20+ through current).

        Args:
            messages:      Conversation history.
            extra_context: RAG context prepended to last user turn.

        Yields:
            Incremental text strings.

        Raises:
            LLMRateLimitError, ContextWindowExceededError, LLMError.
        """
        if extra_context:
            messages = _inject_context(messages, extra_context)

        log.info("llm_stream_start n=%d", len(messages))

        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                kwargs = self._base_kwargs(messages)
                kwargs["stream"] = True

                with self._client.messages.create(**kwargs) as stream:
                    for event in stream:
                        # Handle both old SDK (MessageStreamEvent) and new SDK
                        event_type = getattr(event, "type", None)
                        if event_type == "content_block_delta":
                            delta = getattr(event, "delta", None)
                            if delta and getattr(delta, "type", None) == "text_delta":
                                text = getattr(delta, "text", "")
                                if text:
                                    yield text
                return  # success

            except anthropic.RateLimitError as exc:
                if attempt == max_attempts:
                    raise LLMRateLimitError() from exc
                wait = 2 ** attempt
                log.warning("llm_stream_rate_limit attempt=%d wait=%ds", attempt, wait)
                time.sleep(wait)

            except anthropic.BadRequestError as exc:
                if "prompt is too long" in str(exc).lower():
                    raise ContextWindowExceededError() from exc
                raise LLMError(str(exc), status_code=400) from exc

            except anthropic.APIStatusError as exc:
                raise LLMError(str(exc), status_code=exc.status_code) from exc

            except anthropic.APIConnectionError as exc:
                raise LLMError(f"Connection error: {exc}") from exc

            except Exception as exc:
                raise LLMError(f"Unexpected streaming error: {exc}") from exc

    def build_analysis_prompt(
        self,
        ticker: str,
        info: dict[str, Any],
        signals: dict[str, str],
        signal_summary: str,
        period: str,
    ) -> MessageList:
        """Build stock-analysis MessageList for :meth:`stream`."""
        fundamentals = {
            k: info.get(k)
            for k in (
                "name", "sector", "industry", "market_cap",
                "pe_ratio", "forward_pe", "eps", "dividend_yield",
                "fifty_two_week_high", "fifty_two_week_low", "current_price",
            )
        }
        return [{
            "role": "user",
            "content": _build_analysis_prompt(
                ticker=ticker,
                fundamentals=fundamentals,
                signals=signals,
                bias=signal_summary,
                period=period,
            ),
        }]
