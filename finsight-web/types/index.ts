// FinSight — Shared TypeScript Types
// Mirrors FastAPI Pydantic response schemas exactly.

// ── Finance ─────────────────────────────────────────────────
export interface StockInfo {
  ticker:              string
  name:                string
  sector:              string
  industry:            string
  market_cap:          number | null
  pe_ratio:            number | null
  forward_pe:          number | null
  eps:                 number | null
  dividend_yield:      number | null
  fifty_two_week_high: number | null
  fifty_two_week_low:  number | null
  current_price:       number | null
  currency:            string
}

export interface OHLCVBar {
  date:   string
  open:   number
  high:   number
  low:    number
  close:  number
  volume: number
}

export interface StockHistoryResponse {
  ticker:     string
  period:     string
  interval:   string
  bars:       OHLCVBar[]
  total_bars: number
}

export type SignalValue = 'BULLISH' | 'BEARISH' | 'NEUTRAL' | 'MIXED'

export interface TechnicalSignalsResponse {
  ticker:             string
  period:             string
  signals:            Record<string, SignalValue>
  bias:               SignalValue
  latest_close:       number | null
  latest_rsi:         number | null
  latest_macd:        number | null
  latest_macd_signal: number | null
}

// ── Chat ────────────────────────────────────────────────────
export type ChatRole = 'user' | 'assistant'
export interface ChatMessage { role: ChatRole; content: string }

// ── RAG ─────────────────────────────────────────────────────
export type JobStatus = 'processing' | 'complete' | 'failed'

export interface DocumentUploadResponse {
  job_id: string; filename: string; status: string; message: string
}
export interface EmbedJobStatusResponse {
  job_id: string; filename: string; status: JobStatus
  chunks_indexed: number | null; error: string | null
  created_at: string; completed_at: string | null
}
export interface IndexedDocumentsResponse { documents: string[]; total: number }
export interface DocumentQueryResponse { query: string; context_chunks: number; answer: string }

// ── API errors ───────────────────────────────────────────────
export interface APIError { code: string; message: string; retry_after?: number }
