"""
FinSight FastAPI — Response Schemas (Pydantic v2)
==================================================
Every endpoint returns one of these models (or a streaming response).
Strict ``model_config = ConfigDict(from_attributes=True)`` allows direct
construction from dataclass instances (e.g. ``StockInfo``).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Shared ────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    """Standardised error envelope — never exposes stack traces."""

    code: str = Field(description="Machine-readable error code, e.g. 'RATE_LIMIT_ERROR'.")
    message: str = Field(description="Human-readable description safe to surface to end users.")
    retry_after: int | None = Field(
        default=None,
        description="Seconds until the client should retry (set on 429 responses).",
    )


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Finance ───────────────────────────────────────────────────

class StockInfoResponse(BaseModel):
    """Normalised fundamental data for a single ticker."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    name: str
    sector: str
    industry: str
    market_cap: int | None
    pe_ratio: float | None
    forward_pe: float | None
    eps: float | None
    dividend_yield: float | None
    fifty_two_week_high: float | None
    fifty_two_week_low: float | None
    current_price: float | None
    currency: str


class OHLCVBar(BaseModel):
    """A single OHLCV candle."""

    date: str = Field(description="ISO 8601 date string.")
    open: float
    high: float
    low: float
    close: float
    volume: float


class StockHistoryResponse(BaseModel):
    ticker: str
    period: str
    interval: str
    bars: list[OHLCVBar]
    total_bars: int


class SignalValue(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    MIXED   = "MIXED"


class TechnicalSignalsResponse(BaseModel):
    ticker: str
    period: str
    signals: dict[str, SignalValue]
    bias: SignalValue
    latest_close: float | None
    latest_rsi: float | None
    latest_macd: float | None
    latest_macd_signal: float | None


# ── Chat ──────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    """Used for non-streaming /chat/complete responses."""

    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None


# ── RAG / Documents ───────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    """202 Accepted — tells the client the job ID to poll."""

    job_id: str = Field(description="Unique ID for polling the embedding job status.")
    filename: str
    status: str = Field(default="processing")
    message: str = Field(
        default="Document accepted. Embedding is running in the background. "
                "Poll GET /api/v1/rag/jobs/{job_id} for status."
    )


class JobStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETE   = "complete"
    FAILED     = "failed"


class EmbedJobStatusResponse(BaseModel):
    """Returned by GET /api/v1/rag/jobs/{job_id}."""

    job_id: str
    filename: str
    status: JobStatus
    chunks_indexed: int | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class DocumentQueryResponse(BaseModel):
    query: str
    context_chunks: int = Field(description="Number of chunks retrieved from FAISS.")
    answer: str = Field(description="Claude's grounded answer.")


class IndexedDocumentsResponse(BaseModel):
    documents: list[str]
    total: int
