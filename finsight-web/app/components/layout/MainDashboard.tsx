'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  RefreshCw, ChevronDown, TrendingUp, TrendingDown,
  Minus, Activity, AlertCircle, Loader2,
} from 'lucide-react'

import { financeApi }       from '@/lib/api'
import {
  useFinSightStore,
  selectTicker,
  selectSignals,
  selectActions,
  selectUI,
} from '@/store/useFinSightStore'
import { StockChart }       from '../charts/StockChart'
import type { OHLCVBar, SignalValue, StockInfo } from '@/types'

// ── Signal badge ──────────────────────────────────────────────

function SignalBadge({ value }: { value: SignalValue }) {
  const cls = {
    BULLISH: 'badge-bullish',
    BEARISH: 'badge-bearish',
    NEUTRAL: 'badge-neutral',
    MIXED:   'badge-mixed',
  }[value] ?? 'badge-neutral'

  const Icon = {
    BULLISH: TrendingUp,
    BEARISH: TrendingDown,
    NEUTRAL: Minus,
    MIXED:   Activity,
  }[value] ?? Minus

  return (
    <span className={cls}>
      <Icon className="w-3 h-3" />
      {value}
    </span>
  )
}

// ── Metric tile ───────────────────────────────────────────────

function MetricTile({
  label, value, sub,
}: { label: string; value: string; sub?: string }) {
  return (
    <div className="metric-tile">
      <p className="section-label mb-1">{label}</p>
      <p className="text-base font-mono font-semibold text-fs-text">{value}</p>
      {sub && <p className="text-[10px] text-fs-muted mt-0.5">{sub}</p>}
    </div>
  )
}

// ── Ticker search bar ─────────────────────────────────────────

