"""
FinSight FastAPI — Request Schemas (Pydantic v2)
==================================================
All incoming payload models live here.  Every field carries a ``Field``
constraint so invalid data is rejected at the boundary before it ever
touches business logic.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator

# ── Type aliases ──────────────────────────────────────────────
TickerStr = Annotated[
    str,
    Field(
        min_length=1,
        max_length=12,
        pattern=r"^[A-Z0-9.\-\^=]+$",
        description="NYSE/NASDAQ ticker symbol, e.g. 'AAPL', 'BTC-USD', '^GSPC'.",
        examples=["AAPL", "MSFT", "BTC-USD"],
    ),
]

PeriodStr = Annotated[
    str,
    Field(
        description="yfinance period string.",
        examples=["1y"],
    ),
]


# ── Finance ───────────────────────────────────────────────────

class StockAnalysisRequest(BaseModel):
    """Request body for POST /api/v1/finance/analysis."""

    ticker: TickerStr
    period: PeriodStr = Field(default="1y")
    include_ai_analysis: bool = Field(
        default=True,
        description="If true, stream a Claude analysis after computing indicators.",
    )

    @field_validator("ticker", mode="before")
    @classmethod
    def normalise_ticker(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        allowed = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "max"}
        if v not in allowed:
            raise ValueError(f"period must be one of {sorted(allowed)}")
        return v


class StockHistoryRequest(BaseModel):
    """Query parameters for GET /api/v1/finance/history."""

    ticker: TickerStr
    period: PeriodStr = Field(default="1y")
    interval: str = Field(
        default="1d",
        description="Bar size: '1d', '1wk', '1mo'.",
    )

    @field_validator("ticker", mode="before")
    @classmethod
    def normalise_ticker(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: str) -> str:
        allowed = {"1d", "1wk", "1mo"}
        if v not in allowed:
            raise ValueError(f"interval must be one of {sorted(allowed)}")
        return v


# ── Chat ──────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    """A single turn in a conversation."""

    role: str = Field(
        ...,
        pattern=r"^(user|assistant)$",
        description="'user' or 'assistant'.",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=32_000,
        description="Message text.",
    )


class ChatRequest(BaseModel):
    """Request body for POST /api/v1/chat/complete."""

    messages: list[ChatMessage] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Conversation history. Last message must have role='user'.",
    )
    extra_context: str | None = Field(
        default=None,
        max_length=64_000,
        description="Optional RAG-retrieved context prepended to the last user turn.",
    )

    @field_validator("messages")
    @classmethod
    def last_message_is_user(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        if v and v[-1].role != "user":
            raise ValueError("The last message in the conversation must have role='user'.")
        return v


# ── RAG / Documents ───────────────────────────────────────────

class DocumentQueryRequest(BaseModel):
    """Request body for POST /api/v1/rag/query."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=2_000,
        description="Natural-language question about the indexed documents.",
    )
    k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve.",
    )


class DocumentUploadMetadata(BaseModel):
    """Optional JSON metadata submitted alongside a multipart PDF upload."""

    description: str | None = Field(
        default=None,
        max_length=500,
        description="Short description of the document (e.g. 'AAPL 10-K 2024').",
    )
