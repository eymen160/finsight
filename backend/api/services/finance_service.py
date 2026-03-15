"""
FinSight — Finance Service
============================
Glue layer between FastAPI route handlers and the core
``StockClient`` / ``technical`` modules.  All business logic lives
here; route handlers stay thin.

Service methods are ``async`` so they can be called from async
route handlers, even though the underlying yfinance calls are
synchronous.  Heavy I/O is offloaded to the default thread pool
via ``asyncio.to_thread``.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import pandas as pd

from core.analysis.technical import add_indicators, get_signals, signal_summary
from core.data.stock_client import StockClient, StockInfo
from core.exceptions import DataFetchError, TickerNotFoundError

log = logging.getLogger(__name__)


async def fetch_stock_info(
    client: StockClient,
    ticker: str,
) -> StockInfo:
    """Async wrapper: fetch fundamental data for *ticker*.

    Args:
        client: Injected StockClient singleton.
        ticker: Normalised ticker symbol.

    Returns:
        Populated :class:`~core.data.stock_client.StockInfo`.

    Raises:
        TickerNotFoundError, RateLimitError, DataFetchError.
    """
    log.info("service.fetch_info ticker=%s", ticker)
    return await asyncio.to_thread(client.get_info, ticker)


async def fetch_ohlcv(
    client: StockClient,
    ticker: str,
    period: str,
    interval: str = "1d",
) -> pd.DataFrame:
    """Async wrapper: fetch OHLCV price history.

    Args:
        client:   Injected StockClient singleton.
        ticker:   Normalised ticker symbol.
        period:   yfinance period string.
        interval: Bar size.

    Returns:
        DataFrame with DatetimeIndex and OHLCV columns.
    """
    log.info("service.fetch_ohlcv ticker=%s period=%s", ticker, period)
    return await asyncio.to_thread(client.get_history, ticker, period, interval)


async def compute_technical_analysis(
    client: StockClient,
    ticker: str,
    period: str,
) -> dict[str, Any]:
    """Fetch OHLCV, add indicators, and compute signals.

    Returns:
        Dict with keys: ``df`` (DataFrame), ``signals`` (SignalMap),
        ``bias`` (str), ``info`` (StockInfo).
    """
    info, df_raw = await asyncio.gather(
        fetch_stock_info(client, ticker),
        fetch_ohlcv(client, ticker, period),
    )
    df      = add_indicators(df_raw)
    signals = get_signals(df)
    bias    = signal_summary(signals)

    log.info(
        "service.technical_ok ticker=%s bias=%s n_signals=%d",
        ticker, bias, len(signals),
    )
    return {"df": df, "signals": signals, "bias": bias, "info": info}


def dataframe_to_bars(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert OHLCV DataFrame rows to serialisable dicts.

    Args:
        df: OHLCV DataFrame with DatetimeIndex.

    Returns:
        List of dicts suitable for :class:`~api.schemas.responses.OHLCVBar`.
    """
    bars = []
    for ts, row in df.iterrows():
        bars.append({
            "date":   str(ts)[:10],
            "open":   float(row.get("Open",  0)),
            "high":   float(row.get("High",  0)),
            "low":    float(row.get("Low",   0)),
            "close":  float(row.get("Close", 0)),
            "volume": float(row.get("Volume",0)),
        })
    return bars


def safe_float(value: Any) -> float | None:
    """Return float or None, swallowing NaN/None."""
    try:
        f = float(value)
        import math
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None
