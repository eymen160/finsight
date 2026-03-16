'use client'

import { useEffect } from 'react'
import { FileText, Trash2 } from 'lucide-react'
import { ragApi }                          from '@/lib/api'
import { useFinSightStore, selectRAG, selectActions } from '@/store/useFinSightStore'

export function DocumentList() {
  const rag     = useFinSightStore(selectRAG)
  const actions = useFinSightStore(selectActions)

  useEffect(() => {
    ragApi.listDocuments()
      .then(r => actions.setDocuments(r.documents))
      .catch(() => {/* backend may not be running */})
  }, [actions])

  if (rag.documents.length === 0) {
    return (
      <p className="text-xs text-fs-muted italic">No documents indexed yet.</p>
    )
  }

  return (
    <div className="space-y-1.5">
      {rag.documents.map(doc => (
        <div
          key={doc}
          className="flex items-center gap-2 bg-green-500/5 border border-green-500/15 rounded-lg px-2.5 py-1.5"
        >
          <FileText className="w-3 h-3 text-green-400 flex-shrink-0" />
          <span className="text-xs text-green-400 truncate flex-1 font-mono" title={doc}>
            {doc}
          </span>
        </div>
      ))}
      <button
        onClick={async () => {
          await ragApi.clearIndex().catch(() => {})
          actions.setDocuments([])
        }}
        className="w-full flex items-center justify-center gap-1.5 text-xs text-fs-muted hover:text-red-400 py-1.5 transition-colors"
      >
        <Trash2 className="w-3 h-3" />
        Clear index
      </button>
    </div>
  )
}
