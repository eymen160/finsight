"""
FinSight — Stock Data Client
================================
Thin, fault-tolerant wrapper around ``yfinance`` that adds:

- **TTL caching** — avoids redundant network calls within a session.
- **Typed retry logic** — distinguishes rate-limit errors from genuine
  failures and raises specific domain exceptions rather than raw
  ``yfinance`` errors.
- **User-Agent rotation** — reduces the probability of being throttled
  on shared Streamlit Cloud egress IPs.
- **Timeout enforcement** — prevents UI freezes on slow Yahoo responses.

All public methods are synchronous and safe to call from Streamlit's
main thread.  They never raise bare ``Exception``; callers receive
specific subclasses of :class:`~core.exceptions.FinSightError`.

Usage::

    from core.data.stock_client import StockClient
    client = StockClient()
    info    = client.get_info("AAPL")
    history = client.get_history("AAPL", period="1y")
"""

from __future__ import annotations

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
from core.logger import get_logger

log = get_logger(__name__)

# ── User-Agent pool ───────────────────────────────────────────
# Rotate across realistic browser strings to reduce shared-IP throttling.
_USER_AGENTS: list[str] = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.3 Safari/605.1.15"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) "
        "Gecko/20100101 Firefox/124.0"
    ),
]

# ── Rate-limit keyword detection ──────────────────────────────
_RATE_KEYWORDS = frozenset(
    {"too many requests", "rate limit", "429", "quota exceeded"}
)
_TIMEOUT_KEYWORDS = frozenset(
    {"timed out", "timeout", "read timeout", "connection timeout"}
)


def _classify_error(exc: Exception, ticker: str) -> FinSightError:  # type: ignore[name-defined]
    """Map a raw exception from yfinance to a typed domain exception.

    Args:
        exc:    The raw exception raised by yfinance or requests.
        ticker: The ticker symbol being fetched at the time of failure.

    Returns:
        A specific :class:`~core.exceptions.FinSightError` subclass.
    """
    from core.exceptions import FinSightError  # avoid circular at module level

    msg = str(exc).lower()
    if any(k in msg for k in _RATE_KEYWORDS):
        return RateLimitError(ticker)
    if any(k in msg for k in _TIMEOUT_KEYWORDS):
        return NetworkTimeoutError(ticker, settings.yfinance_timeout)
    return DataFetchError(f"yfinance error for '{ticker}': {exc}", ticker=ticker)


# ── TTL in-memory cache ───────────────────────────────────────

@dataclass(slots=True)
class _CacheEntry:
    value: Any
    expires_at: float


