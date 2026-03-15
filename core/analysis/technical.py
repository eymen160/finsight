"""
FinSight — Technical Analysis Engine
========================================
Pure, side-effect-free functions that compute technical indicators and
derive actionable signals from OHLCV data.

All functions:
- Return new objects; they never mutate their inputs.
- Are fully type-annotated.
- Carry Google-style docstrings.
- Validate their inputs defensively and raise ``ValueError`` on invalid data.

Indicators (Phase 1):
    Trend:     SMA(20, 50, 200), EMA(12, 26)
    Momentum:  MACD + Signal + Histogram, RSI(14)
    Volatility: Bollinger Bands(20, 2σ), ATR(14)
    Volume:    Volume SMA(20)

Usage::

    from core.analysis.technical import add_indicators, get_signals, signal_summary
    df  = add_indicators(raw_ohlcv_df)
    sig = get_signals(df)
    print(signal_summary(sig))  # "BULLISH" | "BEARISH" | "MIXED" | "NEUTRAL"
"""

from __future__ import annotations

import logging

import pandas as pd
import ta
import ta.momentum
import ta.trend
import ta.volatility

log = logging.getLogger(__name__)

# ── Type aliases ──────────────────────────────────────────────
SignalMap = dict[str, str]
"""Mapping of indicator name → ``"BULLISH" | "BEARISH" | "NEUTRAL"``."""

_VALID_SIGNALS = frozenset({"BULLISH", "BEARISH", "NEUTRAL"})
_REQUIRED_COLS = frozenset({"Open", "High", "Low", "Close", "Volume"})


