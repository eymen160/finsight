"""
Unit tests for core.data.stock_client

All yfinance calls are mocked — tests run offline.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from core.data.stock_client import StockClient
from core.exceptions import DataFetchError, TickerNotFoundError


@pytest.fixture
def client() -> StockClient:
    c = StockClient()
    c.clear_cache()
    return c


@pytest.fixture
def mock_info() -> dict:
    return {
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "marketCap": 3_000_000_000_000,
        "trailingPE": 28.5,
        "forwardPE": 24.0,
        "trailingEps": 6.43,
        "dividendYield": 0.005,
        "fiftyTwoWeekHigh": 200.0,
        "fiftyTwoWeekLow": 140.0,
        "currentPrice": 185.0,
        "currency": "USD",
        "symbol": "AAPL",
    }


class TestGetInfo:
    @patch("core.data.stock_client.yf.Ticker")
    def test_returns_stock_info(self, mock_ticker, client, mock_info):
        mock_ticker.return_value.info = mock_info
        info = client.get_info("AAPL")

        assert info.ticker == "AAPL"
        assert info.name == "Apple Inc."
        assert info.market_cap == 3_000_000_000_000
        assert info.pe_ratio == 28.5

    @patch("core.data.stock_client.yf.Ticker")
    def test_caches_result(self, mock_ticker, client, mock_info):
        mock_ticker.return_value.info = mock_info
        client.get_info("AAPL")
        client.get_info("AAPL")
        # yf.Ticker should only be called once due to caching
        assert mock_ticker.call_count == 1

    @patch("core.data.stock_client.yf.Ticker")
    def test_raises_on_network_error(self, mock_ticker, client):
        mock_ticker.side_effect = ConnectionError("timeout")
        with pytest.raises(DataFetchError):
            client.get_info("AAPL")


class TestGetHistory:
    @patch("core.data.stock_client.yf.download")
    def test_returns_dataframe(self, mock_download, client):
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        mock_download.return_value = pd.DataFrame(
            {"Open": [1]*5, "High": [2]*5, "Low": [0]*5, "Close": [1.5]*5, "Volume": [1000]*5},
            index=dates,
        )
        df = client.get_history("AAPL", period="1mo")
        assert not df.empty
        assert "Close" in df.columns

    @patch("core.data.stock_client.yf.download")
    def test_raises_ticker_not_found_on_empty(self, mock_download, client):
        mock_download.return_value = pd.DataFrame()
        with pytest.raises(TickerNotFoundError):
            client.get_history("INVALID_XYZ")
