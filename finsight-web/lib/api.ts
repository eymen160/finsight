/**
 * FinSight — Typed API Client
 * Centralises all fetch logic to the FastAPI backend.
 */
import type {
  StockInfo,
  StockHistoryResponse,
  TechnicalSignalsResponse,
  DocumentUploadResponse,
  EmbedJobStatusResponse,
  IndexedDocumentsResponse,
  DocumentQueryResponse,
  ChatMessage,
  APIError,
} from '@/types'

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ── Error class ───────────────────────────────────────────────

export class APIResponseError extends Error {
  constructor(
    public readonly code:        string,
    message:                     string,
    public readonly status:      number,
    public readonly retry_after?: number,
  ) {
    super(message)
    this.name = 'APIResponseError'
  }
}

// ── Generic fetch ─────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!res.ok) {
    let err: APIError
    try { err = await res.json() }
    catch { err = { code: 'UNKNOWN', message: `HTTP ${res.status}` } }
    const retryAfter = res.headers.get('Retry-After')
    throw new APIResponseError(
      err.code, err.message, res.status,
      retryAfter ? parseInt(retryAfter, 10) : err.retry_after,
    )
  }
  return res.json() as Promise<T>
}

// ── Finance ───────────────────────────────────────────────────

export const financeApi = {
  getInfo(ticker: string): Promise<StockInfo> {
    return apiFetch(`/api/v1/finance/info/${encodeURIComponent(ticker)}`)
  },
  getHistory(ticker: string, period = '1y', interval = '1d'): Promise<StockHistoryResponse> {
    const p = new URLSearchParams({ period, interval })
    return apiFetch(`/api/v1/finance/history/${encodeURIComponent(ticker)}?${p}`)
  },
  getSignals(ticker: string, period = '1y'): Promise<TechnicalSignalsResponse> {
    return apiFetch(`/api/v1/finance/signals/${encodeURIComponent(ticker)}?period=${period}`)
  },
}

// ── RAG ───────────────────────────────────────────────────────

export const ragApi = {
  async uploadDocument(file: File): Promise<DocumentUploadResponse> {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/api/v1/rag/upload`, {
      method: 'POST', body: form,
    })
    if (!res.ok) {
      const err: APIError = await res.json().catch(() => ({
        code: 'UPLOAD_FAILED', message: `Upload failed (HTTP ${res.status})`,
      }))
      throw new APIResponseError(err.code, err.message, res.status)
    }
    return res.json()
  },
  getJobStatus(jobId: string): Promise<EmbedJobStatusResponse> {
    return apiFetch(`/api/v1/rag/jobs/${encodeURIComponent(jobId)}`)
  },
  listDocuments(): Promise<IndexedDocumentsResponse> {
    return apiFetch('/api/v1/rag/documents')
  },
  queryDocument(query: string, k = 5): Promise<DocumentQueryResponse> {
    return apiFetch('/api/v1/rag/query', {
      method: 'POST', body: JSON.stringify({ query, k }),
    })
  },
  clearIndex(): Promise<void> {
    return apiFetch('/api/v1/rag/index', { method: 'DELETE' })
  },
}

// ── Chat SSE streaming ────────────────────────────────────────

export async function streamChat(
  messages:      ChatMessage[],
  extraContext?: string,
  signal?:       AbortSignal,
): Promise<ReadableStreamDefaultReader<string>> {
  const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, extra_context: extraContext ?? null }),
    signal,
  })

  if (!res.ok || !res.body) {
    const err: APIError = await res.json().catch(() => ({
      code: 'STREAM_FAILED', message: 'Failed to connect to AI stream.',
    }))
    throw new APIResponseError(err.code, err.message, res.status)
  }

  const reader  = res.body.getReader()
  const decoder = new TextDecoder()
  let   buffer  = ''

  const textStream = new ReadableStream<string>({
    async pull(controller) {
      while (true) {
        const { done, value } = await reader.read()
        if (done) { controller.close(); return }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (payload === '[DONE]') { controller.close(); return }
          try {
            const parsed = JSON.parse(payload) as { text?: string; error?: string }
            if (parsed.error) { controller.error(new Error(parsed.error)); return }
            if (parsed.text)  { controller.enqueue(parsed.text); return }
          } catch { /* skip malformed */ }
        }
      }
    },
    cancel() { reader.cancel() },
  })

  return textStream.getReader()
}