function TickerBar() {
  const ticker  = useFinSightStore(selectTicker)
  const actions = useFinSightStore(selectActions)
  const [draft, setDraft] = useState(ticker.symbol)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const sym = draft.trim().toUpperCase()
    if (sym && sym !== ticker.symbol) {
      actions.setTicker(sym)
    }
  }

  const PERIODS = ['1mo','3mo','6mo','1y','2y','5y'] as const

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          className="input-premium w-32 text-sm uppercase"
          value={draft}
          onChange={e => setDraft(e.target.value.toUpperCase())}
          maxLength={12}
          placeholder="AAPL"
          aria-label="Ticker symbol"
        />
        <button type="submit" className="btn-primary py-2 px-3 text-xs">
          Go
        </button>
      </form>

      <div className="flex gap-1">
        {PERIODS.map(p => (
          <button
            key={p}
            onClick={() => actions.setPeriod(p)}
            className={[
              'px-2.5 py-1 rounded-md text-xs font-mono transition-all duration-150',
              ticker.period === p
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                : 'text-fs-muted hover:text-fs-text hover:bg-white/5',
            ].join(' ')}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Main dashboard ────────────────────────────────────────────

export function MainDashboard() {
  const ticker  = useFinSightStore(selectTicker)
  const signals = useFinSightStore(selectSignals)
  const actions = useFinSightStore(selectActions)
  const { activeView } = useFinSightStore(selectUI)

  const [bars,  setBars]  = useState<OHLCVBar[]>([])
  const [info,  setInfo]  = useState<StockInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // ── Fetch all data ─────────────────────────────────────────

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    actions.setTickerLoading(true)

    try {
      const [infoData, histData, signalsData] = await Promise.all([
        financeApi.getInfo(ticker.symbol),
        financeApi.getHistory(ticker.symbol, ticker.period),
        financeApi.getSignals(ticker.symbol, ticker.period),
      ])

      setInfo(infoData)
      setBars(histData.bars)
      actions.setTickerName(infoData.name)
      actions.setSignals(signalsData.signals as Record<string, SignalValue>, signalsData.bias)
      actions.setLatestMetrics(signalsData.latest_close, signalsData.latest_rsi)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch data'
      setError(msg)
      actions.setTickerError(msg)
    } finally {
      setLoading(false)
      actions.setTickerLoading(false)
    }
  }, [ticker.symbol, ticker.period, actions])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // ── Helpers ────────────────────────────────────────────────

  const formatLarge = (v: number | null) => {
    if (v === null) return '—'
    if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`
    if (v >= 1e9)  return `$${(v / 1e9).toFixed(2)}B`
    if (v >= 1e6)  return `$${(v / 1e6).toFixed(2)}M`
    return `$${v.toFixed(2)}`
  }

  const fmt = (v: number | null, prefix = '$', decimals = 2) =>
    v !== null ? `${prefix}${v.toFixed(decimals)}` : '—'

  // ── Render ─────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* ── Top toolbar ── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-fs-border flex-shrink-0 gap-4 flex-wrap">
        <TickerBar />
        <div className="flex items-center gap-2">
          {loading && <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />}
          {signals.bias && <SignalBadge value={signals.bias} />}
          <button
            onClick={fetchData}
            disabled={loading}
            className="btn-ghost p-2"
            aria-label="Refresh data"
            title="Refresh"
          >
            <RefreshCw className={['w-3.5 h-3.5', loading ? 'animate-spin' : ''].join(' ')} />
          </button>
        </div>
      </div>

      {/* ── Error state ── */}
      {error && (
        <div className="mx-5 mt-4 flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-xl p-4 animate-fade-in">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-400">Data fetch failed</p>
            <p className="text-xs text-fs-muted mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* ── Scrollable content ── */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 no-scrollbar">

        {/* Company header */}
        {info && (
          <div className="flex items-baseline gap-3 flex-wrap animate-fade-in">
            <h1 className="text-xl font-bold text-fs-text tracking-tight">
              {info.name}
            </h1>
            <span className="font-mono text-sm text-fs-muted bg-fs-subtle px-2 py-0.5 rounded">
              {ticker.symbol}
            </span>
            {info.sector !== 'N/A' && (
              <span className="text-xs text-fs-muted border border-fs-border px-2.5 py-0.5 rounded-full">
                {info.sector}
              </span>
            )}
            {info.current_price !== null && (
              <span className="ml-auto font-mono text-2xl font-semibold text-fs-text">
                ${info.current_price.toFixed(2)}
                <span className="text-xs text-fs-muted ml-1">{info.currency}</span>
              </span>
            )}
          </div>
        )}

        {/* Key metrics strip */}
        {info && (
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 animate-fade-in">
            <MetricTile label="52W High"   value={fmt(info.fifty_two_week_high)} />
            <MetricTile label="52W Low"    value={fmt(info.fifty_two_week_low)} />
            <MetricTile label="P/E (TTM)"  value={info.pe_ratio  ? `${info.pe_ratio.toFixed(1)}x` : '—'} />
            <MetricTile label="Fwd P/E"    value={info.forward_pe? `${info.forward_pe.toFixed(1)}x`: '—'} />
            <MetricTile label="Market Cap" value={formatLarge(info.market_cap)} />
            <MetricTile
              label="RSI (14)"
              value={signals.latestRsi ? signals.latestRsi.toFixed(1) : '—'}
              sub={signals.latestRsi
                ? signals.latestRsi < 30 ? 'Oversold'
                : signals.latestRsi > 70 ? 'Overbought' : 'Neutral'
                : undefined}
            />
          </div>
        )}

        {/* Technical signals row */}
        {Object.keys(signals.signals).length > 0 && (
          <div className="flex flex-wrap gap-2 animate-fade-in">
            {Object.entries(signals.signals).map(([name, value]) => (
              <div key={name} className="flex items-center gap-2 bg-fs-surface border border-fs-border rounded-lg px-3 py-1.5">
                <span className="section-label">{name}</span>
                <SignalBadge value={value as SignalValue} />
              </div>
            ))}
          </div>
        )}

        {/* Chart */}
        {bars.length > 0 && !loading && (
          <div className="animate-fade-in">
            <StockChart bars={bars} ticker={ticker.symbol} />
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-2 animate-pulse">
            {[320, 110, 110].map((h, i) => (
              <div
                key={i}
                className="rounded-xl bg-fs-surface border border-fs-border"
                style={{ height: h }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
