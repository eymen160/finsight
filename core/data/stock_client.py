"""
FinSight — Stock Data Client
==============================
yfinance wrapper with:
  - Long TTL cache (10 min) to avoid rate limits on Streamlit Cloud
  - Exponential backoff retry on rate-limit errors
  - Randomised User-Agent header rotation
  - Graceful fallback for missing fields
"""

import random
import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import yfinance as yf

from config.settings import settings
from core.exceptions import DataFetchError, TickerNotFoundError
from core.logger import get_logger

logger = get_logger(__name__)

# Rotate UA to reduce Yahoo rate-limiting on shared IPs (Streamlit Cloud)
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# ── TTL Cache (10 min default on Cloud, 5 min local) ──────────

@dataclass
class _CacheEntry:
    value: Any
    expires_at: float

class _TTLCache:
    def __init__(self, ttl: int) -> None:
        self._ttl   = ttl
        self._store: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        e = self._store.get(key)
        if e is None or time.monotonic() > e.expires_at:
            return None
        return e.value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = _CacheEntry(value=value, expires_at=time.monotonic() + self._ttl)

    def clear(self) -> None:
        self._store.clear()

# ── Return model ──────────────────────────────────────────────

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

def _retry_fetch(fn, retries: int = 3):
    """Call fn() with exponential backoff on rate-limit errors."""
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:
            msg = str(exc).lower()
            is_rate = any(k in msg for k in ["too many requests","rate limit","429","quota"])
            if is_rate and attempt < retries - 1:
                wait = 2 ** attempt + random.uniform(0, 1)
                logger.warning("rate_limited_retrying", attempt=attempt+1, wait=round(wait,1))
                time.sleep(wait)
            else:
                raise
    raise DataFetchError("Max retries exceeded")


class StockClient:

    # Use 10-minute cache on Cloud (shared IP hits rate limits fast)
    _CACHE_TTL = 600

    def __init__(self) -> None:
        self._cache = _TTLCache(ttl=self._CACHE_TTL)

    def _ticker(self, symbol: str) -> yf.Ticker:
        t = yf.Ticker(symbol)
        # Inject random UA to reduce shared-IP rate-limiting
        try:
            if hasattr(t, "_session") and t._session:
                t._session.headers["User-Agent"] = random.choice(_USER_AGENTS)
        except Exception:
            pass
        return t

    def get_info(self, ticker: str) -> StockInfo:
        key = f"info:{ticker.upper()}"
        if cached := self._cache.get(key):
            logger.debug("cache_hit", key=key)
            return cached

        logger.info("fetching_info", ticker=ticker)
        try:
            raw: dict = _retry_fetch(lambda: self._ticker(ticker).info)
        except Exception as exc:
            raise DataFetchError(f"yfinance error for '{ticker}': {exc}") from exc

        if not raw or (not raw.get("symbol") and not raw.get("shortName")):
            raise TickerNotFoundError(ticker)

        def _f(k): return raw.get(k)

        info = StockInfo(
            ticker        = ticker.upper(),
            name          = _f("longName") or _f("shortName") or ticker,
            sector        = _f("sector")   or "N/A",
            industry      = _f("industry") or "N/A",
            market_cap    = _f("marketCap"),
            pe_ratio      = _f("trailingPE"),
            forward_pe    = _f("forwardPE"),
            eps           = _f("trailingEps"),
            dividend_yield= _f("dividendYield"),
            fifty_two_week_high = _f("fiftyTwoWeekHigh"),
            fifty_two_week_low  = _f("fiftyTwoWeekLow"),
            current_price = _f("currentPrice") or _f("regularMarketPrice") or _f("previousClose"),
            currency      = _f("currency") or "USD",
            raw           = raw,
        )
        self._cache.set(key, info)
        return info

    def get_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        key = f"hist:{ticker.upper()}:{period}:{interval}"
        if cached := self._cache.get(key):
            logger.debug("cache_hit", key=key)
            return cached

        logger.info("fetching_history", ticker=ticker, period=period)
        try:
            df: pd.DataFrame = _retry_fetch(lambda: yf.download(
                ticker, period=period, interval=interval,
                progress=False, auto_adjust=True,
                # Small delay avoids burst detection
            ))
        except Exception as exc:
            raise DataFetchError(f"yfinance error for '{ticker}': {exc}") from exc

        if df.empty:
            raise TickerNotFoundError(ticker)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)
        self._cache.set(key, df)
        return df

    def get_financials(self, ticker: str) -> dict[str, pd.DataFrame]:
        key = f"fin:{ticker.upper()}"
        if cached := self._cache.get(key):
            return cached
        try:
            t = self._ticker(ticker)
            result = {
                "income_statement": t.financials,
                "balance_sheet":    t.balance_sheet,
                "cash_flow":        t.cashflow,
            }
        except Exception as exc:
            raise DataFetchError(f"Financials error for '{ticker}': {exc}") from exc
        self._cache.set(key, result)
        return result

    def clear_cache(self) -> None:
        self._cache.clear()
        logger.info("cache_cleared")
