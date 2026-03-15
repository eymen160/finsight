"""
FinSight — Finance Router
===========================
Endpoints:
  GET  /api/v1/finance/info/{ticker}      → Fundamental data
  GET  /api/v1/finance/history/{ticker}   → OHLCV bars
  GET  /api/v1/finance/signals/{ticker}   → Technical signals + bias
  POST /api/v1/finance/analysis           → Full analysis (non-streaming)

All heavy I/O runs in the thread pool via the service layer.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status

from api.dependencies import LoggerDep, StockClientDep
from api.schemas.requests import StockAnalysisRequest
from api.schemas.responses import (
    OHLCVBar,
    SignalValue,
    StockHistoryResponse,
    StockInfoResponse,
    TechnicalSignalsResponse,
)
from api.services.finance_service import (
    compute_technical_analysis,
    dataframe_to_bars,
    fetch_ohlcv,
    fetch_stock_info,
    safe_float,
)
from core.exceptions import (
    DataFetchError,
    NetworkTimeoutError,
    RateLimitError,
    TickerNotFoundError,
)

router = APIRouter(prefix="/finance", tags=["Finance"])


# ── Helper: map domain exceptions → HTTP ─────────────────────

def _raise_http(exc: Exception) -> None:
    """Re-raise a core domain exception as the appropriate HTTPException."""
    if isinstance(exc, TickerNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TICKER_NOT_FOUND", "message": str(exc)},
        )
    if isinstance(exc, RateLimitError):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMIT_ERROR",
                "message": str(exc),
                "retry_after": getattr(exc, "retry_after", 60),
            },
        )
    if isinstance(exc, NetworkTimeoutError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "NETWORK_TIMEOUT", "message": str(exc)},
        )
    if isinstance(exc, DataFetchError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "DATA_FETCH_ERROR", "message": str(exc)},
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
    )


# ── Routes ────────────────────────────────────────────────────

@router.get(
    "/info/{ticker}",
    response_model=StockInfoResponse,
    summary="Get fundamental data for a ticker",
    responses={
        404: {"description": "Ticker not found"},
        429: {"description": "Yahoo Finance rate limit"},
        504: {"description": "Network timeout"},
    },
)
async def get_stock_info(
    ticker: str,
    stock: StockClientDep,
    log: LoggerDep,
) -> StockInfoResponse:
    """Fetch normalised fundamental data (name, P/E, market cap, etc.)."""
    log.info("GET /info/%s", ticker)
    try:
        info = await fetch_stock_info(stock, ticker.upper())
    except Exception as exc:
        _raise_http(exc)

    return StockInfoResponse.model_validate(info)


@router.get(
    "/history/{ticker}",
    response_model=StockHistoryResponse,
    summary="Get OHLCV price history",
)
async def get_stock_history(
    ticker: str,
    stock: StockClientDep,
    log: LoggerDep,
    period: str = Query(default="1y", description="yfinance period string"),
    interval: str = Query(default="1d", description="Bar size: 1d / 1wk / 1mo"),
) -> StockHistoryResponse:
    """Return OHLCV bars for the requested period."""
    log.info("GET /history/%s period=%s", ticker, period)
    try:
        df = await fetch_ohlcv(stock, ticker.upper(), period, interval)
    except Exception as exc:
        _raise_http(exc)

    bars = [OHLCVBar(**b) for b in dataframe_to_bars(df)]
    return StockHistoryResponse(
        ticker     = ticker.upper(),
        period     = period,
        interval   = interval,
        bars       = bars,
        total_bars = len(bars),
    )


@router.get(
    "/signals/{ticker}",
    response_model=TechnicalSignalsResponse,
    summary="Get technical indicator signals",
)
async def get_technical_signals(
    ticker: str,
    stock: StockClientDep,
    log: LoggerDep,
    period: str = Query(default="1y"),
) -> TechnicalSignalsResponse:
    """Compute RSI, MACD, BB, SMA signals and return aggregate bias."""
    log.info("GET /signals/%s period=%s", ticker, period)
    try:
        result = await compute_technical_analysis(stock, ticker.upper(), period)
    except Exception as exc:
        _raise_http(exc)

    df      = result["df"]
    signals = result["signals"]
    bias    = result["bias"]
    last    = df.iloc[-1] if not df.empty else None

    return TechnicalSignalsResponse(
        ticker             = ticker.upper(),
        period             = period,
        signals            = {k: SignalValue(v) for k, v in signals.items()},
        bias               = SignalValue(bias),
        latest_close       = safe_float(last.get("Close"))      if last is not None else None,
        latest_rsi         = safe_float(last.get("rsi_14"))     if last is not None else None,
        latest_macd        = safe_float(last.get("macd"))       if last is not None else None,
        latest_macd_signal = safe_float(last.get("macd_signal"))if last is not None else None,
    )
