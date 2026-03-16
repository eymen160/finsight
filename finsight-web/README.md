# FinSight Web — Next.js Frontend

Premium FinTech dashboard for the FinSight AI financial analysis platform.

## Stack

- **Next.js 14** (App Router)
- **TypeScript** (strict)
- **Tailwind CSS** + custom FinTech design system
- **Zustand** — global state (ticker, chat, RAG, UI)
- **Recharts** — candlestick + SMA + RSI + MACD charts
- **react-dropzone** — PDF drag-and-drop upload

## Quick Start

```bash
cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL to your FastAPI backend
npm install
npm run dev   # → http://localhost:3000
```

## Project Structure

```
app/
  page.tsx                     ← 3-panel layout (sidebar|chart|chat)
  layout.tsx                   ← Root layout + fonts
  globals.css                  ← Design system (tokens, components, utilities)
  components/
    layout/
      Sidebar.tsx              ← Collapsible left sidebar (doc management)
      MainDashboard.tsx        ← Central chart + signals + metrics
    charts/
      StockChart.tsx           ← Recharts: candles, SMA, RSI, MACD
    chat/
      ChatPanel.tsx            ← SSE streaming AI chat
    rag/
      DocumentUpload.tsx       ← Drag-drop PDF + polling progress bar
      DocumentList.tsx         ← Indexed documents list
    ui/
      Badge.tsx                ← Signal badges (BULLISH/BEARISH/etc.)
      Spinner.tsx              ← Loading spinner

store/
  useFinSightStore.ts          ← Zustand: all global state + actions

lib/
  api.ts                       ← Typed API client + SSE stream reader
  utils.ts                     ← cn(), formatters

types/
  index.ts                     ← All TypeScript types (mirrors FastAPI schemas)
```

## Environment Variables

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | FastAPI backend URL (no trailing slash) |

## Design System

The `globals.css` defines a full Bloomberg Terminal × Stripe design system:
- `glass-card` — frosted glass card surface
- `badge-bullish/bearish/neutral/mixed` — signal indicator badges
- `metric-tile` — KPI card with gradient accent bar
- `input-premium` — styled input with focus ring
- `btn-primary/ghost/outline` — button variants
- `section-label` — ALL CAPS section headers
- `streaming-cursor` — animated typing cursor for AI responses
