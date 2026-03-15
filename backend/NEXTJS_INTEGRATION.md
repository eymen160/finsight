# FinSight — Next.js Frontend Integration Guide

## Base URL

```ts
// lib/api.ts
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
```

---

## 1. Stock Info & Signals

```ts
// app/api/finance/route.ts  (Next.js Route Handler — proxies to FastAPI)
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const ticker = searchParams.get('ticker') ?? 'AAPL';
  const period = searchParams.get('period') ?? '1y';

  const [info, signals] = await Promise.all([
    fetch(`${API_BASE}/api/v1/finance/info/${ticker}`).then(r => r.json()),
    fetch(`${API_BASE}/api/v1/finance/signals/${ticker}?period=${period}`).then(r => r.json()),
  ]);
  return Response.json({ info, signals });
}
```

---

## 2. Streaming Chat (SSE)

```tsx
// components/ChatPanel.tsx
'use client';
import { useState } from 'react';

export function ChatPanel() {
  const [response, setResponse] = useState('');
  const [loading, setLoading]   = useState(false);

  async function sendMessage(userMessage: string) {
    setLoading(true);
    setResponse('');

    const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: userMessage }],
      }),
    });

    if (!res.body) return;

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const lines = decoder.decode(value).split('\n\n');
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6).trim();
        if (payload === '[DONE]') { setLoading(false); return; }

        try {
          const parsed = JSON.parse(payload);
          if (parsed.text)  setResponse(prev => prev + parsed.text);
          if (parsed.error) console.error('Stream error:', parsed.error);
        } catch { /* ignore malformed chunks */ }
      }
    }
    setLoading(false);
  }

  return (
    <div>
      <button onClick={() => sendMessage('Explain P/E ratio')}>Ask</button>
      <pre style={{ whiteSpace: 'pre-wrap' }}>{response}</pre>
    </div>
  );
}
```

---

## 3. PDF Upload + Background Job Polling

```tsx
// components/DocumentUpload.tsx
'use client';
import { useState, useCallback } from 'react';

type JobStatus = 'idle' | 'uploading' | 'processing' | 'complete' | 'failed';

export function DocumentUpload() {
  const [status, setStatus]   = useState<JobStatus>('idle');
  const [jobId,  setJobId]    = useState<string | null>(null);
  const [chunks, setChunks]   = useState<number | null>(null);
  const [error,  setError]    = useState<string | null>(null);

  const pollJob = useCallback((id: string) => {
    const interval = setInterval(async () => {
      const res  = await fetch(`${API_BASE}/api/v1/rag/jobs/${id}`);
      const data = await res.json();

      if (data.status === 'complete') {
        clearInterval(interval);
        setStatus('complete');
        setChunks(data.chunks_indexed);
      } else if (data.status === 'failed') {
        clearInterval(interval);
        setStatus('failed');
        setError(data.error ?? 'Unknown error');
      }
      // Otherwise still "processing" — keep polling
    }, 2000); // poll every 2 seconds
  }, []);

  async function handleUpload(file: File) {
    setStatus('uploading');
    setError(null);

    const form = new FormData();
    form.append('file', file);

    const res = await fetch(`${API_BASE}/api/v1/rag/upload`, {
      method: 'POST',
      body:   form,
    });

    if (!res.ok) {
      const err = await res.json();
      setStatus('failed');
      setError(err.message ?? 'Upload failed');
      return;
    }

    const { job_id } = await res.json();  // 202 Accepted
    setJobId(job_id);
    setStatus('processing');
    pollJob(job_id);
  }

  return (
    <div>
      <input
        type="file"
        accept=".pdf"
        onChange={e => e.target.files?.[0] && handleUpload(e.target.files[0])}
      />
      {status === 'uploading'   && <p>Uploading…</p>}
      {status === 'processing'  && <p>⏳ Embedding document… (job: {jobId})</p>}
      {status === 'complete'    && <p>✅ Indexed {chunks} chunks. Ready to query!</p>}
      {status === 'failed'      && <p>❌ Error: {error}</p>}
    </div>
  );
}
```

---

## 4. Document Q&A (RAG Query)

```ts
// After upload is complete, query the document
async function queryDocument(question: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/rag/query`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: question, k: 5 }),
  });

  if (res.status === 404) throw new Error('No documents indexed yet.');
  if (!res.ok)            throw new Error('Query failed');

  const { answer } = await res.json();
  return answer;
}
```

---

## 5. Error Handling Pattern

Every error response has this shape:
```ts
interface APIError {
  code:        string;   // e.g. "RATE_LIMIT_ERROR", "TICKER_NOT_FOUND"
  message:     string;   // safe to show to users
  retry_after?: number;  // seconds — set on 429 responses
}
```

```ts
async function safeFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const error: APIError = await res.json();
    if (res.status === 429 && error.retry_after) {
      // Respect Retry-After header
      await new Promise(r => setTimeout(r, error.retry_after! * 1000));
      return safeFetch<T>(url, options); // retry once
    }
    throw new Error(error.message);
  }
  return res.json() as T;
}
```

---

## 6. Environment Variables (Vercel)

```
# Vercel Dashboard → Project → Settings → Environment Variables
NEXT_PUBLIC_API_URL=https://your-fastapi.onrender.com
```

---

## 7. Full API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness check |
| `GET`  | `/api/v1/finance/info/{ticker}` | Fundamentals |
| `GET`  | `/api/v1/finance/history/{ticker}` | OHLCV bars |
| `GET`  | `/api/v1/finance/signals/{ticker}` | Technical signals + bias |
| `POST` | `/api/v1/chat/stream` | SSE streaming chat |
| `POST` | `/api/v1/chat/complete` | Non-streaming chat |
| `POST` | `/api/v1/rag/upload` | PDF upload → 202 + job_id |
| `GET`  | `/api/v1/rag/jobs/{job_id}` | Poll embed job status |
| `POST` | `/api/v1/rag/query` | RAG query + Claude answer |
| `GET`  | `/api/v1/rag/documents` | List indexed documents |
| `DELETE` | `/api/v1/rag/index` | Wipe FAISS index |

Interactive docs (dev only): `http://localhost:8000/docs`
