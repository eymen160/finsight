"""
FinSight — Stock Analysis Service
====================================
Full analysis pipeline: fetch info + OHLCV, compute indicators,
build Claude prompt, return streaming generator — all wired together
for the /finance/analysis route.
"""
from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any

from core.data.stock_client import StockClient, StockInfo
from core.llm.claude_client import ClaudeClient
from core.analysis.technical import add_indicators, get_signals, signal_summary
from api.services.finance_service import fetch_stock_info, fetch_ohlcv


async def run_full_analysis(
    ticker: str,
    period: str,
    stock: StockClient,
    claude: ClaudeClient,
) -> tuple[StockInfo, dict[str, Any], dict[str, str], str]:
    """
    Fetch data, compute signals, and return everything needed
    for the analysis endpoint.

    Returns:
        Tuple of (info, df_dict, signals, bias).
    """
    info, df_raw = await asyncio.gather(
        fetch_stock_info(stock, ticker),
        fetch_ohlcv(stock, ticker, period),
    )
    df      = add_indicators(df_raw)
    signals = get_signals(df)
    bias    = signal_summary(signals)
    return info, df, signals, bias


def build_analysis_stream(
    ticker: str,
    period: str,
    info: StockInfo,
    signals: dict[str, str],
    bias: str,
    claude: ClaudeClient,
) -> Generator[str, None, None]:
    """
    Build and return the Claude streaming generator for analysis.
    Caller wraps this in asyncio.to_thread or an SSE generator.
    """
    messages = claude.build_analysis_prompt(
        ticker         = ticker,
        info           = info.__dict__,
        signals        = signals,
        signal_summary = bias,
        period         = period,
    )
    return claude.stream(messages)
