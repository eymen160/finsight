"""
FinSight — RAG Service
========================
Handles the CPU/IO-heavy PDF ingestion in a background task so the
upload endpoint returns 202 immediately.

Background task flow:
  1. POST /api/v1/rag/upload  → saves temp file, enqueues job, returns 202.
  2. FastAPI BackgroundTask   → calls ``run_ingest_job`` in thread pool.
  3. GET  /api/v1/rag/jobs/{id} → client polls; returns job status.
  4. On completion: job_store entry updated with ``status="complete"``.

The job_store is a plain ``dict[str, EmbedJob]`` on ``app.state``.
For production scale, replace with Redis or a database.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.exceptions import DocumentLoadError, DocumentParseError, RAGError
from core.rag.pipeline import RAGPipeline

log = logging.getLogger(__name__)


# ── Job model ─────────────────────────────────────────────────

@dataclass
class EmbedJob:
    """Mutable record for a single PDF ingestion job."""

    job_id: str
    filename: str
    tmp_path: str
    status: str = "processing"        # "processing" | "complete" | "failed"
    chunks_indexed: int | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


# ── Service functions ─────────────────────────────────────────

def create_job(filename: str, tmp_path: str) -> EmbedJob:
    """Instantiate a new EmbedJob and return it.

    The caller is responsible for adding it to the job_store.
    """
    return EmbedJob(
        job_id   = str(uuid.uuid4()),
        filename = filename,
        tmp_path = tmp_path,
    )


async def run_ingest_job(
    job: EmbedJob,
    job_store: dict[str, EmbedJob],
    pipeline: RAGPipeline,
) -> None:
    """Background coroutine: embed the PDF and update job_store.

    Offloads the synchronous ``pipeline.ingest`` call to the default
    thread-pool executor so it doesn't block the event loop.

    Args:
        job:       The EmbedJob record (mutated in-place).
        job_store: Shared app.state dict (mutated in-place).
        pipeline:  The RAGPipeline singleton from app.state.
    """
    log.info("bg_ingest_start job_id=%s file=%s", job.job_id, job.filename)
    try:
        chunks = await asyncio.to_thread(pipeline.ingest, job.tmp_path)
        job.status         = "complete"
        job.chunks_indexed = chunks
        job.completed_at   = datetime.utcnow()
        log.info("bg_ingest_done job_id=%s chunks=%d", job.job_id, chunks)
    except (DocumentLoadError, DocumentParseError, RAGError) as exc:
        job.status       = "failed"
        job.error        = str(exc)
        job.completed_at = datetime.utcnow()
        log.error("bg_ingest_failed job_id=%s error=%s", job.job_id, exc)
    except Exception as exc:
        job.status       = "failed"
        job.error        = f"Unexpected error: {exc}"
        job.completed_at = datetime.utcnow()
        log.exception("bg_ingest_unexpected job_id=%s", job.job_id)
    finally:
        job_store[job.job_id] = job
        # Clean up temp file
        try:
            Path(job.tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


async def retrieve_context(
    pipeline: RAGPipeline,
    query: str,
    k: int = 5,
) -> tuple[str, int]:
    """Async wrapper for synchronous FAISS retrieval.

    Args:
        pipeline: RAGPipeline singleton.
        query:    User question.
        k:        Number of chunks to retrieve.

    Returns:
        Tuple of (context_string, chunk_count).
    """
    context = await asyncio.to_thread(pipeline.retrieve, query, k)
    chunk_count = context.count("[Excerpt")
    return context, chunk_count
