"""
FinSight FastAPI — Application Entry Point
===========================================
Responsibilities of this file:
  1. ASGI lifespan: initialise all heavy singletons ONCE at startup.
  2. Middleware: CORS, security headers, request-size limits.
  3. Global exception handlers: map domain exceptions → JSON, no stack traces.
  4. Router registration with /api/v1 prefix.
  5. Health check.

Run locally::

    uvicorn backend.main:app --reload --port 8000

Deploy (Docker)::

    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2
"""
from __future__ import annotations

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Ensure project root is on path when running from /backend ──
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.routers import chat, finance, rag
from api.schemas.responses import ErrorDetail, HealthResponse
from config.settings import settings
from core.data.stock_client import StockClient
from core.exceptions import (
    ContextWindowExceededError,
    DataFetchError,
    DocumentLoadError,
    DocumentParseError,
    FinSightError,
    IndexNotFoundError,
    LLMError,
    LLMRateLimitError,
    NetworkTimeoutError,
    RateLimitError,
    TickerNotFoundError,
)
from core.llm.claude_client import ClaudeClient
from core.logger import configure_logging
from core.rag.pipeline import RAGPipeline

configure_logging(settings.log_level)
log = logging.getLogger("finsight.main")


# ══════════════════════════════════════════════════════════════
# LIFESPAN — init singletons once, tear down cleanly
# ══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    ASGI lifespan context manager.

    Startup:
      - Initialise StockClient (installs requests-cache SQLite).
      - Initialise ClaudeClient (validates API key early).
      - Initialise RAGPipeline (loads persisted FAISS index if present).
      - Create the in-memory job_store dict.

    Shutdown:
      - Log clean exit (add DB teardown here if needed).
    """
    log.info("startup_begin version=%s env=%s", settings.app_version, settings.app_env)

    # ── Initialise core singletons ────────────────────────────
    try:
        app.state.stock_client  = StockClient()
        log.info("startup_stock_client_ok")

        app.state.claude_client = ClaudeClient()
        log.info("startup_claude_client_ok model=%s", settings.claude_model)

        app.state.rag_pipeline  = RAGPipeline()
        log.info("startup_rag_pipeline_ok")

        app.state.job_store: dict = {}
        log.info("startup_job_store_ok")

    except RuntimeError as exc:
        # ANTHROPIC_API_KEY missing — fail fast with a clear message
        log.critical("startup_failed reason=%s", exc)
        raise

    log.info("startup_complete — all singletons ready")
    yield
    # ── Shutdown ──────────────────────────────────────────────
    log.info("shutdown_complete")


# ══════════════════════════════════════════════════════════════
# APP FACTORY
# ══════════════════════════════════════════════════════════════

app = FastAPI(
    title       = "FinSight API",
    description = (
        "Production-grade financial analysis API. "
        "Endpoints for stock data, technical analysis, "
        "document RAG, and Claude-powered AI chat."
    ),
    version     = settings.app_version,
    docs_url    = "/docs"  if not settings.is_production else None,
    redoc_url   = "/redoc" if not settings.is_production else None,
    openapi_url = "/openapi.json" if not settings.is_production else None,
    lifespan    = lifespan,
)


# ══════════════════════════════════════════════════════════════
# MIDDLEWARE
# ══════════════════════════════════════════════════════════════

# ── CORS ──────────────────────────────────────────────────────
_ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins     = _ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers     = ["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers    = ["X-Request-ID", "Retry-After"],
    max_age           = 600,
)


# ── Security headers + request timing ─────────────────────────
@app.middleware("http")
async def security_and_timing_middleware(request: Request, call_next):
    """
    Add security headers to every response and log request timing.
    Also enforces a maximum request body size to prevent DDoS via
    huge uploads hitting routes other than /rag/upload.
    """
    start = time.perf_counter()

    # Block oversized bodies on non-upload routes (25 MB absolute cap)
    if request.url.path != "/api/v1/rag/upload":
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 1 * 1024 * 1024:  # 1 MB cap elsewhere
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"code": "REQUEST_TOO_LARGE", "message": "Request body exceeds 1 MB limit."},
            )

    response = await call_next(request)

    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"]         = "DENY"
    response.headers["Referrer-Policy"]          = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"]         = "1; mode=block"

    log.info(
        "request method=%s path=%s status=%d ms=%.1f",
        request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response


# ══════════════════════════════════════════════════════════════
# GLOBAL EXCEPTION HANDLERS
# Maps every FinSight domain exception → structured JSON response.
# Stack traces NEVER reach the client.
# ══════════════════════════════════════════════════════════════

def _error_response(
    status_code: int,
    code: str,
    message: str,
    retry_after: int | None = None,
) -> JSONResponse:
    body = ErrorDetail(code=code, message=message, retry_after=retry_after)
    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(
        status_code = status_code,
        content     = body.model_dump(exclude_none=True),
        headers     = headers,
    )


@app.exception_handler(TickerNotFoundError)
async def ticker_not_found_handler(request: Request, exc: TickerNotFoundError) -> JSONResponse:
    return _error_response(404, "TICKER_NOT_FOUND", str(exc))


@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    return _error_response(429, "RATE_LIMIT_ERROR", str(exc), retry_after=exc.retry_after)


@app.exception_handler(NetworkTimeoutError)
async def timeout_handler(request: Request, exc: NetworkTimeoutError) -> JSONResponse:
    return _error_response(504, "NETWORK_TIMEOUT", str(exc))


@app.exception_handler(DataFetchError)
async def data_fetch_handler(request: Request, exc: DataFetchError) -> JSONResponse:
    return _error_response(502, "DATA_FETCH_ERROR", str(exc))


@app.exception_handler(LLMRateLimitError)
async def llm_rate_limit_handler(request: Request, exc: LLMRateLimitError) -> JSONResponse:
    return _error_response(429, "LLM_RATE_LIMIT", str(exc), retry_after=exc.retry_after)


@app.exception_handler(ContextWindowExceededError)
async def context_window_handler(request: Request, exc: ContextWindowExceededError) -> JSONResponse:
    return _error_response(422, "CONTEXT_WINDOW_EXCEEDED", str(exc))


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    return _error_response(502, "LLM_ERROR", "AI service temporarily unavailable.")


@app.exception_handler(DocumentParseError)
async def doc_parse_handler(request: Request, exc: DocumentParseError) -> JSONResponse:
    return _error_response(422, "DOCUMENT_PARSE_ERROR", str(exc))


@app.exception_handler(DocumentLoadError)
async def doc_load_handler(request: Request, exc: DocumentLoadError) -> JSONResponse:
    return _error_response(400, "DOCUMENT_LOAD_ERROR", str(exc))


@app.exception_handler(IndexNotFoundError)
async def index_not_found_handler(request: Request, exc: IndexNotFoundError) -> JSONResponse:
    return _error_response(404, "INDEX_NOT_FOUND", str(exc))


@app.exception_handler(FinSightError)
async def finsight_base_handler(request: Request, exc: FinSightError) -> JSONResponse:
    """Catch-all for any FinSightError subclass not handled above."""
    log.error("unhandled_finsight_error type=%s msg=%s", type(exc).__name__, exc)
    return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Final safety net — never let a stack trace leak to the client."""
    log.exception("unhandled_exception path=%s", request.url.path)
    return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")


# ══════════════════════════════════════════════════════════════
# ROUTERS
# ══════════════════════════════════════════════════════════════

API_PREFIX = "/api/v1"

app.include_router(finance.router, prefix=API_PREFIX)
app.include_router(chat.router,    prefix=API_PREFIX)
app.include_router(rag.router,     prefix=API_PREFIX)


# ══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Liveness check",
)
async def health() -> HealthResponse:
    """Returns 200 when the server is up. Used by Docker/k8s probes."""
    return HealthResponse(version=settings.app_version)
