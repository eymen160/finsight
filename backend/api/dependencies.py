"""
FinSight FastAPI — Dependency Injection
=========================================
All heavy singletons are initialised once during the ASGI lifespan
and stored on ``app.state``.  Route handlers receive them via ``Depends()``,
keeping handler signatures clean and making unit-testing trivial
(just override the dependency).

Usage in a route::

    @router.get("/something")
    async def handler(
        stock: StockClient   = Depends(get_stock_client),
        claude: ClaudeClient = Depends(get_claude_client),
        rag: RAGPipeline     = Depends(get_rag_pipeline),
        log: logging.Logger  = Depends(get_logger),
    ) -> ...:
        ...
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, Request

# Core module types — imported for annotation only
# The actual objects live on app.state, set during lifespan.
from core.data.stock_client import StockClient
from core.llm.claude_client import ClaudeClient
from core.rag.pipeline import RAGPipeline


# ── Provider functions ────────────────────────────────────────

def get_stock_client(request: Request) -> StockClient:
    """Return the process-wide StockClient from app.state."""
    return request.app.state.stock_client


def get_claude_client(request: Request) -> ClaudeClient:
    """Return the process-wide ClaudeClient from app.state."""
    return request.app.state.claude_client


def get_rag_pipeline(request: Request) -> RAGPipeline:
    """Return the process-wide RAGPipeline from app.state."""
    return request.app.state.rag_pipeline


def get_job_store(request: Request) -> dict:
    """Return the in-memory background-job status store from app.state."""
    return request.app.state.job_store


def get_logger(request: Request) -> logging.Logger:
    """Return a route-level logger tagged with the request path."""
    return logging.getLogger(f"finsight.api{request.url.path}")


# ── Annotated aliases (cleaner DI syntax in route signatures) ─

StockClientDep  = Annotated[StockClient,  Depends(get_stock_client)]
ClaudeClientDep = Annotated[ClaudeClient, Depends(get_claude_client)]
RAGPipelineDep  = Annotated[RAGPipeline,  Depends(get_rag_pipeline)]
JobStoreDep     = Annotated[dict,         Depends(get_job_store)]
LoggerDep       = Annotated[logging.Logger, Depends(get_logger)]
