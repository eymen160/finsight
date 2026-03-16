/**
 * FinSight — Zustand Global Store
 *
 * Manages:
 *  - selectedTicker + period (finance panel)
 *  - stockInfo + signals    (fetched data, cached per ticker)
 *  - chatHistory            (persisted across panel open/close)
 *  - uploadJobs             (active + completed PDF embed jobs)
 *  - indexedDocuments       (list of docs in FAISS)
 *  - UI state               (panel visibility, loading flags)
 */

import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import type {
  ChatMessage,
  Period,
  StockInfoResponse,
  TechnicalSignalsResponse,
  UploadJob,
} from "@/types/api";

// ── State shape ───────────────────────────────────────────────

interface FinSightState {
  // ── Finance ────────────────────────────────────────────────
  ticker: string;
  period: Period;
  stockInfo:   StockInfoResponse | null;
  signals:     TechnicalSignalsResponse | null;
  isLoadingStock: boolean;
  stockError:  string | null;

  // ── Chat ───────────────────────────────────────────────────
  chatHistory:   ChatMessage[];
  isChatStreaming: boolean;

  // ── RAG / Documents ────────────────────────────────────────
  uploadJobs:        Record<string, UploadJob>;   // keyed by job_id
  indexedDocuments:  string[];
  isLoadingDocs:     boolean;

  // ── UI ─────────────────────────────────────────────────────
  isSidebarOpen:    boolean;
  isChatPanelOpen:  boolean;
}

// ── Action shape ──────────────────────────────────────────────

interface FinSightActions {
  // Finance
  setTicker:    (ticker: string) => void;
  setPeriod:    (period: Period) => void;
  setStockData: (info: StockInfoResponse, signals: TechnicalSignalsResponse) => void;
  setLoadingStock: (loading: boolean) => void;
  setStockError:   (error: string | null) => void;

  // Chat
  addUserMessage:      (content: string) => string;     // returns message id
  addAssistantMessage: (id: string, content: string) => void;
  appendToLastMessage: (id: string, chunk: string) => void;
  finaliseMessage:     (id: string) => void;
  setChatStreaming:     (streaming: boolean) => void;
  clearChatHistory:    () => void;

  // RAG
  upsertUploadJob:    (job: UploadJob) => void;
  removeUploadJob:    (jobId: string) => void;
  setIndexedDocuments: (docs: string[]) => void;
  setLoadingDocs:      (loading: boolean) => void;

  // UI
  toggleSidebar:   () => void;
  toggleChatPanel: () => void;
  setSidebarOpen:  (open: boolean) => void;
  setChatPanelOpen: (open: boolean) => void;
}

// ── ID generator ─────────────────────────────────────────────

let _id = 0;
const genId = () => `msg_${Date.now()}_${_id++}`;

// ── Store ─────────────────────────────────────────────────────

