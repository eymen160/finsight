"""
FinSight — Stock Data Client
================================
Two-layer caching strategy to survive Streamlit Cloud rate limits:

Layer 1: requests-cache (SQLite on /tmp) — persists across reruns & redeploys.
         yfinance uses requests internally, so ALL http calls are cached automatically.
         TTL = 10 minutes. No code changes needed at call sites.

Layer 2: In-memory TTLCache — avoids even SQLite lookups within a session.
         TTL = 10 minutes. Cleared on manual "Refresh" button.

This means:
  - First load: might be slow if Yahoo rate-limits.
  - All subsequent loads within 10 min: instant (SQLite).
  - Manual refresh: clears both layers and re-fetches.
"""
from __future__ import annotations

import logging
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
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

# ── Layer 1: requests-cache (SQLite) ─────────────────────────
# Install once at import time. yfinance uses requests internally,
# so this transparently caches ALL Yahoo Finance HTTP responses.
_CACHE_DB = Path("/tmp/finsight_http_cache")

try:
    import requests_cache
    requests_cache.install_cache(
        str(_CACHE_DB),
        backend="sqlite",
        expire_after=600,          # 10 min TTL
        stale_if_error=True,       # serve stale on network error
        allowable_methods=["GET"],
        ignored_parameters=["crumb"],  # yfinance crumb changes but data doesn't
    )
    log.info("requests_cache_installed path=%s", _CACHE_DB)
    _REQUESTS_CACHE_OK = True
except ImportError:
    log.warning("requests-cache not installed — HTTP-level caching disabled")
    _REQUESTS_CACHE_OK = False


# ── User-Agent pool ───────────────────────────────────────────
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
    msg = str(exc).lower()
    if any(k in msg for k in _RATE_KEYWORDS):
        return RateLimitError(ticker)
    if any(k in msg for k in _TIMEOUT_KEYWORDS):
        return NetworkTimeoutError(ticker, settings.yfinance_timeout)
    return DataFetchError(f"yfinance error for '{ticker}': {exc}", ticker=ticker)


# ── Layer 2: in-memory TTL cache ──────────────────────────────

@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float


class _TTLCache:
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
        # Also clear the HTTP-level SQLite cache so fresh data is fetched
        if _REQUESTS_CACHE_OK:
            try:
                import requests_cache
                requests_cache.clear()
                log.info("requests_cache_cleared")
            except Exception:
                pass


# ── Return Model ──────────────────────────────────────────────

@dataclass
class StockInfo:
    """Normalised fundamental data for a single ticker."""
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
    """Two-layer cached yfinance client.

    Instantiate once via @st.cache_resource.
    """

    def __init__(self, cache_ttl: int | None = None) -> None:
        self._mem  = _TTLCache(ttl=cache_ttl or settings.yfinance_cache_ttl)
        self._max  = settings.yfinance_max_retries

    def _ticker(self, sym: str) -> yf.Ticker:
        t = yf.Ticker(sym)
        try:
            s = requests.Session()
            s.headers["User-Agent"] = random.choice(_USER_AGENTS)
            t._session = s  # type: ignore[attr-defined]
        except Exception:
            pass
        return t

    def _fetch(self, fn: Any, ticker: str) -> Any:
        """Retry with exponential backoff on rate-limit errors."""
        last: Exception | None = None
        for attempt in range(1, self._max + 1):
            try:
                return fn()
            except Exception as exc:
                typed = _classify(exc, ticker)
                last  = typed
                if isinstance(typed, RateLimitError) and attempt < self._max:
                    wait = 2 ** attempt + random.uniform(0, 1)
                    log.warning("rate_limited ticker=%s attempt=%d wait=%.1fs", ticker, attempt, wait)
                    time.sleep(wait)
                else:
                    raise typed from exc
        raise last  # type: ignore[misc]

    def get_info(self, ticker: str) -> StockInfo:
        """Fetch and normalise fundamental data for *ticker*."""
        sym = ticker.upper().strip()
        key = f"info:{sym}"
        if hit := self._mem.get(key):
            log.debug("mem_cache_hit key=%s", key)
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
            current_price       = (g("currentPrice") or g("regularMarketPrice") or g("previousClose")),
            currency            = g("currency") or "USD",
            raw                 = raw,
        )
        self._mem.set(key, info)
        log.info("fetch_info_ok ticker=%s name=%s", sym, info.name)
        return info

    def get_history(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Fetch OHLCV price history for *ticker*."""
        sym = ticker.upper().strip()
        key = f"hist:{sym}:{period}:{interval}"
        if hit := self._mem.get(key):
            log.debug("mem_cache_hit key=%s", key)
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
        self._mem.set(key, df)
        log.info("fetch_history_ok ticker=%s rows=%d", sym, len(df))
        return df

    def get_financials(self, ticker: str) -> dict[str, pd.DataFrame]:
        """Fetch annual income statement, balance sheet, and cash flow."""
        sym = ticker.upper().strip()
        key = f"fin:{sym}"
        if hit := self._mem.get(key):
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
        self._mem.set(key, result)
        return result

    def clear_cache(self) -> None:
        """Clear both memory and HTTP-level caches."""
        self._mem.clear()  # also clears requests_cache SQLite
        log.info("all_caches_cleared")
