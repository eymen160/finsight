'use client'

import { useState } from 'react'
import {
  ChevronLeft, ChevronRight,
  BarChart2, FileText, MessageSquare, Home,
  TrendingUp, Settings,
} from 'lucide-react'
import { useFinSightStore, selectUI, selectActions } from '@/store/useFinSightStore'
import { DocumentUpload }  from '../rag/DocumentUpload'
import { DocumentList }    from '../rag/DocumentList'

export function Sidebar() {
  const { sidebarOpen } = useFinSightStore(selectUI)
  const { toggleSidebar } = useFinSightStore(selectActions)

  return (
    <aside
      className={[
        'relative flex flex-col border-r border-fs-border bg-fs-surface',
        'transition-all duration-300 ease-in-out flex-shrink-0',
        sidebarOpen ? 'w-[240px]' : 'w-[52px]',
      ].join(' ')}
    >
      {/* Toggle button */}
      <button
        onClick={toggleSidebar}
        className={[
          'absolute -right-3 top-6 z-10',
          'w-6 h-6 rounded-full bg-fs-surface border border-fs-border',
          'flex items-center justify-center',
          'text-fs-muted hover:text-fs-text hover:border-fs-border-2',
          'transition-all duration-150 shadow-card',
        ].join(' ')}
        aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
      >
        {sidebarOpen
          ? <ChevronLeft  className="w-3 h-3" />
          : <ChevronRight className="w-3 h-3" />}
      </button>

      {/* Logo */}
      <div className={[
        'flex items-center gap-2.5 px-3 py-4 border-b border-fs-border',
        sidebarOpen ? '' : 'justify-center',
      ].join(' ')}>
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-600 to-blue-500 flex items-center justify-center flex-shrink-0">
          <TrendingUp className="w-4 h-4 text-white" />
        </div>
        {sidebarOpen && (
          <div className="overflow-hidden">
            <p className="text-sm font-bold text-fs-text leading-none tracking-tight">FinSight</p>
            <p className="text-[9px] text-fs-muted mt-0.5 tracking-widest uppercase">AI Finance</p>
          </div>
        )}
      </div>

      {/* Nav items */}
      <nav className="p-2 space-y-0.5 border-b border-fs-border">
        {[
          { icon: BarChart2,     label: 'Dashboard',    active: true  },
          { icon: FileText,      label: 'Documents',    active: false },
          { icon: MessageSquare, label: 'Chat',         active: false },
        ].map(({ icon: Icon, label, active }) => (
          <button
            key={label}
            className={[
              sidebarOpen ? 'nav-item' : 'w-full p-2 rounded-lg flex justify-center',
              active ? 'nav-item-active' : '',
            ].join(' ')}
            title={!sidebarOpen ? label : undefined}
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {sidebarOpen && <span>{label}</span>}
          </button>
        ))}
      </nav>

      {/* Document management */}
      {sidebarOpen && (
        <div className="flex-1 overflow-y-auto p-3 space-y-4 no-scrollbar">
          <div>
            <p className="section-label mb-2">Upload Document</p>
            <DocumentUpload />
          </div>
          <div>
            <p className="section-label mb-2">Indexed Documents</p>
            <DocumentList />
          </div>
        </div>
      )}

      {/* Collapsed: just upload icon */}
      {!sidebarOpen && (
        <div className="flex-1 flex flex-col items-center pt-3 gap-2">
          <button
            className="w-8 h-8 rounded-lg bg-blue-600/15 border border-blue-500/25 flex items-center justify-center text-blue-400 hover:bg-blue-600/25 transition-colors"
            title="Upload PDF"
            onClick={toggleSidebar}
          >
            <FileText className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Footer */}
      <div className={[
        'p-3 border-t border-fs-border',
        sidebarOpen ? '' : 'flex justify-center',
      ].join(' ')}>
        <button
          className={sidebarOpen ? 'nav-item' : 'p-2 rounded-lg text-fs-muted hover:text-fs-text'}
          title="Settings"
        >
          <Settings className="w-4 h-4 flex-shrink-0" />
          {sidebarOpen && <span>Settings</span>}
        </button>
      </div>
    </aside>
  )
}
