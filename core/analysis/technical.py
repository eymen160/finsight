"""
FinSight — Technical Analysis
================================
Adds common technical indicators to an OHLCV DataFrame.
All functions are pure (no side effects) and return a new DataFrame.

Indicators included (Phase 1):
  - SMA  (20, 50, 200)
  - EMA  (12, 26)
  - MACD + Signal + Histogram
  - RSI  (14)
  - Bollinger Bands (20, 2σ)
  - ATR  (14)
  - Volume SMA (20)

Usage:
    from core.analysis.technical import add_indicators, get_signals
    df_with_indicators = add_indicators(raw_df)
    signals = get_signals(df_with_indicators)
"""

import pandas as pd
import ta

from core.logger import get_logger

logger = get_logger(__name__)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute technical indicators and append them as new columns.

    Args:
        df: OHLCV DataFrame with columns [Open, High, Low, Close, Volume].

    Returns:
        A copy of *df* with indicator columns appended.
    """
    df = df.copy()

    close = df["Close"].squeeze()
    high  = df["High"].squeeze()
    low   = df["Low"].squeeze()
    vol   = df["Volume"].squeeze()

    # ── Trend ─────────────────────────────────────────────────
    df["sma_20"]  = ta.trend.sma_indicator(close, window=20)
    df["sma_50"]  = ta.trend.sma_indicator(close, window=50)
    df["sma_200"] = ta.trend.sma_indicator(close, window=200)
    df["ema_12"]  = ta.trend.ema_indicator(close, window=12)
    df["ema_26"]  = ta.trend.ema_indicator(close, window=26)

    macd_obj = ta.trend.MACD(close)
    df["macd"]        = macd_obj.macd()
    df["macd_signal"] = macd_obj.macd_signal()
    df["macd_hist"]   = macd_obj.macd_diff()

    # ── Momentum ──────────────────────────────────────────────
    df["rsi_14"] = ta.momentum.rsi(close, window=14)

    # ── Volatility ────────────────────────────────────────────
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df["bb_upper"]  = bb.bollinger_hband()
    df["bb_middle"] = bb.bollinger_mavg()
    df["bb_lower"]  = bb.bollinger_lband()
    df["bb_pct"]    = bb.bollinger_pband()   # % position within bands

    df["atr_14"] = ta.volatility.average_true_range(high, low, close, window=14)

    # ── Volume ────────────────────────────────────────────────
    df["vol_sma_20"] = ta.trend.sma_indicator(vol.astype(float), window=20)

    logger.debug("indicators_added", columns=list(df.columns))
    return df


def get_signals(df: pd.DataFrame) -> dict[str, str]:
    """
    Generate human-readable buy / sell / neutral signals from
    the last completed candle.

    Returns:
        A dict mapping signal_name → "BULLISH" | "BEARISH" | "NEUTRAL".
    """
    if df.empty:
        return {}

    last = df.iloc[-1]
    signals: dict[str, str] = {}

    # RSI
    rsi = last.get("rsi_14")
    if rsi is not None:
        if rsi < 30:
            signals["RSI"] = "BULLISH"   # oversold
        elif rsi > 70:
            signals["RSI"] = "BEARISH"   # overbought
        else:
            signals["RSI"] = "NEUTRAL"

    # MACD crossover
    macd_hist = last.get("macd_hist")
    if macd_hist is not None:
        signals["MACD"] = "BULLISH" if macd_hist > 0 else "BEARISH"

    # Price vs SMAs
    close = last.get("Close")
    sma_50 = last.get("sma_50")
    sma_200 = last.get("sma_200")
    if close is not None and sma_50 is not None:
        signals["SMA_50"]  = "BULLISH" if close > sma_50  else "BEARISH"
    if close is not None and sma_200 is not None:
        signals["SMA_200"] = "BULLISH" if close > sma_200 else "BEARISH"

    # Bollinger Band position
    bb_pct = last.get("bb_pct")
    if bb_pct is not None:
        if bb_pct < 0.2:
            signals["BB"] = "BULLISH"
        elif bb_pct > 0.8:
            signals["BB"] = "BEARISH"
        else:
            signals["BB"] = "NEUTRAL"

    return signals


def signal_summary(signals: dict[str, str]) -> str:
    """
    Return an overall bias string: "BULLISH" | "BEARISH" | "MIXED".
    Simple majority vote across all signals.
    """
    if not signals:
        return "NEUTRAL"
    counts = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
    for v in signals.values():
        counts[v] = counts.get(v, 0) + 1
    if counts["BULLISH"] > counts["BEARISH"]:
        return "BULLISH"
    if counts["BEARISH"] > counts["BULLISH"]:
        return "BEARISH"
    return "MIXED"
