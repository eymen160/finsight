"""
FinSight — Stock Data Client
==============================
Thin wrapper around yfinance that adds:
  - In-memory TTL caching (avoids hammering Yahoo during dev)
  - Structured logging
  - Domain exceptions instead of raw yfinance errors
  - Type-safe return models via dataclasses

Usage:
    from core.data.stock_client import StockClient
    client = StockClient()
    info    = client.get_info("AAPL")
    history = client.get_history("AAPL", period="1y")
"""

import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import yfinance as yf

from config.settings import settings
from core.exceptions import DataFetchError, TickerNotFoundError
from core.logger import get_logger

logger = get_logger(__name__)


# ── Simple in-memory TTL cache ────────────────────────────────

@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class _TTLCache:
    """Minimal TTL cache — no external dependency."""

    def __init__(self, ttl: int) -> None:
        self._ttl = ttl
        self._store: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None or time.monotonic() > entry.expires_at:
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = _CacheEntry(
            value=value,
            expires_at=time.monotonic() + self._ttl,
        )

    def clear(self) -> None:
        self._store.clear()


# ── Return models ─────────────────────────────────────────────

@dataclass
class StockInfo:
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
    raw: dict[str, Any] = field(repr=False)


# ── Client ────────────────────────────────────────────────────

class StockClient:
    """
    Fetches stock data from Yahoo Finance.

    All public methods are synchronous and safe to call from
    Streamlit's main thread. Long-running fetches are isolated
    here so the UI never imports yfinance directly.
    """

    def __init__(self) -> None:
        self._cache = _TTLCache(ttl=settings.cache_ttl_seconds)

    # ── Public API ────────────────────────────────────────────

    def get_info(self, ticker: str) -> StockInfo:
        """
        Return fundamental info for *ticker*.

        Raises:
            TickerNotFoundError: if Yahoo returns no info dict.
            DataFetchError: on network / parse failures.
        """
        cache_key = f"info:{ticker.upper()}"
        if cached := self._cache.get(cache_key):
            logger.debug("cache_hit", key=cache_key)
            return cached

        logger.info("fetching_stock_info", ticker=ticker)
        try:
            raw: dict = yf.Ticker(ticker).info
        except Exception as exc:
            raise DataFetchError(f"yfinance error for '{ticker}': {exc}") from exc

        if not raw or raw.get("trailingPegRatio") is None and raw.get("symbol") is None:
            raise TickerNotFoundError(ticker)

        info = StockInfo(
            ticker=ticker.upper(),
            name=raw.get("longName") or raw.get("shortName", ticker),
            sector=raw.get("sector", "N/A"),
            industry=raw.get("industry", "N/A"),
            market_cap=raw.get("marketCap"),
            pe_ratio=raw.get("trailingPE"),
            forward_pe=raw.get("forwardPE"),
            eps=raw.get("trailingEps"),
            dividend_yield=raw.get("dividendYield"),
            fifty_two_week_high=raw.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=raw.get("fiftyTwoWeekLow"),
            current_price=raw.get("currentPrice") or raw.get("regularMarketPrice"),
            currency=raw.get("currency", "USD"),
            raw=raw,
        )
        self._cache.set(cache_key, info)
        return info

    def get_history(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Return OHLCV history as a DataFrame indexed by date.

        Args:
            ticker:   Ticker symbol, e.g. "AAPL".
            period:   yfinance period string: "1mo", "6mo", "1y", "5y", "max".
            interval: Bar size: "1d", "1wk", "1mo".

        Raises:
            TickerNotFoundError: if the DataFrame comes back empty.
            DataFetchError: on network errors.
        """
        cache_key = f"history:{ticker.upper()}:{period}:{interval}"
        if cached := self._cache.get(cache_key):
            logger.debug("cache_hit", key=cache_key)
            return cached

        logger.info("fetching_history", ticker=ticker, period=period, interval=interval)
        try:
            df: pd.DataFrame = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
        except Exception as exc:
            raise DataFetchError(f"yfinance download error: {exc}") from exc

        if df.empty:
            raise TickerNotFoundError(ticker)

        # Flatten MultiIndex columns if yfinance returns them
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)
        self._cache.set(cache_key, df)
        return df

    def get_financials(self, ticker: str) -> dict[str, pd.DataFrame]:
        """
        Return income statement, balance sheet, and cash flow
        as a dict of DataFrames.

        Returns:
            {
                "income_statement": pd.DataFrame,
                "balance_sheet":    pd.DataFrame,
                "cash_flow":        pd.DataFrame,
            }
        """
        cache_key = f"financials:{ticker.upper()}"
        if cached := self._cache.get(cache_key):
            return cached

        logger.info("fetching_financials", ticker=ticker)
        try:
            t = yf.Ticker(ticker)
            result = {
                "income_statement": t.financials,
                "balance_sheet": t.balance_sheet,
                "cash_flow": t.cashflow,
            }
        except Exception as exc:
            raise DataFetchError(f"Could not fetch financials for '{ticker}': {exc}") from exc

        self._cache.set(cache_key, result)
        return result

    def clear_cache(self) -> None:
        """Flush the in-memory cache (useful in tests)."""
        self._cache.clear()
        logger.info("cache_cleared")
