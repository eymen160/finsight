/**
 * FinSight — Zustand Global Store
 */
import { create } from 'zustand'
import { persist, devtools } from 'zustand/middleware'
import type { ChatMessage, SignalValue, OHLCVBar, StockInfo, JobStatus } from '@/types'

// ── Types ─────────────────────────────────────────────────────

interface UploadJob {
  jobId:         string
  filename:      string
  status:        JobStatus
  chunksIndexed: number | null
  error:         string | null
  progress:      number
}

interface TickerSlice {
  symbol:    string
  name:      string
  period:    string
  isLoading: boolean
  error:     string | null
}

interface ChatSlice {
  messages:    ChatMessage[]
  isStreaming: boolean
  streamError: string | null
}

interface RAGSlice {
  documents:   string[]
  activeJob:   UploadJob | null
  isUploading: boolean
}

interface SignalSlice {
  signals:     Record<string, SignalValue>
  bias:        SignalValue | null
  latestClose: number | null
  latestRsi:   number | null
}

interface UISlice {
  sidebarOpen:   boolean
  chatPanelOpen: boolean
  activeView:    'chart' | 'fundamentals'
}

interface Actions {
  setTicker:         (symbol: string) => void
  setTickerName:     (name: string) => void
  setPeriod:         (period: string) => void
  setTickerLoading:  (v: boolean) => void
  setTickerError:    (e: string | null) => void
  setSignals:        (signals: Record<string, SignalValue>, bias: SignalValue) => void
  setLatestMetrics:  (close: number | null, rsi: number | null) => void
  addUserMessage:    (content: string) => void
  addAssistantMessage: (content: string) => void
  appendAssistantDelta: (delta: string) => void
  setStreaming:      (v: boolean) => void
  setStreamError:    (e: string | null) => void
  clearChat:         () => void
  startUploadJob:    (jobId: string, filename: string) => void
  updateUploadJob:   (update: Partial<UploadJob>) => void
  completeUploadJob: (chunks: number) => void
  failUploadJob:     (error: string) => void
  clearUploadJob:    () => void
  setDocuments:      (docs: string[]) => void
  toggleSidebar:     () => void
  toggleChatPanel:   () => void
  setActiveView:     (v: UISlice['activeView']) => void
}

interface Store extends UISlice {
  ticker:  TickerSlice
  chat:    ChatSlice
  rag:     RAGSlice
  signals: SignalSlice
  actions: Actions
}

// ── Store ─────────────────────────────────────────────────────

export const useFinSightStore = create<Store>()(
  devtools(
    persist(
      (set, get) => ({
        sidebarOpen:   true,
        chatPanelOpen: true,
        activeView:    'chart',
        ticker:  { symbol: 'AAPL', name: 'Apple Inc.', period: '1y', isLoading: false, error: null },
        chat:    { messages: [], isStreaming: false, streamError: null },
        rag:     { documents: [], activeJob: null, isUploading: false },
        signals: { signals: {}, bias: null, latestClose: null, latestRsi: null },

        actions: {
          setTicker:        (symbol) => set(s => ({ ticker: { ...s.ticker, symbol: symbol.toUpperCase(), error: null } })),
          setTickerName:    (name)   => set(s => ({ ticker: { ...s.ticker, name } })),
          setPeriod:        (period) => set(s => ({ ticker: { ...s.ticker, period } })),
          setTickerLoading: (v)      => set(s => ({ ticker: { ...s.ticker, isLoading: v } })),
          setTickerError:   (e)      => set(s => ({ ticker: { ...s.ticker, error: e, isLoading: false } })),

          setSignals:       (signals, bias) => set(s => ({ signals: { ...s.signals, signals, bias } })),
          setLatestMetrics: (c, r)          => set(s => ({ signals: { ...s.signals, latestClose: c, latestRsi: r } })),

          addUserMessage:    (content) => set(s => ({ chat: { ...s.chat, messages: [...s.chat.messages, { role: 'user', content }] } })),
          addAssistantMessage: (content) => set(s => ({ chat: { ...s.chat, messages: [...s.chat.messages, { role: 'assistant', content }] } })),
          appendAssistantDelta: (delta) => set(s => {
            const msgs = [...s.chat.messages]
            const last = msgs[msgs.length - 1]
            if (last?.role === 'assistant') msgs[msgs.length - 1] = { ...last, content: last.content + delta }
            return { chat: { ...s.chat, messages: msgs } }
          }),
          setStreaming:   (v) => set(s => ({ chat: { ...s.chat, isStreaming: v } })),
          setStreamError: (e) => set(s => ({ chat: { ...s.chat, streamError: e, isStreaming: false } })),
          clearChat:      ()  => set({ chat: { messages: [], isStreaming: false, streamError: null } }),

          startUploadJob:    (jobId, filename) => set(s => ({ rag: { ...s.rag, isUploading: true, activeJob: { jobId, filename, status: 'processing', chunksIndexed: null, error: null, progress: 5 } } })),
          updateUploadJob:   (u) => set(s => ({ rag: { ...s.rag, activeJob: s.rag.activeJob ? { ...s.rag.activeJob, ...u } : null } })),
          completeUploadJob: (chunks) => set(s => ({ rag: { ...s.rag, isUploading: false, activeJob: s.rag.activeJob ? { ...s.rag.activeJob, status: 'complete', chunksIndexed: chunks, progress: 100 } : null } })),
          failUploadJob:     (error) => set(s => ({ rag: { ...s.rag, isUploading: false, activeJob: s.rag.activeJob ? { ...s.rag.activeJob, status: 'failed', error, progress: 0 } : null } })),
          clearUploadJob:    ()  => set(s => ({ rag: { ...s.rag, activeJob: null, isUploading: false } })),
          setDocuments:      (docs) => set(s => ({ rag: { ...s.rag, documents: docs } })),

          toggleSidebar:   () => set(s => ({ sidebarOpen: !s.sidebarOpen })),
          toggleChatPanel: () => set(s => ({ chatPanelOpen: !s.chatPanelOpen })),
          setActiveView:   (v) => set({ activeView: v }),
        },
      }),
      {
        name: 'finsight-store',
        partialize: (s) => ({
          sidebarOpen: s.sidebarOpen,
          chatPanelOpen: s.chatPanelOpen,
          ticker: { symbol: s.ticker.symbol, period: s.ticker.period, name: s.ticker.name },
          chat: { messages: s.chat.messages.slice(-30) },
          rag: { documents: s.rag.documents },
        }),
      },
    ),
    { name: 'FinSight' },
  ),
)

// ── Selectors ─────────────────────────────────────────────────
export const selectTicker  = (s: Store) => s.ticker
export const selectChat    = (s: Store) => s.chat
export const selectRAG     = (s: Store) => s.rag
export const selectSignals = (s: Store) => s.signals
export const selectUI      = (s: Store) => ({ sidebarOpen: s.sidebarOpen, chatPanelOpen: s.chatPanelOpen, activeView: s.activeView })
export const selectActions = (s: Store) => s.actions

// Legacy hooks for compatibility
export const useTickerState = () => useFinSightStore(selectTicker)
export const useChatState   = () => useFinSightStore(selectChat)
export const useRAGState    = () => useFinSightStore(selectRAG)
export const useUIState     = () => useFinSightStore(selectUI)
