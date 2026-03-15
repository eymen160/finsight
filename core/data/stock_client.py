"""
FinSight — Stock Data Client
================================
Fault-tolerant yfinance wrapper.

Features:
- TTL in-memory cache (600 s default) — eliminates redundant network calls
- Typed retry with exponential backoff — distinguishes 429 from real errors
- User-Agent rotation — reduces shared-IP throttling on Streamlit Cloud
- Specific domain exceptions — no bare Exception leaking to callers
- @st.cache_resource compatible — safe to store in session_state

Usage::

    from core.data.stock_client import StockClient
    client = StockClient()
    info    = client.get_info("AAPL")
    history = client.get_history("AAPL", period="1y")
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from config.settings import settings
from core.exceptions import (
    DataFetchError,
    NetworkTimeoutError,
    RateLimitError,
    TickerNotFoundError,
)

log = logging.getLogger(__name__)

_USER_AGENTS: list[str] = [
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) "
     "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"),
    ("Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"),
]

_RATE_KEYWORDS    = frozenset({"too many requests", "rate limit", "429", "quota"})
_TIMEOUT_KEYWORDS = frozenset({"timed out", "timeout", "read timeout"})


def _classify(exc: Exception, ticker: str) -> DataFetchError:
    """Map a raw exception to the most specific DataFetchError subclass.

    Args:
        exc:    Raw exception from yfinance or requests.
        ticker: Symbol being fetched (for error context).

    Returns:
        A typed :class:`~core.exceptions.DataFetchError` subclass.
    """
    msg = str(exc).lower()
    if any(k in msg for k in _RATE_KEYWORDS):
        return RateLimitError(ticker)
    if any(k in msg for k in _TIMEOUT_KEYWORDS):
        return NetworkTimeoutError(ticker, settings.yfinance_timeout)
    return DataFetchError(f"yfinance error for '{ticker}': {exc}", ticker=ticker)


# ── TTL Cache ─────────────────────────────────────────────────

@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float


class _TTLCache:
    """Minimal thread-unsafe in-memory TTL cache.

    Args:
        ttl: Seconds until each entry expires.
    """

    def __init__(self, ttl: int) -> None:
        self._ttl   = ttl
        self._store: dict[str, _Entry] = {}

    def get(self, key: str) -> Any | None:
        e = self._store.get(key)
        return e.value if (e and time.monotonic() < e.expires_at) else None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = _Entry(value, time.monotonic() + self._ttl)

    def clear(self) -> None:
        self._store.clear()


# ── Return Model ──────────────────────────────────────────────

@dataclass
class StockInfo:
    """Normalised fundamental data for a single ticker.

    All optional fields are ``None`` when Yahoo Finance omits the value
    (e.g. ETFs carry no P/E ratio).

    Attributes:
        ticker:              Upper-case symbol.
        name:                Full company/fund name.
        sector:              GICS sector or ``"N/A"``.
        industry:            GICS industry or ``"N/A"``.
        market_cap:          Total market cap in USD.
        pe_ratio:            Trailing-12-month P/E.
        forward_pe:          Next-12-month estimated P/E.
        eps:                 Trailing-12-month EPS.
        dividend_yield:      Annual yield as decimal (0.02 = 2 %).
        fifty_two_week_high: 52-week intraday high.
        fifty_two_week_low:  52-week intraday low.
        current_price:       Latest price (real-time or prior close).
        currency:            ISO 4217 code (``"USD"``, ``"EUR"`` …).
        raw:                 Full yfinance info dict for advanced queries.
    """
    ticker:              str
    name:                str
    sector:              str
    industry:            str
    market_cap:          int   | None
    pe_ratio:            float | None
    forward_pe:          float | None
    eps:                 float | None
    dividend_yield:      float | None
    fifty_two_week_high: float | None
    fifty_two_week_low:  float | None
    current_price:       float | None
    currency:            str
    raw: dict[str, Any] = field(repr=False)


# ── Client ────────────────────────────────────────────────────

class StockClient:
    """Fault-tolerant yfinance client with caching and typed exceptions.

    Instantiate once per Streamlit session and store in ``st.session_state``
    so the TTL cache persists across reruns.

    Args:
        cache_ttl: Cache duration in seconds.  Defaults to
                   ``settings.yfinance_cache_ttl`` (600 s).
    """

    def __init__(self, cache_ttl: int | None = None) -> None:
        self._cache       = _TTLCache(ttl=cache_ttl or settings.yfinance_cache_ttl)
        self._max_retries = settings.yfinance_max_retries

    # ── Private ───────────────────────────────────────────────

    def _ticker(self, symbol: str) -> yf.Ticker:
        """Build a ``yf.Ticker`` with a random User-Agent session."""
        t = yf.Ticker(symbol)
        try:
            s = requests.Session()
            s.headers["User-Agent"] = random.choice(_USER_AGENTS)
            t._session = s  # type: ignore[attr-defined]
        except Exception:
            pass  # best-effort; yfinance works without custom session
        return t

    def _fetch(self, fn: Any, ticker: str) -> Any:
        """Execute *fn* with exponential-backoff retry on RateLimitError.

        Args:
            fn:     Zero-argument callable performing the network call.
            ticker: Symbol for error attribution.

        Returns:
            Return value of *fn* on success.

        Raises:
            RateLimitError:      After exhausting all retry attempts.
            NetworkTimeoutError: On timeout.
            DataFetchError:      On any other non-retriable failure.
        """
        last: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                typed = _classify(exc, ticker)
                last  = typed
                if isinstance(typed, RateLimitError) and attempt < self._max_retries:
                    wait = 2 ** attempt + random.uniform(0, 1)
                    log.warning(
                        "rate_limited ticker=%s attempt=%d/%d wait=%.1fs",
                        ticker, attempt, self._max_retries, wait,
                    )
                    time.sleep(wait)
                else:
                    raise typed from exc
        raise last  # type: ignore[misc]

    # ── Public API ────────────────────────────────────────────

    def get_info(self, ticker: str) -> StockInfo:
        """Fetch normalised fundamental data for *ticker*.

        Args:
            ticker: Ticker symbol, e.g. ``"AAPL"``. Case-insensitive.

        Returns:
            Populated :class:`StockInfo` dataclass.

        Raises:
            TickerNotFoundError:  Yahoo returned no recognisable data.
            RateLimitError:       Throttled after retries.
            NetworkTimeoutError:  Request timed out.
            DataFetchError:       Any other network/parse failure.
        """
        sym = ticker.upper().strip()
        key = f"info:{sym}"
        if hit := self._cache.get(key):
            log.debug("cache_hit key=%s", key)
            return hit  # type: ignore[return-value]

        log.info("fetch_info ticker=%s", sym)
        raw: dict[str, Any] = self._fetch(lambda: self._ticker(sym).info, sym)

        if not raw or not (raw.get("symbol") or raw.get("shortName") or raw.get("longName")):
            raise TickerNotFoundError(sym)

        g = raw.get
        info = StockInfo(
            ticker              = sym,
            name                = g("longName") or g("shortName") or sym,
            sector              = g("sector")   or "N/A",
            industry            = g("industry") or "N/A",
            market_cap          = g("marketCap"),
            pe_ratio            = g("trailingPE"),
            forward_pe          = g("forwardPE"),
            eps                 = g("trailingEps"),
            dividend_yield      = g("dividendYield"),
            fifty_two_week_high = g("fiftyTwoWeekHigh"),
            fifty_two_week_low  = g("fiftyTwoWeekLow"),
            current_price       = g("currentPrice") or g("regularMarketPrice") or g("previousClose"),
            currency            = g("currency") or "USD",
            raw                 = raw,
        )
        self._cache.set(key, info)
        log.info("fetch_info_ok ticker=%s name=%s", sym, info.name)
        return info

    def get_history(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Fetch OHLCV price history for *ticker*.

        Args:
            ticker:   Ticker symbol. Case-insensitive.
            period:   yfinance period string: ``"1mo"``, ``"6mo"``, ``"1y"``,
                      ``"2y"``, ``"5y"``, ``"max"``.
            interval: Bar size: ``"1d"`` (daily), ``"1wk"``, ``"1mo"``.

        Returns:
            DataFrame with DatetimeIndex and columns
            ``[Open, High, Low, Close, Volume]`` (auto-adjusted).

        Raises:
            TickerNotFoundError: Download returned empty DataFrame.
            RateLimitError:      Throttled after retries.
            NetworkTimeoutError: Request timed out.
            DataFetchError:      Any other failure.
        """
        sym = ticker.upper().strip()
        key = f"hist:{sym}:{period}:{interval}"
        if hit := self._cache.get(key):
            log.debug("cache_hit key=%s", key)
            return hit  # type: ignore[return-value]

        log.info("fetch_history ticker=%s period=%s", sym, period)
        df: pd.DataFrame = self._fetch(
            lambda: yf.download(
                sym, period=period, interval=interval,
                progress=False, auto_adjust=True,
            ),
            sym,
        )

        if df.empty:
            raise TickerNotFoundError(sym)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)
        self._cache.set(key, df)
        log.info("fetch_history_ok ticker=%s rows=%d", sym, len(df))
        return df

    def get_financials(self, ticker: str) -> dict[str, pd.DataFrame]:
        """Fetch annual income statement, balance sheet, and cash flow.

        Args:
            ticker: Ticker symbol. Case-insensitive.

        Returns:
            Dict with keys ``"income_statement"``, ``"balance_sheet"``,
            ``"cash_flow"``.

        Raises:
            DataFetchError: Any retrieval failure.
        """
        sym = ticker.upper().strip()
        key = f"fin:{sym}"
        if hit := self._cache.get(key):
            return hit  # type: ignore[return-value]

        log.info("fetch_financials ticker=%s", sym)

        def _call() -> dict[str, pd.DataFrame]:
            t = self._ticker(sym)
            return {
                "income_statement": t.financials,
                "balance_sheet":    t.balance_sheet,
                "cash_flow":        t.cashflow,
            }

        result = self._fetch(_call, sym)
        self._cache.set(key, result)
        return result

    def clear_cache(self) -> None:
        """Evict all cached entries, forcing fresh network calls."""
        self._cache.clear()
        log.info("cache_cleared")