def _validate_ohlcv(df: pd.DataFrame) -> None:
    """Assert that *df* has the expected OHLCV columns and is non-empty.

    Args:
        df: DataFrame to validate.

    Raises:
        ValueError: If required columns are missing or *df* is empty.
    """
    if df.empty:
        raise ValueError("OHLCV DataFrame is empty — cannot compute indicators.")
    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute technical indicators and append them as new columns.

    Args:
        df: OHLCV DataFrame with columns
            ``[Open, High, Low, Close, Volume]`` and a DatetimeIndex.
            The DataFrame is **not** mutated.

    Returns:
        A copy of *df* with the following additional columns:

        ============  ===========================================
        Column        Description
        ============  ===========================================
        sma_20        Simple moving average, 20-period
        sma_50        Simple moving average, 50-period
        sma_200       Simple moving average, 200-period
        ema_12        Exponential moving average, 12-period
        ema_26        Exponential moving average, 26-period
        macd          MACD line (EMA12 − EMA26)
        macd_signal   Signal line (9-period EMA of MACD)
        macd_hist     MACD histogram (MACD − Signal)
        rsi_14        Relative Strength Index, 14-period
        bb_upper      Bollinger Band upper (SMA20 + 2σ)
        bb_middle     Bollinger Band middle (SMA20)
        bb_lower      Bollinger Band lower (SMA20 − 2σ)
        bb_pct        BB %B — price position within bands [0, 1]
        atr_14        Average True Range, 14-period
        vol_sma_20    Volume simple moving average, 20-period
        ============  ===========================================

    Raises:
        ValueError: If *df* is empty or missing required columns.
    """
    _validate_ohlcv(df)
    out = df.copy()

    # Squeeze in case yfinance returns a single-column MultiIndex
    close = out["Close"].squeeze()
    high  = out["High"].squeeze()
    low   = out["Low"].squeeze()
    vol   = out["Volume"].squeeze()

    # ── Trend ─────────────────────────────────────────────────
    out["sma_20"]  = ta.trend.sma_indicator(close, window=20)
    out["sma_50"]  = ta.trend.sma_indicator(close, window=50)
    out["sma_200"] = ta.trend.sma_indicator(close, window=200)
    out["ema_12"]  = ta.trend.ema_indicator(close, window=12)
    out["ema_26"]  = ta.trend.ema_indicator(close, window=26)

    macd = ta.trend.MACD(close)
    out["macd"]        = macd.macd()
    out["macd_signal"] = macd.macd_signal()
    out["macd_hist"]   = macd.macd_diff()

    # ── Momentum ──────────────────────────────────────────────
    out["rsi_14"] = ta.momentum.rsi(close, window=14)

    # ── Volatility ────────────────────────────────────────────
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    out["bb_upper"]  = bb.bollinger_hband()
    out["bb_middle"] = bb.bollinger_mavg()
    out["bb_lower"]  = bb.bollinger_lband()
    out["bb_pct"]    = bb.bollinger_pband()

    out["atr_14"] = ta.volatility.average_true_range(high, low, close, window=14)

    # ── Volume ────────────────────────────────────────────────
    out["vol_sma_20"] = ta.trend.sma_indicator(vol.astype(float), window=20)

    log.debug("indicators_added n_cols=%d n_rows=%d", len(out.columns), len(out))
    return out


def get_signals(df: pd.DataFrame) -> SignalMap:
    """Derive actionable signals from the most recent bar in *df*.

    Each signal uses a well-known rule:

    - **RSI**: oversold (<30) → BULLISH; overbought (>70) → BEARISH.
    - **MACD**: histogram positive → BULLISH; negative → BEARISH.
    - **SMA_50 / SMA_200**: price above → BULLISH; below → BEARISH.
    - **BB**: price in lower 20% of band → BULLISH; upper 80% → BEARISH.

    Args:
        df: DataFrame returned by :func:`add_indicators`.

    Returns:
        A :data:`SignalMap` mapping indicator name to signal string.
        Returns an empty dict if *df* is empty or no indicator columns
        are present.
    """
    if df.empty:
        log.debug("get_signals called on empty DataFrame — returning {}")
        return {}

    last: pd.Series = df.iloc[-1]
    signals: SignalMap = {}

    def _safe(col: str) -> float | None:
        """Return the scalar value of *col* in the last row, or None."""
        val = last.get(col)
        try:
            return float(val) if val is not None and not pd.isna(val) else None
        except (TypeError, ValueError):
            return None

    # RSI
    if (rsi := _safe("rsi_14")) is not None:
        signals["RSI"] = "BULLISH" if rsi < 30 else ("BEARISH" if rsi > 70 else "NEUTRAL")

    # MACD histogram
    if (hist := _safe("macd_hist")) is not None:
        signals["MACD"] = "BULLISH" if hist > 0 else "BEARISH"

    # Price vs SMA 50 / 200
    close = _safe("Close")
    for label, col in [("SMA_50", "sma_50"), ("SMA_200", "sma_200")]:
        if close is not None and (sma := _safe(col)) is not None:
            signals[label] = "BULLISH" if close > sma else "BEARISH"

    # Bollinger Band %B
    if (pct := _safe("bb_pct")) is not None:
        signals["BB"] = "BULLISH" if pct < 0.2 else ("BEARISH" if pct > 0.8 else "NEUTRAL")

    log.debug("signals_computed n=%d signals=%s", len(signals), signals)
    return signals


def signal_summary(signals: SignalMap) -> str:
    """Aggregate individual signals into a single overall bias string.

    Uses a simple majority-vote algorithm:
    - More BULLISH than BEARISH → ``"BULLISH"``
    - More BEARISH than BULLISH → ``"BEARISH"``
    - Equal counts or empty → ``"MIXED"`` / ``"NEUTRAL"``

    Args:
        signals: A :data:`SignalMap` as returned by :func:`get_signals`.

    Returns:
        One of ``"BULLISH"``, ``"BEARISH"``, ``"MIXED"``, or ``"NEUTRAL"``.
    """
    if not signals:
        return "NEUTRAL"

    counts: dict[str, int] = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
    for value in signals.values():
        counts[value] = counts.get(value, 0) + 1

    if counts["BULLISH"] > counts["BEARISH"]:
        return "BULLISH"
    if counts["BEARISH"] > counts["BULLISH"]:
        return "BEARISH"
    if counts["BULLISH"] == 0 and counts["BEARISH"] == 0:
        return "NEUTRAL"
    return "MIXED"
