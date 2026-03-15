"""
FinSight — Claude API Client
================================
Single-responsibility wrapper around the Anthropic Python SDK.

Responsibilities:
- Construct and validate Messages API requests.
- Retry on transient rate-limit errors with exponential back-off.
- Inject RAG context into the user turn without polluting call sites.
- Build structured stock-analysis prompts with grounding instructions
  to minimise hallucination.

This module owns the system prompt and all prompt engineering.
UI layers call :meth:`ClaudeClient.stream` or :meth:`ClaudeClient.complete`
and never construct raw API payloads themselves.

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

# ── System prompt ─────────────────────────────────────────────
# Grounding instructions are included explicitly to reduce hallucination.
# The phrase "do not fabricate" is more reliable than "don't make up".

_SYSTEM_PROMPT = """\
You are FinSight, a senior AI financial analyst.

## Capabilities
- Technical analysis: interpret price action, momentum indicators, and chart patterns.
- Fundamental analysis: evaluate valuation multiples, profitability, and balance-sheet health.
- Document analysis: extract insights from SEC filings, earnings transcripts, and research reports.
- Financial education: explain complex concepts clearly for both retail and institutional audiences.

## Strict Rules
1. **Ground every claim in the data provided.** Do not fabricate prices, ratios, or dates.
2. If the provided data is insufficient to answer, say so explicitly rather than guessing.
3. Distinguish analysis from opinion: use phrases like "the data suggests" or "one interpretation is."
4. Always append a one-sentence risk disclaimer to analysis that could influence investment decisions.
5. Never recommend specific buy, sell, or hold actions on individual securities.
6. Format responses with clear Markdown headings and bullet points for readability.\
"""

# ── Prompt templates ──────────────────────────────────────────

def _build_stock_analysis_prompt(
    ticker: str,
    fundamentals: dict[str, Any],
    signals: dict[str, str],
    bias: str,
    period: str,
) -> str:
    """Construct the stock analysis user message.

    Args:
        ticker:       Ticker symbol.
        fundamentals: Dict of fundamental metrics from :class:`~core.data.stock_client.StockInfo`.
        signals:      Technical signals from :func:`~core.analysis.technical.get_signals`.
        bias:         Overall signal bias from :func:`~core.analysis.technical.signal_summary`.
        period:       The time period of the price history (e.g. ``"1y"``).

    Returns:
        A formatted string suitable for the ``"user"`` role in the Messages API.
    """
    def _fmt(v: Any) -> str:
        if v is None:
            return "N/A"
        if isinstance(v, float):
            return f"{v:,.2f}"
        if isinstance(v, int) and v > 1_000_000:
            if v >= 1e12: return f"${v/1e12:.2f}T"
            if v >= 1e9:  return f"${v/1e9:.2f}B"
            if v >= 1e6:  return f"${v/1e6:.2f}M"
        return str(v)

    fund_lines = "\n".join(
        f"- **{k.replace('_', ' ').title()}:** {_fmt(v)}"
        for k, v in fundamentals.items()
    )
    sig_lines = "\n".join(
        f"- **{k}:** {v}" for k, v in signals.items()
    )

    return (
        f"Please analyse **{ticker}** using the data below.\n\n"
        f"### Fundamental Data\n{fund_lines}\n\n"
        f"### Technical Signals ({period} period)\n{sig_lines}\n"
        f"**Aggregate Bias:** {bias}\n\n"
        "### Required Output Structure\n"
        "1. **Company Overview** — one paragraph max.\n"
        "2. **Fundamental Analysis** — valuation vs. sector peers, red flags.\n"
        "3. **Technical Analysis** — trend direction, momentum, key price levels.\n"
        "4. **Key Risks** — 3–5 bullet points.\n"
        "5. **Summary** — 2–3 sentences.\n"
        "6. **Risk Disclaimer** — one sentence.\n\n"
        "_Use only the data provided above. If a metric is N/A, note its absence._"
    )


# ── Client ────────────────────────────────────────────────────

MessageList = list[dict[str, str]]


class ClaudeClient:
    """Stateless wrapper around the Anthropic Messages API.

    Designed to be instantiated once per Streamlit session and stored
    in ``st.session_state``.  All methods are synchronous and thread-safe
    (the underlying ``httpx`` client handles connection pooling).

    Args:
        api_key: Anthropic API key.  Defaults to ``settings.api_key``.
        model:   Claude model identifier.  Defaults to ``settings.claude_model``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model:   str | None = None,
    ) -> None:
        resolved_key = api_key or settings.api_key
        self._client = anthropic.Anthropic(api_key=resolved_key)
        self._model  = model or settings.claude_model
        log.info("claude_client_init model=%s", self._model)

    # ── Internal helpers ──────────────────────────────────────

    def _create_with_retry(
        self,
        messages: MessageList,
        stream: bool = False,
    ) -> Any:
        """Call the Messages API with exponential-backoff retry on 429s.

        Args:
            messages: Conversation history in OpenAI-compatible format.
            stream:   If ``True``, return a streaming context manager.

        Returns:
            An :class:`anthropic.types.Message` (non-stream) or a
            streaming context manager (stream=True).

        Raises:
            LLMRateLimitError:         After exhausting retries on 429.
            ContextWindowExceededError: On ``invalid_request_error`` with
                                        "prompt is too long" in the message.
            LLMError:                  For all other API failures.
        """
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                kwargs: dict[str, Any] = dict(
                    model      = self._model,
                    max_tokens = settings.max_tokens,
                    temperature= settings.temperature,
                    system     = _SYSTEM_PROMPT,
                    messages   = messages,
                )
                if stream:
                    return self._client.messages.stream(**kwargs)
                return self._client.messages.create(**kwargs)

            except anthropic.RateLimitError as exc:
                if attempt == max_attempts:
                    raise LLMRateLimitError() from exc
                wait = 2 ** attempt
                log.warning(
                    "llm_rate_limit attempt=%d/%d wait=%ds",
                    attempt, max_attempts, wait,
                )
                time.sleep(wait)

            except anthropic.BadRequestError as exc:
                if "prompt is too long" in str(exc).lower():
                    raise ContextWindowExceededError() from exc
                raise LLMError(str(exc), status_code=400) from exc

            except anthropic.APIStatusError as exc:
                raise LLMError(str(exc), status_code=exc.status_code) from exc

            except anthropic.APIConnectionError as exc:
                raise LLMError(f"Connection error: {exc}") from exc

        raise LLMError("Unreachable — all retry attempts failed")  # pragma: no cover

    # ── Public API ────────────────────────────────────────────

    def complete(
        self,
        messages: MessageList,
        extra_context: str | None = None,
    ) -> str:
        """Non-streaming single-turn completion.

        Args:
            messages:      Conversation in ``[{"role": ..., "content": ...}]`` format.
            extra_context: RAG-retrieved text to prepend to the last user turn.

        Returns:
            The assistant's full response as a plain string.

        Raises:
            LLMRateLimitError:         Rate-limited after retries.
            ContextWindowExceededError: Prompt too long.
            LLMError:                  Other API failures.
        """
        if extra_context:
            messages = _inject_context(messages, extra_context)

        log.info("llm_complete n_messages=%d", len(messages))
        response: anthropic.types.Message = self._create_with_retry(messages)

        log.info(
            "llm_complete_done input_tokens=%d output_tokens=%d",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return response.content[0].text

    def stream(
        self,
        messages: MessageList,
        extra_context: str | None = None,
    ) -> Generator[str, None, None]:
        """Streaming completion — yields text deltas as they arrive.

        Designed for direct use with ``st.write_stream(client.stream(msgs))``.

        Args:
            messages:      Conversation history.
            extra_context: RAG context to prepend to the last user turn.

        Yields:
            Incremental text strings from the model.

        Raises:
            LLMRateLimitError: Rate-limited after retries.
            LLMError:          Other API failures.
        """
        if extra_context:
            messages = _inject_context(messages, extra_context)

        log.info("llm_stream_start n_messages=%d", len(messages))
        try:
            with self._create_with_retry(messages, stream=True) as stream_ctx:
                for text in stream_ctx.text_stream:
                    yield text
        except (LLMError, LLMRateLimitError, ContextWindowExceededError):
            raise
        except anthropic.APIError as exc:
            raise LLMError(str(exc)) from exc

    def build_analysis_prompt(
        self,
        ticker: str,
        info: dict[str, Any],
        signals: dict[str, str],
        signal_summary: str,
        period: str,
    ) -> MessageList:
        """Build a structured stock-analysis message list.

        Separates prompt-construction from call-site logic so that
        prompt engineering can evolve independently of the UI layer.

        Args:
            ticker:         Ticker symbol.
            info:           Dict representation of a
                            :class:`~core.data.stock_client.StockInfo` instance.
            signals:        Output of :func:`~core.analysis.technical.get_signals`.
            signal_summary: Output of :func:`~core.analysis.technical.signal_summary`.
            period:         Price-history period string (e.g. ``"1y"``).

        Returns:
            A single-element :data:`MessageList` ready for :meth:`stream`
            or :meth:`complete`.
        """
        fundamentals = {
            k: info.get(k)
            for k in (
                "name", "sector", "industry", "market_cap",
                "pe_ratio", "forward_pe", "eps", "dividend_yield",
                "fifty_two_week_high", "fifty_two_week_low", "current_price",
            )
        }
        content = _build_stock_analysis_prompt(
            ticker=ticker,
            fundamentals=fundamentals,
            signals=signals,
            bias=signal_summary,
            period=period,
        )
        return [{"role": "user", "content": content}]


# ── Module-level helpers ──────────────────────────────────────

def _inject_context(messages: MessageList, context: str) -> MessageList:
    """Prepend RAG-retrieved context to the last user message.

    Creates a shallow copy of *messages* so the original list is not
    mutated.  Only modifies the last message if its role is ``"user"``.

    Args:
        messages: Original conversation history.
        context:  Concatenated retrieval results from the RAG pipeline.

    Returns:
        A new :data:`MessageList` with context prepended to the last turn.
    """
    msgs = list(messages)
    if not msgs:
        return msgs
    last = msgs[-1]
    if last.get("role") == "user":
        msgs[-1] = {
            "role": "user",
            "content": (
                "## Retrieved Context (ground your answer in this)\n\n"
                f"{context}\n\n"
                "---\n\n"
                f"## Question\n\n{last['content']}"
            ),
        }
    return msgs
