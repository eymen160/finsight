"""
FinSight — Custom Exceptions
==============================
Raise these instead of generic exceptions so callers can handle
specific failure modes without string-matching error messages.
"""


class FinSightError(Exception):
    """Base exception for all FinSight errors."""


# ── Data layer ────────────────────────────────────────────────
class TickerNotFoundError(FinSightError):
    """Raised when yfinance cannot find data for a given ticker."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"No data found for ticker '{ticker}'")


class DataFetchError(FinSightError):
    """Raised when a remote data source returns an unexpected response."""


# ── LLM layer ─────────────────────────────────────────────────
class LLMError(FinSightError):
    """Raised when the Claude API call fails after retries."""


class ContextWindowExceededError(LLMError):
    """Raised when the prompt is too long for the model's context window."""


# ── RAG layer ─────────────────────────────────────────────────
class RAGError(FinSightError):
    """Base exception for RAG pipeline errors."""


class DocumentLoadError(RAGError):
    """Raised when a document cannot be loaded or parsed."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        super().__init__(f"Cannot load document '{path}': {reason}")


class IndexNotFoundError(RAGError):
    """Raised when the FAISS index has not been built yet."""
