"""
FinSight — Technical Analysis Engine
========================================
Pure, side-effect-free functions that add technical indicators to OHLCV
DataFrames and derive human-readable signals from the most recent bar.

All functions:
- Return new objects; inputs are never mutated.
- Are fully type-annotated.
- Raise ``ValueError`` on invalid input rather than silently returning NaN.

Indicators:
    Trend     : SMA(20, 50, 200), EMA(12, 26)
    Momentum  : MACD + Signal + Histogram, RSI(14)
    Volatility: Bollinger Bands(20, 2σ), ATR(14)
    Volume    : Volume SMA(20)

Usage::

    from core.analysis.technical import add_indicators, get_signals, signal_summary
    df      = add_indicators(raw_ohlcv_df)
    signals = get_signals(df)
    bias    = signal_summary(signals)   # "BULLISH" | "BEARISH" | "MIXED" | "NEUTRAL"
"""
from __future__ import annotations

import logging

import pandas as pd
import ta
import ta.momentum
import ta.trend
import ta.volatility

log = logging.getLogger(__name__)

# ── Type alias ────────────────────────────────────────────────
SignalMap = dict[str, str]
"""``{indicator_name: "BULLISH" | "BEARISH" | "NEUTRAL"}``"""

_REQUIRED_COLS = frozenset({"Open", "High", "Low", "Close", "Volume"})


def _validate(df: pd.DataFrame) -> None:
    """Assert *df* has required OHLCV columns and is non-empty.

    Args:
        df: Input DataFrame to validate.

    Raises:
        ValueError: If *df* is empty or missing required columns.
    """
    if df.empty:
        raise ValueError("OHLCV DataFrame is empty — cannot compute indicators.")
    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute technical indicators and append them as new columns.

    Args:
        df: OHLCV DataFrame with columns ``[Open, High, Low, Close, Volume]``
            and a DatetimeIndex.  The DataFrame is **not** mutated.

    Returns:
        A copy of *df* with columns: ``sma_20``, ``sma_50``, ``sma_200``,
        ``ema_12``, ``ema_26``, ``macd``, ``macd_signal``, ``macd_hist``,
        ``rsi_14``, ``bb_upper``, ``bb_middle``, ``bb_lower``, ``bb_pct``,
        ``atr_14``, ``vol_sma_20``.

    Raises:
        ValueError: If *df* is empty or missing required columns.
    """
    _validate(df)
    out = df.copy()

    close = out["Close"].squeeze()
    high  = out["High"].squeeze()
    low   = out["Low"].squeeze()
    vol   = out["Volume"].squeeze()

    # Trend
    out["sma_20"]  = ta.trend.sma_indicator(close, window=20)
    out["sma_50"]  = ta.trend.sma_indicator(close, window=50)
    out["sma_200"] = ta.trend.sma_indicator(close, window=200)
    out["ema_12"]  = ta.trend.ema_indicator(close, window=12)
    out["ema_26"]  = ta.trend.ema_indicator(close, window=26)

    _macd = ta.trend.MACD(close)
    out["macd"]        = _macd.macd()
    out["macd_signal"] = _macd.macd_signal()
    out["macd_hist"]   = _macd.macd_diff()

    # Momentum
    out["rsi_14"] = ta.momentum.rsi(close, window=14)

    # Volatility
    _bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    out["bb_upper"]  = _bb.bollinger_hband()
    out["bb_middle"] = _bb.bollinger_mavg()
    out["bb_lower"]  = _bb.bollinger_lband()
    out["bb_pct"]    = _bb.bollinger_pband()

    out["atr_14"] = ta.volatility.average_true_range(high, low, close, window=14)

    # Volume
    out["vol_sma_20"] = ta.trend.sma_indicator(vol.astype(float), window=20)

    log.debug("indicators_added rows=%d cols=%d", len(out), len(out.columns))
    return out


def get_signals(df: pd.DataFrame) -> SignalMap:
    """Derive actionable signals from the most recent bar.

    Signal rules:
    - **RSI**    : < 30 → BULLISH (oversold); > 70 → BEARISH (overbought).
    - **MACD**   : histogram > 0 → BULLISH; < 0 → BEARISH.
    - **SMA_50** : close > SMA50  → BULLISH; else BEARISH.
    - **SMA_200**: close > SMA200 → BULLISH; else BEARISH.
    - **BB**     : BB%B < 0.2 → BULLISH; > 0.8 → BEARISH.

    Args:
        df: DataFrame returned by :func:`add_indicators`.

    Returns:
        :data:`SignalMap` mapping indicator name to signal string.
        Returns ``{}`` if *df* is empty.
    """
    if df.empty:
        return {}

    last = df.iloc[-1]
    signals: SignalMap = {}

    def _f(col: str) -> float | None:
        """Safely extract a scalar float from the last row."""
        v = last.get(col)
        try:
            return float(v) if v is not None and not pd.isna(v) else None
        except (TypeError, ValueError):
            return None

    if (rsi := _f("rsi_14")) is not None:
        signals["RSI"] = "BULLISH" if rsi < 30 else ("BEARISH" if rsi > 70 else "NEUTRAL")

    if (hist := _f("macd_hist")) is not None:
        signals["MACD"] = "BULLISH" if hist > 0 else "BEARISH"

    close = _f("Close")
    for label, col in [("SMA_50", "sma_50"), ("SMA_200", "sma_200")]:
        if close is not None and (sma := _f(col)) is not None:
            signals[label] = "BULLISH" if close > sma else "BEARISH"

    if (pct := _f("bb_pct")) is not None:
        signals["BB"] = "BULLISH" if pct < 0.2 else ("BEARISH" if pct > 0.8 else "NEUTRAL")

    log.debug("signals n=%d %s", len(signals), signals)
    return signals


def signal_summary(signals: SignalMap) -> str:
    """Aggregate individual signals into a single overall bias.

    Uses majority-vote: more BULLISH → ``"BULLISH"``,
    more BEARISH → ``"BEARISH"``, tie → ``"MIXED"``, empty → ``"NEUTRAL"``.

    Args:
        signals: :data:`SignalMap` from :func:`get_signals`.

    Returns:
        One of ``"BULLISH"``, ``"BEARISH"``, ``"MIXED"``, ``"NEUTRAL"``.
    """
    if not signals:
        return "NEUTRAL"
    b = sum(1 for v in signals.values() if v == "BULLISH")
    r = sum(1 for v in signals.values() if v == "BEARISH")
    if b > r:   return "BULLISH"
    if r > b:   return "BEARISH"
    if b == 0:  return "NEUTRAL"
    return "MIXED"
