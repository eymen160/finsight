"""
FinSight — RAG Router
=======================
Endpoints:
  POST /api/v1/rag/upload         → 202 Accepted + job_id
  GET  /api/v1/rag/jobs/{job_id}  → Job status (for polling)
  POST /api/v1/rag/query          → Retrieve context + Claude answer
  GET  /api/v1/rag/documents      → List indexed documents
  DELETE /api/v1/rag/index        → Wipe the FAISS index

PDF Upload Flow
---------------
1. Client POSTs multipart form with the PDF file.
2. Endpoint saves file to /tmp, creates an EmbedJob, returns 202.
3. FastAPI BackgroundTask runs ``run_ingest_job`` (async, thread-pool).
4. Client polls GET /jobs/{job_id} every 2 seconds.
5. When status = "complete", client may call POST /rag/query.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    UploadFile,
    status,
)

from api.dependencies import JobStoreDep, LoggerDep, RAGPipelineDep
from api.schemas.requests import DocumentQueryRequest
from api.schemas.responses import (
    DocumentQueryResponse,
    DocumentUploadResponse,
    EmbedJobStatusResponse,
    IndexedDocumentsResponse,
    JobStatus,
)
from api.services.rag_service import (
    EmbedJob,
    create_job,
    retrieve_context,
    run_ingest_job,
)
from core.exceptions import IndexNotFoundError, LLMError, LLMRateLimitError
from api.dependencies import ClaudeClientDep

router = APIRouter(prefix="/rag", tags=["RAG"])

# Maximum accepted PDF size: 20 MB
_MAX_PDF_BYTES = 20 * 1024 * 1024


# ── Routes ────────────────────────────────────────────────────

@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentUploadResponse,
    summary="Upload a PDF document for RAG indexing (async)",
    responses={
        202: {"description": "Document accepted; embedding running in background."},
        413: {"description": "File too large (> 20 MB)."},
        415: {"description": "Unsupported media type (only PDF accepted)."},
    },
)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    rag: RAGPipelineDep,
    job_store: JobStoreDep,
    log: LoggerDep,
) -> DocumentUploadResponse:
    """
    Accept a PDF upload and start embedding in a background task.

    Returns **202 Accepted** immediately with a ``job_id``.
    The client should poll ``GET /api/v1/rag/jobs/{job_id}`` every 2 s
    until ``status`` is ``"complete"`` or ``"failed"``.
    """
    # ── Validation ────────────────────────────────────────────
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "UNSUPPORTED_TYPE", "message": "Only PDF files are accepted."},
        )

    content = await file.read()
    if len(content) > _MAX_PDF_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"PDF exceeds the 20 MB limit (got {len(content) // 1024} KB).",
            },
        )

    if not content[:4] == b"%PDF":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "INVALID_PDF", "message": "File does not appear to be a valid PDF."},
        )

    # ── Persist to /tmp ───────────────────────────────────────
    suffix = Path(file.filename or "upload.pdf").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    # ── Create job and enqueue background task ─────────────────
    job: EmbedJob = create_job(filename=file.filename or "document.pdf", tmp_path=tmp_path)
    job_store[job.job_id] = job

    background_tasks.add_task(run_ingest_job, job, job_store, rag)

    log.info("upload_accepted job_id=%s file=%s size=%d", job.job_id, job.filename, len(content))

    return DocumentUploadResponse(
        job_id   = job.job_id,
        filename = job.filename,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=EmbedJobStatusResponse,
    summary="Poll background embedding job status",
    responses={
        404: {"description": "Job ID not found."},
    },
)
async def get_job_status(
    job_id: str,
    job_store: JobStoreDep,
    log: LoggerDep,
) -> EmbedJobStatusResponse:
    """
    Poll the status of a background PDF embedding job.

    Status values:
    - ``processing`` — embedding is still running.
    - ``complete``   — indexing finished; ``chunks_indexed`` is populated.
    - ``failed``     — an error occurred; ``error`` field contains the reason.
    """
    job: EmbedJob | None = job_store.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"No job found with id '{job_id}'."},
        )

    log.debug("GET /jobs/%s status=%s", job_id, job.status)

    return EmbedJobStatusResponse(
        job_id         = job.job_id,
        filename       = job.filename,
        status         = JobStatus(job.status),
        chunks_indexed = job.chunks_indexed,
        error          = job.error,
        created_at     = job.created_at,
        completed_at   = job.completed_at,
    )


@router.post(
    "/query",
    response_model=DocumentQueryResponse,
    summary="Query indexed documents and get a grounded AI answer",
    responses={
        404: {"description": "No documents indexed yet."},
        429: {"description": "Claude API rate limit."},
        502: {"description": "Claude API error."},
    },
)
async def query_documents(
    body: DocumentQueryRequest,
    rag: RAGPipelineDep,
    claude: ClaudeClientDep,
    log: LoggerDep,
) -> DocumentQueryResponse:
    """
    Retrieve relevant chunks via FAISS similarity search and ask Claude
    to answer *query* grounded exclusively in the retrieved context.

    For streaming answers, use ``POST /api/v1/chat/stream`` with the
    ``extra_context`` field populated from this endpoint's context.
    """
    log.info("POST /rag/query query=%r k=%d", body.query[:60], body.k)

    try:
        context, chunk_count = await retrieve_context(rag, body.query, body.k)
    except IndexNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INDEX_NOT_FOUND", "message": str(exc)},
        ) from exc

    import asyncio
    messages = [{"role": "user", "content": body.query}]
    try:
        answer = await asyncio.to_thread(claude.complete, messages, context)
    except LLMRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_ERROR", "message": str(exc), "retry_after": exc.retry_after},
        ) from exc
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "LLM_ERROR", "message": "AI service temporarily unavailable."},
        ) from exc

    return DocumentQueryResponse(
        query          = body.query,
        context_chunks = chunk_count,
        answer         = answer,
    )


@router.get(
    "/documents",
    response_model=IndexedDocumentsResponse,
    summary="List all indexed document filenames",
)
async def list_documents(
    rag: RAGPipelineDep,
    log: LoggerDep,
) -> IndexedDocumentsResponse:
    """Return the filenames of all documents currently in the FAISS index."""
    docs = rag.list_documents()
    log.debug("GET /documents n=%d", len(docs))
    return IndexedDocumentsResponse(documents=docs, total=len(docs))


@router.delete(
    "/index",
    status_code=status.HTTP_200_OK,
    summary="Wipe the FAISS index and all indexed documents",
)
async def clear_index(
    rag: RAGPipelineDep,
    log: LoggerDep,
) -> dict:
    """Delete the FAISS index and all persisted chunk data."""
    log.warning("DELETE /index — wiping FAISS index")
    import asyncio
    await asyncio.to_thread(rag.clear)
    return {"status": "ok", "message": "Index cleared"}