class _TTLCache:
    """Simple in-memory TTL cache with no external dependencies.

    Args:
        ttl: Time-to-live in seconds for each cached entry.
    """

    def __init__(self, ttl: int) -> None:
        self._ttl = ttl
        self._store: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        """Return the cached value for *key*, or ``None`` if expired/absent."""
        entry = self._store.get(key)
        if entry is None or time.monotonic() > entry.expires_at:
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key* for ``self._ttl`` seconds."""
        self._store[key] = _CacheEntry(
            value=value,
            expires_at=time.monotonic() + self._ttl,
        )

    def clear(self) -> None:
        """Evict all cached entries."""
        self._store.clear()


# ── Return model ──────────────────────────────────────────────

@dataclass
class StockInfo:
    """Normalised summary of a ticker's fundamental data.

    All optional fields are ``None`` when Yahoo Finance does not provide
    the value (e.g. ETFs have no P/E ratio).

    Attributes:
        ticker:              Normalised upper-case symbol.
        name:                Full company or fund name.
        sector:              GICS sector string, or ``"N/A"``.
        industry:            GICS industry string, or ``"N/A"``.
        market_cap:          Total market capitalisation in USD.
        pe_ratio:            Trailing 12-month price-to-earnings.
        forward_pe:          Next-12-month estimated P/E.
        eps:                 Trailing 12-month earnings per share.
        dividend_yield:      Annual dividend yield as a decimal (0.02 = 2%).
        fifty_two_week_high: 52-week intraday high.
        fifty_two_week_low:  52-week intraday low.
        current_price:       Most recent price (real-time or prior close).
        currency:            ISO 4217 currency code (e.g. ``"USD"``).
        raw:                 Full ``yfinance`` info dict for advanced use.
    """

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
    """Fault-tolerant yfinance client with caching and typed exceptions.

    Designed to be instantiated once per Streamlit session and stored in
    ``st.session_state`` to persist the in-memory cache across reruns.

    Args:
        cache_ttl: Seconds to cache successful responses.
                   Defaults to ``settings.yfinance_cache_ttl``.
    """

    def __init__(self, cache_ttl: int | None = None) -> None:
        self._cache = _TTLCache(ttl=cache_ttl or settings.yfinance_cache_ttl)
        self._max_retries = settings.yfinance_max_retries
        self._timeout = settings.yfinance_timeout

    # ── Private helpers ───────────────────────────────────────

    def _make_ticker(self, symbol: str) -> yf.Ticker:
        """Construct a ``yf.Ticker`` with a randomised User-Agent."""
        ticker = yf.Ticker(symbol)
        try:
            session = requests.Session()
            session.headers["User-Agent"] = random.choice(_USER_AGENTS)
            ticker._session = session  # type: ignore[attr-defined]
        except Exception:
            pass  # Best-effort; yfinance works without a custom session
        return ticker

    def _fetch_with_retry(self, fn: Any, ticker: str) -> Any:
        """Execute *fn* with exponential-backoff retry on rate limits.

        Args:
            fn:     Zero-argument callable that performs the network call.
            ticker: Symbol for error attribution.

        Returns:
            The return value of *fn* on success.

        Raises:
            RateLimitError:      After exhausting all retry attempts.
            NetworkTimeoutError: On request timeout.
            DataFetchError:      On any other non-retriable error.
        """
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                domain_exc = _classify_error(exc, ticker)
                last_exc = domain_exc

                if isinstance(domain_exc, RateLimitError) and attempt < self._max_retries:
                    wait = 2 ** attempt + random.uniform(0.0, 1.0)
                    log.warning(
                        "rate_limited_retrying attempt=%d/%d wait=%.1fs ticker=%s",
                        attempt, self._max_retries, wait, ticker,
                    )
                    time.sleep(wait)
                else:
                    raise domain_exc from exc

        raise last_exc  # type: ignore[misc]

    # ── Public API ────────────────────────────────────────────

    def get_info(self, ticker: str) -> StockInfo:
        """Fetch and normalise fundamental data for *ticker*.

        Args:
            ticker: Ticker symbol (e.g. ``"AAPL"``). Case-insensitive.

        Returns:
            A :class:`StockInfo` dataclass populated from Yahoo Finance.

        Raises:
            TickerNotFoundError:  If Yahoo returns no recognisable data.
            RateLimitError:       After exhausting rate-limit retries.
            NetworkTimeoutError:  If the request times out.
            DataFetchError:       For any other network/parse failure.
        """
        symbol = ticker.upper().strip()
        cache_key = f"info:{symbol}"

        if cached := self._cache.get(cache_key):
            log.debug("cache_hit key=%s", cache_key)
            return cached  # type: ignore[return-value]

        log.info("fetching_info ticker=%s", symbol)
        raw: dict[str, Any] = self._fetch_with_retry(
            lambda: self._make_ticker(symbol).info,
            ticker=symbol,
        )

        # Validate that Yahoo returned a real ticker, not an empty dict
        if not raw or not (raw.get("symbol") or raw.get("shortName") or raw.get("longName")):
            raise TickerNotFoundError(symbol)

        def _get(key: str) -> Any:
            return raw.get(key)

        info = StockInfo(
            ticker             = symbol,
            name               = _get("longName") or _get("shortName") or symbol,
            sector             = _get("sector")   or "N/A",
            industry           = _get("industry") or "N/A",
            market_cap         = _get("marketCap"),
            pe_ratio           = _get("trailingPE"),
            forward_pe         = _get("forwardPE"),
            eps                = _get("trailingEps"),
            dividend_yield     = _get("dividendYield"),
            fifty_two_week_high= _get("fiftyTwoWeekHigh"),
            fifty_two_week_low = _get("fiftyTwoWeekLow"),
            current_price      = (
                _get("currentPrice")
                or _get("regularMarketPrice")
                or _get("previousClose")
            ),
            currency = _get("currency") or "USD",
            raw      = raw,
        )

        self._cache.set(cache_key, info)
        log.info("info_cached ticker=%s name=%s", symbol, info.name)
        return info

    def get_history(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Fetch OHLCV price history for *ticker*.

        Args:
            ticker:   Ticker symbol (e.g. ``"AAPL"``). Case-insensitive.
            period:   yfinance period string: ``"1mo"``, ``"6mo"``, ``"1y"``,
                      ``"5y"``, ``"max"``.
            interval: Bar size: ``"1d"`` (daily), ``"1wk"``, ``"1mo"``.

        Returns:
            A :class:`pandas.DataFrame` with DatetimeIndex and columns
            ``[Open, High, Low, Close, Volume]`` (auto-adjusted prices).

        Raises:
            TickerNotFoundError: If the download returns an empty DataFrame.
            RateLimitError:      After exhausting rate-limit retries.
            NetworkTimeoutError: On request timeout.
            DataFetchError:      For any other failure.
        """
        symbol    = ticker.upper().strip()
        cache_key = f"hist:{symbol}:{period}:{interval}"

        if cached := self._cache.get(cache_key):
            log.debug("cache_hit key=%s", cache_key)
            return cached  # type: ignore[return-value]

        log.info("fetching_history ticker=%s period=%s interval=%s", symbol, period, interval)
        df: pd.DataFrame = self._fetch_with_retry(
            lambda: yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
            ),
            ticker=symbol,
        )

        if df.empty:
            raise TickerNotFoundError(symbol)

        # yfinance may return a MultiIndex when downloading a single ticker
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)
        self._cache.set(cache_key, df)
        log.info("history_cached ticker=%s rows=%d", symbol, len(df))
        return df

    def get_financials(self, ticker: str) -> dict[str, pd.DataFrame]:
        """Fetch annual financial statements for *ticker*.

        Args:
            ticker: Ticker symbol. Case-insensitive.

        Returns:
            A dict with keys ``"income_statement"``, ``"balance_sheet"``,
            and ``"cash_flow"``, each containing a :class:`pandas.DataFrame`.

        Raises:
            DataFetchError: If any statement cannot be retrieved.
        """
        symbol    = ticker.upper().strip()
        cache_key = f"fin:{symbol}"

        if cached := self._cache.get(cache_key):
            return cached  # type: ignore[return-value]

        log.info("fetching_financials ticker=%s", symbol)

        def _fetch() -> dict[str, pd.DataFrame]:
            t = self._make_ticker(symbol)
            return {
                "income_statement": t.financials,
                "balance_sheet":    t.balance_sheet,
                "cash_flow":        t.cashflow,
            }

        result = self._fetch_with_retry(_fetch, ticker=symbol)
        self._cache.set(cache_key, result)
        return result

    def clear_cache(self) -> None:
        """Evict all cached entries, forcing fresh network calls."""
        self._cache.clear()
        log.info("cache_cleared")
