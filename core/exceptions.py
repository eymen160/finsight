"""
FinSight — Domain Exception Hierarchy
========================================
Every layer raises a specific subclass so callers can handle
failure modes without fragile string-matching on error messages.

Hierarchy:
    FinSightError
    ├── DataFetchError
    │   ├── TickerNotFoundError
    │   ├── RateLimitError
    │   └── NetworkTimeoutError
    ├── LLMError
    │   ├── ContextWindowExceededError
    │   └── LLMRateLimitError
    └── RAGError
        ├── DocumentLoadError
        ├── DocumentParseError
        └── IndexNotFoundError
"""

from __future__ import annotations


# ── Base ──────────────────────────────────────────────────────

class FinSightError(Exception):
    """Root exception for all FinSight domain errors.

    All custom exceptions inherit from this so callers can do a
    single broad catch (``except FinSightError``) when they need
    to handle any application-level failure uniformly.
    """


# ── Data / Market-data layer ──────────────────────────────────

class DataFetchError(FinSightError):
    """Raised when a remote data source returns an unexpected response.

    Args:
        message: Human-readable description of what went wrong.
        ticker: Optional ticker symbol for context.
    """

    def __init__(self, message: str, ticker: str | None = None) -> None:
        self.ticker = ticker
        super().__init__(message)


class TickerNotFoundError(DataFetchError):
    """Raised when yfinance returns empty/invalid data for a ticker.

    Args:
        ticker: The symbol that could not be found.
    """

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(
            f"No market data found for '{ticker}'. "
            "Verify the symbol is correct and the market is open.",
            ticker=ticker,
        )


class RateLimitError(DataFetchError):
    """Raised when Yahoo Finance throttles requests from the client IP.

    This is common on Streamlit Cloud where many apps share the same
    egress IP address.

    Args:
        ticker: The symbol being fetched when throttling occurred.
        retry_after: Suggested seconds to wait before retrying, if known.
    """

    def __init__(self, ticker: str, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Yahoo Finance rate limit hit for '{ticker}'. "
            f"Wait ~{retry_after}s then retry.",
            ticker=ticker,
        )


class NetworkTimeoutError(DataFetchError):
    """Raised when a market-data request exceeds the configured timeout.

    Args:
        ticker: The symbol being fetched.
        timeout_seconds: The timeout that was exceeded.
    """

    def __init__(self, ticker: str, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Network timeout ({timeout_seconds}s) fetching '{ticker}'.",
            ticker=ticker,
        )


# ── LLM layer ─────────────────────────────────────────────────

class LLMError(FinSightError):
    """Raised when the Claude API call fails after all retries.

    Args:
        message: Error detail from the Anthropic SDK.
        status_code: HTTP status code if available.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class ContextWindowExceededError(LLMError):
    """Raised when the constructed prompt exceeds the model context limit.

    Args:
        estimated_tokens: Approximate token count of the rejected prompt.
    """

    def __init__(self, estimated_tokens: int | None = None) -> None:
        self.estimated_tokens = estimated_tokens
        msg = "Prompt exceeds model context window."
        if estimated_tokens:
            msg += f" Estimated tokens: {estimated_tokens:,}."
        super().__init__(msg)


class LLMRateLimitError(LLMError):
    """Raised when the Anthropic API returns a 429 after exhausting retries.

    Args:
        retry_after: Seconds until the rate-limit window resets.
    """

    def __init__(self, retry_after: int = 60) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Anthropic API rate limit exceeded. Retry after {retry_after}s.",
            status_code=429,
        )


# ── RAG layer ─────────────────────────────────────────────────

class RAGError(FinSightError):
    """Base exception for all RAG pipeline errors."""


class DocumentLoadError(RAGError):
    """Raised when a PDF cannot be opened or read from disk.

    Args:
        path: Filesystem path of the document that failed to load.
        reason: Underlying OS or library error message.
    """

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Cannot load '{path}': {reason}")


class DocumentParseError(RAGError):
    """Raised when pypdf can open the file but extracts no usable text.

    Typically indicates a scanned/image-only PDF without OCR layer.

    Args:
        path: Path to the problematic document.
        page_count: Number of pages that were attempted.
    """

    def __init__(self, path: str, page_count: int) -> None:
        self.path = path
        self.page_count = page_count
        super().__init__(
            f"Extracted zero text from '{path}' ({page_count} pages). "
            "The PDF may be image-only (no OCR layer)."
        )


class IndexNotFoundError(RAGError):
    """Raised when a retrieval query is attempted before any ingest.

    Signals to the UI layer that it should prompt the user to upload
    a document rather than display a generic error.
    """

    def __init__(self) -> None:
        super().__init__(
            "No documents have been indexed yet. "
            "Upload a PDF on the Document Q&A page first."
        )
