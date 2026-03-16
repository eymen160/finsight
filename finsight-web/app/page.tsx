/**
 * FinSight — Main Dashboard Page (App Router)
 *
 * Layout:
 *   ┌─────────────────────────────────────────────────┐
 *   │                    TopBar                        │
 *   ├──────────┬─────────────────────────┬────────────┤
 *   │          │                         │            │
 *   │ Sidebar  │    Main (Charts)        │  ChatPanel │
 *   │  (docs)  │                         │   (AI)     │
 *   │          │                         │            │
 *   └──────────┴─────────────────────────┴────────────┘
 *
 * Both sidebar and chat panel are collapsible.
 */
"use client";

import React, { useEffect, useState } from "react";
import { TopBar }     from "@/components/layout/TopBar";
import { Sidebar }    from "@/components/layout/Sidebar";
import { ChatPanel }  from "@/components/chat/ChatPanel";
import { StockChart, SignalStrip } from "@/components/chart/StockChart";
import { MetricsRow } from "@/components/chart/MetricsRow";
import { useStockData } from "@/hooks/useStockData";
import { useTickerState, useUIState } from "@/store/useFinSightStore";
import { financeApi, APIClientError } from "@/lib/api-client";
import type { OHLCVBar } from "@/types/api";

// ── Chart section ─────────────────────────────────────────────

function ChartSection() {
  const { ticker, period, stockInfo, signals, isLoading, error } = useTickerState();
  const [bars, setBars] = useState<OHLCVBar[]>([]);
  const [loadingBars, setLoadingBars] = useState(false);

  useStockData(); // triggers info + signals fetch

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setLoadingBars(true);
    financeApi.getHistory(ticker, period)
      .then((res) => { if (!cancelled) setBars(res.bars); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoadingBars(false); });
    return () => { cancelled = true; };
  }, [ticker, period]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <div className="text-2xl">⚠️</div>
        <p className="text-sm text-bear-text font-medium">{error}</p>
        <p className="text-xs text-ink-muted max-w-xs text-center">
          {error.includes("rate limit") || error.includes("Rate")
            ? "Yahoo Finance is throttling requests. Wait 30–60 seconds and try again."
            : "Check the ticker symbol and try again."}
        </p>
      </div>
    );
  }

  if (isLoading || loadingBars) {
    return (
      <div className="flex flex-col gap-4 p-4 h-full">
        {/* Metrics skeleton */}
        <div className="flex gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton flex-1 h-16 rounded-xl" />
          ))}
        </div>
        {/* Chart skeleton */}
        <div className="skeleton flex-1 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-0 overflow-hidden">
      {/* Ticker header */}
      {stockInfo && (
        <div className="px-4 pt-4 pb-2 flex-shrink-0">
          <div className="flex items-baseline gap-3 mb-3">
            <h1 className="text-xl font-bold text-ink-high tracking-tight">
              {stockInfo.name}
            </h1>
            <code className="text-xs font-mono text-ink-muted bg-surface-muted px-2 py-0.5 rounded">
              {stockInfo.ticker}
            </code>
            <span className="text-xs text-ink-muted bg-surface-muted px-2 py-0.5 rounded border border-surface-border">
              {stockInfo.sector}
            </span>
          </div>
          {signals && <SignalStrip signals={signals} />}
        </div>
      )}

      {/* Metrics strip */}
      {stockInfo && (
        <div className="px-4 py-2 flex-shrink-0">
          <MetricsRow info={stockInfo} />
        </div>
      )}

      {/* Main chart */}
      <div className="flex-1 min-h-0 px-4 pb-4">
        {bars.length > 0 ? (
          <div className="fin-card h-full p-2">
            <div className="flex items-center justify-between px-2 py-1 mb-1">
              <span className="data-label">Price History · {period.toUpperCase()}</span>
              <span className="text-2xs font-mono text-ink-muted">
                {bars.length} bars
              </span>
            </div>
            <div className="h-[calc(100%-28px)]">
              <StockChart bars={bars} signals={signals} />
            </div>
          </div>
        ) : (
          <div className="fin-card h-full flex items-center justify-center">
            <div className="text-center">
              <p className="text-ink-muted text-sm">No chart data available</p>
              <p className="text-ink-muted text-xs mt-1">Try a different ticker or period</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────

export default function DashboardPage() {
  const { isChatPanelOpen } = useUIState();

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-canvas bg-mesh-gradient">
      <TopBar />

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left: Document sidebar */}
        <Sidebar />

        {/* Center: Charts + metrics */}
        <main className="flex-1 min-w-0 overflow-hidden">
          <ChartSection />
        </main>

        {/* Right: AI Chat panel */}
        {isChatPanelOpen && (
          <aside className="
            w-80 flex-shrink-0 border-l border-surface-border
            bg-canvas-900 flex flex-col animate-slide-in-right overflow-hidden
          ">
            <ChatPanel />
          </aside>
        )}
      </div>
    </div>
  );
}
