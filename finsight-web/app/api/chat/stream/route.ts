export const dynamic = 'force-dynamic'

import { type NextRequest, NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function POST(req: NextRequest) {
  const body = await req.json()

  try {
    const upstream = await fetch(`${API_BASE}/api/v1/chat/stream`, {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept':       'text/event-stream',
      },
      body: JSON.stringify(body),
    })

    if (!upstream.ok || !upstream.body) {
      return NextResponse.json(
        { code: 'BACKEND_ERROR', message: `Backend returned ${upstream.status}` },
        { status: upstream.status },
      )
    }

    return new Response(upstream.body, {
      status: 200,
      headers: {
        'Content-Type':      'text/event-stream',
        'Cache-Control':     'no-cache, no-store',
        'X-Accel-Buffering': 'no',
      },
    })
  } catch {
    return NextResponse.json(
      { code: 'BACKEND_UNREACHABLE', message: 'Cannot reach backend.' },
      { status: 502 },
    )
  }
}
