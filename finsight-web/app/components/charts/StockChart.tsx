'use client'

/**
 * StockChart
 * ===========
 * Premium Recharts-based financial chart with:
 *  - Candlestick bars (custom shape)
 *  - Volume bars
 *  - SMA 20/50/200 overlays
 *  - RSI sub-chart
 *  - MACD sub-chart
 *  - Custom dark tooltips
 */

import { useMemo } from 'react'
import {
  ComposedChart, Bar, Line,
  XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
  Cell,
} from 'recharts'
import type { OHLCVBar } from '@/types'

// ── Candlestick custom bar ────────────────────────────────────

interface CandleProps {
  x?:      number
  y?:      number
  width?:  number
  height?: number
  open:    number
  close:   number
  high:    number
  low:     number
  index?:  number
}

function CandleBar(props: CandleProps) {
  const { x = 0, y = 0, width = 0, height = 0, open, close, high, low } = props
  const isUp    = close >= open
  const fill    = isUp ? '#22c55e' : '#ef4444'
  const stroke  = fill
  const centerX = x + width / 2

  // We use Bar's y/height for the body (recharts provides them)
  // We calculate wick positions manually
  const bodyTop    = Math.min(y, y + height)
  const bodyBottom = Math.max(y, y + height)

  return (
    <g>
      {/* Wick (high/low line) */}
      <line
        x1={centerX} y1={0}
        x2={centerX} y2={bodyTop}
        stroke={stroke}
        strokeWidth={1}
        opacity={0.7}
      />
      <line
        x1={centerX} y1={bodyBottom}
        x2={centerX} y2={1000}
        stroke={stroke}
        strokeWidth={1}
        opacity={0.7}
      />
      {/* Body */}
      <rect
        x={x + 1}
        y={bodyTop}
        width={Math.max(width - 2, 1)}
        height={Math.max(Math.abs(height), 1)}
        fill={fill}
        stroke={stroke}
        strokeWidth={0.5}
        opacity={0.85}
        rx={0.5}
      />
    </g>
  )
}

// ── Custom Tooltip ────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: {
  active?:  boolean
  payload?: Array<{ name: string; value: number; color: string; dataKey: string }>
  label?:   string
}) {
  if (!active || !payload?.length) return null

  const bar = payload.find(p => p.dataKey === 'close')
  const vol = payload.find(p => p.dataKey === 'volume')

  return (
    <div className="glass-card px-3 py-2.5 text-xs min-w-[160px]">
      <p className="font-mono text-fs-muted mb-2">{label}</p>
      {payload.map(p => {
        const isPrice  = ['open','high','low','close'].includes(p.dataKey)
        const isVolume = p.dataKey === 'volume'
        return (
          <div key={p.dataKey} className="flex justify-between gap-4 mb-0.5">
            <span className="text-fs-muted capitalize">{p.dataKey}</span>
            <span className="font-mono" style={{ color: p.color }}>
              {isPrice  ? `$${Number(p.value).toFixed(2)}`         :
               isVolume ? (Number(p.value) / 1e6).toFixed(1) + 'M' :
                          Number(p.value).toFixed(3)}
            </span>
          </div>
        )
      })}
    </div>
  )
}

// ── Chart data builder (adds SMA, RSI, MACD from raw bars) ───

function ema(values: number[], period: number): number[] {
  const k   = 2 / (period + 1)
  const out: number[] = []
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) { out.push(NaN); continue }
    if (i === period - 1) {
      out.push(values.slice(0, period).reduce((a, b) => a + b, 0) / period)
      continue
    }
    out.push(values[i]! * k + out[i - 1]! * (1 - k))
  }
  return out
}

function sma(values: number[], period: number): number[] {
  return values.map((_, i) =>
    i < period - 1
      ? NaN
      : values.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period,
  )
}

function computeRsi(closes: number[], period = 14): number[] {
  const gains: number[] = [0]
  const losses: number[] = [0]
  for (let i = 1; i < closes.length; i++) {
    const diff = closes[i]! - closes[i - 1]!
    gains.push(diff > 0 ? diff : 0)
    losses.push(diff < 0 ? -diff : 0)
  }
  return gains.map((_, i) => {
    if (i < period) return NaN
    const avgGain = gains.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period
    const avgLoss = losses.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period
    return avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
  })
}

interface ChartRow extends OHLCVBar {
  sma20?: number
  sma50?: number
  sma200?: number
  rsi?:   number
  macd?:  number
  signal?:number
  hist?:  number
}

