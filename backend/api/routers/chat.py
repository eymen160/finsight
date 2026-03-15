"""
FinSight — Chat Router
========================
Endpoints:
  POST /api/v1/chat/complete  → Non-streaming single response
  POST /api/v1/chat/stream    → Server-Sent Events streaming response

The streaming endpoint is the recommended one for the Next.js frontend.
The client reads the SSE stream and appends text chunks to the UI.

SSE format::

    data: Hello, \n\n
    data: here is \n\n
    data: the analysis.\n\n
    data: [DONE]\n\n

``[DONE]`` signals end-of-stream so the frontend can finalise state.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from api.dependencies import ClaudeClientDep, LoggerDep, RAGPipelineDep
from api.schemas.requests import ChatRequest
from api.schemas.responses import ChatResponse
from api.services.rag_service import retrieve_context
from core.exceptions import (
    ContextWindowExceededError,
    IndexNotFoundError,
    LLMError,
    LLMRateLimitError,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── SSE helper ────────────────────────────────────────────────

async def _sse_generator(
    claude: object,
    messages: list[dict[str, str]],
    extra_context: str | None,
) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted chunks from the Claude streaming generator.

    Args:
        claude:        ClaudeClient singleton.
        messages:      OpenAI-format message list.
        extra_context: Optional RAG context string.

    Yields:
        SSE data lines, each terminated by ``\\n\\n``.
    """
    try:
        # claude.stream is a synchronous generator; run each next() in thread pool
        loop = asyncio.get_event_loop()
        gen  = claude.stream(messages, extra_context=extra_context)

        while True:
            try:
                chunk: str = await loop.run_in_executor(None, next, gen)
                # Escape newlines inside the chunk value for valid SSE
                payload = json.dumps({"text": chunk})
                yield f"data: {payload}\n\n"
            except StopIteration:
                break

        yield "data: [DONE]\n\n"

    except LLMRateLimitError as exc:
        err = json.dumps({"error": "RATE_LIMIT_ERROR", "message": str(exc), "retry_after": exc.retry_after})
        yield f"data: {err}\n\n"
        yield "data: [DONE]\n\n"

    except ContextWindowExceededError as exc:
        err = json.dumps({"error": "CONTEXT_WINDOW_EXCEEDED", "message": str(exc)})
        yield f"data: {err}\n\n"
        yield "data: [DONE]\n\n"

    except LLMError as exc:
        err = json.dumps({"error": "LLM_ERROR", "message": "AI service temporarily unavailable."})
        yield f"data: {err}\n\n"
        yield "data: [DONE]\n\n"


# ── Routes ────────────────────────────────────────────────────

@router.post(
    "/stream",
    summary="Streaming chat completion (SSE)",
    response_description="Server-Sent Events stream of text deltas",
    responses={
        200: {"content": {"text/event-stream": {}}, "description": "SSE stream"},
        422: {"description": "Invalid request payload"},
    },
)
async def stream_chat(
    body: ChatRequest,
    claude: ClaudeClientDep,
    rag: RAGPipelineDep,
    log: LoggerDep,
) -> StreamingResponse:
    """
    Stream a Claude response token-by-token via Server-Sent Events.

    If ``extra_context`` is provided in the request body, it is injected
    into the prompt as RAG context.  The frontend should include the
    context string retrieved from ``POST /api/v1/rag/query``.

    **Next.js usage:**
    ```ts
    const res = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, extra_context }),
    });
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const lines = decoder.decode(value).split('\\n\\n');
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6);
        if (payload === '[DONE]') return;
        const { text } = JSON.parse(payload);
        setResponse(prev => prev + text);
      }
    }
    ```
    """
    log.info("POST /chat/stream n_messages=%d", len(body.messages))

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    return StreamingResponse(
        _sse_generator(claude, messages, body.extra_context),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",    # disable nginx response buffering
        },
    )


@router.post(
    "/complete",
    response_model=ChatResponse,
    summary="Non-streaming chat completion",
    responses={
        429: {"description": "Claude API rate limit"},
        502: {"description": "Claude API error"},
        422: {"description": "Context window exceeded"},
    },
)
async def complete_chat(
    body: ChatRequest,
    claude: ClaudeClientDep,
    log: LoggerDep,
) -> ChatResponse:
    """
    Return a complete Claude response in a single JSON payload.

    Use this for background tasks or when SSE is not available.
    For interactive UIs, prefer ``/chat/stream``.
    """
    log.info("POST /chat/complete n_messages=%d", len(body.messages))

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    try:
        text = await asyncio.to_thread(
            claude.complete, messages, body.extra_context
        )
    except LLMRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_ERROR", "message": str(exc), "retry_after": exc.retry_after},
        ) from exc
    except ContextWindowExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONTEXT_WINDOW_EXCEEDED", "message": str(exc)},
        ) from exc
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "LLM_ERROR", "message": "AI service temporarily unavailable."},
        ) from exc

    return ChatResponse(content=text)