export const useFinSightStore = create<FinSightState & FinSightActions>()(
  devtools(
    persist(
      (set, get) => ({
        // ── Initial state ─────────────────────────────────────
        ticker:          "AAPL",
        period:          "1y",
        stockInfo:       null,
        signals:         null,
        isLoadingStock:  false,
        stockError:      null,

        chatHistory:     [],
        isChatStreaming: false,

        uploadJobs:       {},
        indexedDocuments: [],
        isLoadingDocs:    false,

        isSidebarOpen:   true,
        isChatPanelOpen: true,

        // ── Finance actions ───────────────────────────────────
        setTicker: (ticker) =>
          set({ ticker: ticker.toUpperCase().trim(), stockInfo: null, signals: null, stockError: null }),

        setPeriod: (period) => set({ period }),

        setStockData: (info, signals) =>
          set({ stockInfo: info, signals, isLoadingStock: false, stockError: null }),

        setLoadingStock: (loading) => set({ isLoadingStock: loading }),
        setStockError:   (error)   => set({ stockError: error, isLoadingStock: false }),

        // ── Chat actions ──────────────────────────────────────
        addUserMessage: (content) => {
          const id = genId();
          set((s) => ({
            chatHistory: [
              ...s.chatHistory,
              { id, role: "user", content, timestamp: Date.now() },
            ],
          }));
          return id;
        },

        addAssistantMessage: (id, content) =>
          set((s) => ({
            chatHistory: [
              ...s.chatHistory,
              { id, role: "assistant", content, isStreaming: true, timestamp: Date.now() },
            ],
          })),

        appendToLastMessage: (id, chunk) =>
          set((s) => ({
            chatHistory: s.chatHistory.map((m) =>
              m.id === id ? { ...m, content: m.content + chunk } : m
            ),
          })),

        finaliseMessage: (id) =>
          set((s) => ({
            chatHistory: s.chatHistory.map((m) =>
              m.id === id ? { ...m, isStreaming: false } : m
            ),
          })),

        setChatStreaming: (streaming) => set({ isChatStreaming: streaming }),

        clearChatHistory: () => set({ chatHistory: [] }),

        // ── RAG actions ───────────────────────────────────────
        upsertUploadJob: (job) =>
          set((s) => ({ uploadJobs: { ...s.uploadJobs, [job.jobId]: job } })),

        removeUploadJob: (jobId) =>
          set((s) => {
            const jobs = { ...s.uploadJobs };
            delete jobs[jobId];
            return { uploadJobs: jobs };
          }),

        setIndexedDocuments: (docs) => set({ indexedDocuments: docs }),
        setLoadingDocs:      (loading) => set({ isLoadingDocs: loading }),

        // ── UI actions ────────────────────────────────────────
        toggleSidebar:   () => set((s) => ({ isSidebarOpen: !s.isSidebarOpen })),
        toggleChatPanel: () => set((s) => ({ isChatPanelOpen: !s.isChatPanelOpen })),
        setSidebarOpen:  (open) => set({ isSidebarOpen: open }),
        setChatPanelOpen: (open) => set({ isChatPanelOpen: open }),
      }),
      {
        name: "finsight-store",
        // Only persist user preferences + chat history
        partialize: (s) => ({
          ticker:          s.ticker,
          period:          s.period,
          chatHistory:     s.chatHistory.filter((m) => !m.isStreaming),
          indexedDocuments: s.indexedDocuments,
          isSidebarOpen:   s.isSidebarOpen,
          isChatPanelOpen: s.isChatPanelOpen,
        }),
      }
    ),
    { name: "FinSight" }
  )
);

// ── Selector hooks (prevent unnecessary re-renders) ───────────

export const useTickerState = () =>
  useFinSightStore((s) => ({
    ticker:         s.ticker,
    period:         s.period,
    stockInfo:      s.stockInfo,
    signals:        s.signals,
    isLoading:      s.isLoadingStock,
    error:          s.stockError,
    setTicker:      s.setTicker,
    setPeriod:      s.setPeriod,
    setStockData:   s.setStockData,
    setLoading:     s.setLoadingStock,
    setError:       s.setStockError,
  }));

export const useChatState = () =>
  useFinSightStore((s) => ({
    chatHistory:         s.chatHistory,
    isChatStreaming:     s.isChatStreaming,
    addUserMessage:      s.addUserMessage,
    addAssistantMessage: s.addAssistantMessage,
    appendToLastMessage: s.appendToLastMessage,
    finaliseMessage:     s.finaliseMessage,
    setChatStreaming:     s.setChatStreaming,
    clearChatHistory:    s.clearChatHistory,
  }));

export const useRAGState = () =>
  useFinSightStore((s) => ({
    uploadJobs:       s.uploadJobs,
    indexedDocuments: s.indexedDocuments,
    isLoadingDocs:    s.isLoadingDocs,
    upsertUploadJob:  s.upsertUploadJob,
    removeUploadJob:  s.removeUploadJob,
    setIndexedDocuments: s.setIndexedDocuments,
    setLoadingDocs:   s.setLoadingDocs,
  }));

export const useUIState = () =>
  useFinSightStore((s) => ({
    isSidebarOpen:    s.isSidebarOpen,
    isChatPanelOpen:  s.isChatPanelOpen,
    toggleSidebar:    s.toggleSidebar,
    toggleChatPanel:  s.toggleChatPanel,
    setSidebarOpen:   s.setSidebarOpen,
    setChatPanelOpen: s.setChatPanelOpen,
  }));