function buildChartData(bars: OHLCVBar[]): ChartRow[] {
  const closes  = bars.map(b => b.close)
  const sma20v  = sma(closes, 20)
  const sma50v  = sma(closes, 50)
  const sma200v = sma(closes, 200)
  const rsiV    = computeRsi(closes)
  const ema12v  = ema(closes, 12)
  const ema26v  = ema(closes, 26)
  const macdLine = ema12v.map((v, i) => v - ema26v[i]!)
  const signalLine = ema(macdLine.map(v => isNaN(v) ? 0 : v), 9)

  return bars.map((b, i) => ({
    ...b,
    sma20:  isNaN(sma20v[i]!)  ? undefined : +sma20v[i]!.toFixed(2),
    sma50:  isNaN(sma50v[i]!)  ? undefined : +sma50v[i]!.toFixed(2),
    sma200: isNaN(sma200v[i]!) ? undefined : +sma200v[i]!.toFixed(2),
    rsi:    isNaN(rsiV[i]!)    ? undefined : +rsiV[i]!.toFixed(2),
    macd:   isNaN(macdLine[i]!)? undefined : +macdLine[i]!.toFixed(4),
    signal: isNaN(signalLine[i]!)? undefined: +signalLine[i]!.toFixed(4),
    hist:   (macdLine[i]! - signalLine[i]!),
  }))
}

// ── Main component ────────────────────────────────────────────

interface StockChartProps {
  bars:   OHLCVBar[]
  ticker: string
}

export function StockChart({ bars, ticker }: StockChartProps) {
  const data = useMemo(() => buildChartData(bars), [bars])

  // Only show last 252 bars (≈ 1yr daily)
  const visible = data.slice(-252)

  const xTickFormatter = (date: string) =>
    new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

  const priceFormatter = (v: number) => `$${v.toFixed(0)}`

  return (
    <div className="space-y-2">
      {/* ── Price + Volume + SMA ── */}
      <div className="chart-container h-[320px]">
        <p className="section-label mb-2">{ticker} · OHLCV + Moving Averages</p>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={visible} margin={{ left: 0, right: 48, top: 4, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis
              dataKey="date"
              tickFormatter={xTickFormatter}
              tick={{ fill: '#475569', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              minTickGap={40}
            />
            <YAxis
              orientation="right"
              tickFormatter={priceFormatter}
              tick={{ fill: '#475569', fontSize: 10, fontFamily: 'JetBrains Mono' }}
              axisLine={false}
              tickLine={false}
              width={48}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Volume bars (behind price) */}
            <Bar dataKey="volume" name="volume" yAxisId={0} opacity={0} />

            {/* Candle body via Bar with custom shape */}
            <Bar
              dataKey="close"
              name="close"
              shape={(props: unknown) => {
                const p = props as CandleProps & { payload: OHLCVBar }
                return (
                  <CandleBar
                    {...p}
                    open={p.payload.open}
                    close={p.payload.close}
                    high={p.payload.high}
                    low={p.payload.low}
                  />
                )
              }}
            >
              {visible.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.close >= entry.open ? '#22c55e' : '#ef4444'}
                />
              ))}
            </Bar>

            {/* SMAs */}
            <Line dataKey="sma20"  dot={false} stroke="#f59e0b" strokeWidth={1.2} name="SMA 20" />
            <Line dataKey="sma50"  dot={false} stroke="#3b82f6" strokeWidth={1.2} name="SMA 50" />
            <Line dataKey="sma200" dot={false} stroke="#ef4444" strokeWidth={1.2} name="SMA 200" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ── RSI ── */}
      <div className="chart-container h-[110px]">
        <p className="section-label mb-1">RSI (14)</p>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={visible} margin={{ left: 0, right: 48, top: 2, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="date" hide />
            <YAxis
              orientation="right"
              domain={[0, 100]}
              tick={{ fill: '#475569', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              ticks={[30, 50, 70]}
              width={48}
            />
            <ReferenceLine y={70} stroke="rgba(239,68,68,0.4)"  strokeDasharray="4 2" />
            <ReferenceLine y={30} stroke="rgba(34,197,94,0.4)"  strokeDasharray="4 2" />
            <Tooltip content={<CustomTooltip />} />
            <Line dataKey="rsi" dot={false} stroke="#8b5cf6" strokeWidth={1.5} name="rsi" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ── MACD ── */}
      <div className="chart-container h-[110px]">
        <p className="section-label mb-1">MACD (12, 26, 9)</p>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={visible} margin={{ left: 0, right: 48, top: 2, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="date" hide />
            <YAxis
              orientation="right"
              tick={{ fill: '#475569', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={48}
            />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="hist" name="hist">
              {visible.map((entry, i) => (
                <Cell
                  key={i}
                  fill={(entry.hist ?? 0) >= 0
                    ? 'rgba(34,197,94,0.6)'
                    : 'rgba(239,68,68,0.6)'}
                />
              ))}
            </Bar>
            <Line dataKey="macd"   dot={false} stroke="#3b82f6" strokeWidth={1.3} name="macd" />
            <Line dataKey="signal" dot={false} stroke="#f59e0b" strokeWidth={1.3} name="signal" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
