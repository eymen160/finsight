export const runtime = 'edge'
export const dynamic = 'force-dynamic'

import type { NextRequest } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL!

export async function POST(req: NextRequest) {
  const body = await req.json()

  let upstream: Response
  try {
    upstream = await fetch(`${API_BASE}/api/v1/chat/stream`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
      body:    JSON.stringify(body),
    })
  } catch {
    return new Response(
      JSON.stringify({ code: 'BACKEND_UNREACHABLE', message: 'Cannot reach backend.' }),
      { status: 502, headers: { 'Content-Type': 'application/json' } },
    )
  }

  if (!upstream.ok || !upstream.body) {
    return new Response(
      JSON.stringify({ code: 'BACKEND_ERROR', message: `Backend returned ${upstream.status}` }),
      { status: upstream.status, headers: { 'Content-Type': 'application/json' } },
    )
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      'Content-Type':      'text/event-stream',
      'Cache-Control':     'no-cache, no-store, must-revalidate',
      'Connection':        'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  })
}
