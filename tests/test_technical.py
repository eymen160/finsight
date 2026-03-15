"""
Unit tests for core.analysis.technical
"""

import numpy as np
import pandas as pd
import pytest

from core.analysis.technical import add_indicators, get_signals, signal_summary


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Generate 250 rows of synthetic OHLCV data."""
    rng = np.random.default_rng(42)
    n = 250
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high  = close + rng.uniform(0.5, 2.0, n)
    low   = close - rng.uniform(0.5, 2.0, n)
    open_ = close + rng.normal(0, 0.5, n)
    vol   = rng.integers(1_000_000, 10_000_000, n).astype(float)

    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=dates,
    )


class TestAddIndicators:
    def test_returns_dataframe(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_input(self, sample_ohlcv):
        original_cols = list(sample_ohlcv.columns)
        add_indicators(sample_ohlcv)
        assert list(sample_ohlcv.columns) == original_cols

    def test_expected_columns_present(self, sample_ohlcv):
        df = add_indicators(sample_ohlcv)
        expected = [
            "sma_20", "sma_50", "sma_200",
            "ema_12", "ema_26",
            "macd", "macd_signal", "macd_hist",
            "rsi_14",
            "bb_upper", "bb_middle", "bb_lower", "bb_pct",
            "atr_14",
            "vol_sma_20",
        ]
        for col in expected:
            assert col in df.columns, f"Missing column: {col}"

    def test_rsi_bounds(self, sample_ohlcv):
        df = add_indicators(sample_ohlcv)
        rsi = df["rsi_14"].dropna()
        assert (rsi >= 0).all() and (rsi <= 100).all()


class TestGetSignals:
    def test_returns_dict(self, sample_ohlcv):
        df = add_indicators(sample_ohlcv)
        signals = get_signals(df)
        assert isinstance(signals, dict)

    def test_valid_values(self, sample_ohlcv):
        df = add_indicators(sample_ohlcv)
        valid = {"BULLISH", "BEARISH", "NEUTRAL"}
        for k, v in get_signals(df).items():
            assert v in valid, f"Signal '{k}' has invalid value '{v}'"

    def test_empty_dataframe(self):
        assert get_signals(pd.DataFrame()) == {}


class TestSignalSummary:
    def test_bullish_majority(self):
        signals = {"A": "BULLISH", "B": "BULLISH", "C": "BEARISH"}
        assert signal_summary(signals) == "BULLISH"

    def test_bearish_majority(self):
        signals = {"A": "BEARISH", "B": "BEARISH", "C": "BULLISH"}
        assert signal_summary(signals) == "BEARISH"

    def test_tie_returns_mixed(self):
        signals = {"A": "BULLISH", "B": "BEARISH"}
        assert signal_summary(signals) == "MIXED"

    def test_empty_returns_neutral(self):
        assert signal_summary({}) == "NEUTRAL"
