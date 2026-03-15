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

# ── Type aliases ──────────────────────────────────────────────
MessageList = list[dict[str, str]]


# ── Prompt builders (pure functions — easy to unit-test) ──────

def _build_analysis_prompt(
    ticker: str,
    fundamentals: dict[str, Any],
    signals: dict[str, str],
    bias: str,
    period: str,
) -> str:
    """Build the structured stock-analysis user message.

    Args:
        ticker:       Ticker symbol.
        fundamentals: Subset of :class:`~core.data.stock_client.StockInfo` fields.
        signals:      Output of :func:`~core.analysis.technical.get_signals`.
        bias:         Output of :func:`~core.analysis.technical.signal_summary`.
        period:       Price-history period (e.g. ``"1y"``).

    Returns:
        Formatted string for the ``"user"`` role.
    """
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
    """Prepend RAG context to the last user turn (non-mutating).

    Args:
        messages: Original conversation history.
        context:  Concatenated retrieval results.

    Returns:
        New :data:`MessageList` with context prepended to the last user message.
    """
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

    Thread-safe (httpx handles connection pooling internally).
    Instantiate once per Streamlit session and store in session_state.

    Args:
        api_key: Override the key from ``settings.api_key``.
        model:   Override the model from ``settings.claude_model``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model:   str | None = None,
    ) -> None:
        self._client = anthropic.Anthropic(api_key=api_key or settings.api_key)
        self._model  = model or settings.claude_model
        log.info("claude_client_init model=%s", self._model)

    # ── Private ───────────────────────────────────────────────

    def _call(self, messages: MessageList, stream: bool = False) -> Any:
        """Call the Messages API with exponential-backoff retry on 429.

        Args:
            messages: Conversation history.
            stream:   Return a streaming context manager when ``True``.

        Returns:
            :class:`anthropic.types.Message` or streaming context manager.

        Raises:
            LLMRateLimitError:         HTTP 429 after retries.
            ContextWindowExceededError: Prompt too long.
            LLMError:                  Any other API failure.
        """
        max_attempts = 4
        kwargs: dict[str, Any] = dict(
            model      = self._model,
            max_tokens = settings.max_tokens,
            temperature= settings.temperature,
            system     = _SYSTEM_PROMPT,
            messages   = messages,
        )
        for attempt in range(1, max_attempts + 1):
            try:
                if stream:
                    return self._client.messages.stream(**kwargs)
                return self._client.messages.create(**kwargs)

            except anthropic.RateLimitError as exc:
                if attempt == max_attempts:
                    raise LLMRateLimitError() from exc
                wait = 2 ** attempt
                log.warning("llm_rate_limit attempt=%d/%d wait=%ds", attempt, max_attempts, wait)
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

    # ── Public API ────────────────────────────────────────────

    def complete(
        self,
        messages: MessageList,
        extra_context: str | None = None,
    ) -> str:
        """Non-streaming completion.

        Args:
            messages:      Conversation in ``[{"role": ..., "content": ...}]`` format.
            extra_context: RAG context to prepend to the last user turn.

        Returns:
            Assistant's full response as a plain string.

        Raises:
            LLMRateLimitError, ContextWindowExceededError, LLMError.
        """
        if extra_context:
            messages = _inject_context(messages, extra_context)

        log.info("llm_complete n_messages=%d", len(messages))
        resp: anthropic.types.Message = self._call(messages)
        log.info(
            "llm_complete_done in=%d out=%d",
            resp.usage.input_tokens, resp.usage.output_tokens,
        )
        return resp.content[0].text

    def stream(
        self,
        messages: MessageList,
        extra_context: str | None = None,
    ) -> Generator[str, None, None]:
        """Streaming completion — yields text deltas for ``st.write_stream``.

        Args:
            messages:      Conversation history.
            extra_context: RAG context to prepend to the last user turn.

        Yields:
            Incremental text strings from the model.

        Raises:
            LLMRateLimitError, ContextWindowExceededError, LLMError.
        """
        if extra_context:
            messages = _inject_context(messages, extra_context)

        log.info("llm_stream_start n_messages=%d", len(messages))
        try:
            with self._call(messages, stream=True) as ctx:
                yield from ctx.text_stream
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
        """Build a stock-analysis :data:`MessageList`.

        Separates prompt construction from call-site logic so prompt
        engineering can evolve without touching the UI layer.

        Args:
            ticker:         Ticker symbol.
            info:           Dict of :class:`~core.data.stock_client.StockInfo`.
            signals:        Output of :func:`~core.analysis.technical.get_signals`.
            signal_summary: Output of :func:`~core.analysis.technical.signal_summary`.
            period:         Price-history period string.

        Returns:
            Single-element :data:`MessageList` ready for :meth:`stream`.
        """
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
