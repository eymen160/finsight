"""
FinSight — Domain Exception Hierarchy
========================================
Every layer raises a typed subclass so callers can handle specific
failure modes without fragile message string-matching.

Hierarchy:
    FinSightError
    ├── DataFetchError
    │   ├── TickerNotFoundError
    │   ├── RateLimitError
    │   └── NetworkTimeoutError
    ├── LLMError
    │   ├── LLMRateLimitError
    │   └── ContextWindowExceededError
    └── RAGError
        ├── DocumentLoadError
        ├── DocumentParseError
        └── IndexNotFoundError
"""
from __future__ import annotations


class FinSightError(Exception):
    """Root exception for all FinSight domain errors."""


# ── Data Layer ────────────────────────────────────────────────

class DataFetchError(FinSightError):
    """A remote data source returned an unexpected or unrecoverable response."""
    def __init__(self, message: str, ticker: str | None = None) -> None:
        self.ticker = ticker
        super().__init__(message)


class TickerNotFoundError(DataFetchError):
    """yfinance returned empty/invalid data for the requested ticker."""
    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(
            f"No market data found for '{ticker}'. "
            "Verify the symbol and try again.",
            ticker=ticker,
        )


class RateLimitError(DataFetchError):
    """Yahoo Finance throttled the request (HTTP 429)."""
    def __init__(self, ticker: str, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Yahoo Finance rate limit hit for '{ticker}'. "
            f"Wait ~{retry_after}s then retry.",
            ticker=ticker,
        )


class NetworkTimeoutError(DataFetchError):
    """A market-data request exceeded the configured timeout."""
    def __init__(self, ticker: str, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Request timed out after {timeout_seconds}s for '{ticker}'.",
            ticker=ticker,
        )


# ── LLM Layer ─────────────────────────────────────────────────

class LLMError(FinSightError):
    """Claude API call failed after all retry attempts."""
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class LLMRateLimitError(LLMError):
    """Anthropic API returned HTTP 429 after exhausting retries."""
    def __init__(self, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Anthropic API rate limit exceeded. Retry after {retry_after}s.",
            status_code=429,
        )


class ContextWindowExceededError(LLMError):
    """Constructed prompt exceeds the model's context window."""
    def __init__(self, estimated_tokens: int | None = None) -> None:
        self.estimated_tokens = estimated_tokens
        msg = "Prompt exceeds model context window."
        if estimated_tokens:
            msg += f" Estimated tokens: {estimated_tokens:,}."
        super().__init__(msg)


# ── RAG Layer ─────────────────────────────────────────────────

class RAGError(FinSightError):
    """Base exception for RAG pipeline failures."""


class DocumentLoadError(RAGError):
    """PDF cannot be opened or read from disk."""
    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Cannot load '{path}': {reason}")


class DocumentParseError(RAGError):
    """pypdf opened the file but extracted zero usable text (image-only PDF)."""
    def __init__(self, path: str, page_count: int) -> None:
        self.path = path
        self.page_count = page_count
        super().__init__(
            f"No text extracted from '{path}' ({page_count} pages). "
            "The PDF may be image-only (requires OCR)."
        )


class IndexNotFoundError(RAGError):
    """Retrieval attempted before any documents have been ingested."""
    def __init__(self) -> None:
        super().__init__(
            "No documents indexed yet. Upload a PDF on the Document Q&A page."
        )
