'use client'

import { useState }        from 'react'
import { MessageSquare, X } from 'lucide-react'
import { Sidebar }          from './components/layout/Sidebar'
import { MainDashboard }    from './components/layout/MainDashboard'
import { ChatPanel }        from './components/chat/ChatPanel'

function TopBar() {
  return (
    <header className="h-9 border-b border-fs-border bg-fs-surface/80 backdrop-blur-sm flex items-center px-4 gap-3 flex-shrink-0">
      <div className="flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-green-400" style={{boxShadow:'0 0 6px rgba(34,197,94,0.8)'}} />
        <span className="text-[10px] font-mono text-fs-muted">LIVE</span>
      </div>
      <div className="h-3 w-px bg-fs-border" />
      <span className="text-[10px] font-mono text-fs-muted">NYSE · NASDAQ · Powered by Claude</span>
      <div className="ml-auto text-[10px] font-mono text-fs-muted">FinSight v0.1.0</div>
    </header>
  )
}

export default function DashboardPage() {
  const [chatOpen, setChatOpen] = useState(true)

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <TopBar />

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <Sidebar />

        {/* Center content */}
        <main className="flex-1 overflow-hidden bg-fs-bg">
          <MainDashboard />
        </main>

        {/* Right chat panel */}
        <aside className={[
          'flex flex-col border-l border-fs-border bg-fs-surface',
          'transition-all duration-300 ease-in-out flex-shrink-0',
          chatOpen ? 'w-[340px]' : 'w-0 overflow-hidden border-l-0',
        ].join(' ')}>
          {chatOpen && <ChatPanel />}
        </aside>
      </div>

      {/* Mobile chat toggle */}
      <button
        onClick={() => setChatOpen(o => !o)}
        className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-blue-600 text-white flex items-center justify-center md:hidden"
      >
        {chatOpen ? <X className="w-5 h-5" /> : <MessageSquare className="w-5 h-5" />}
      </button>
    </div>
  )
}
