'use client'

/**
 * DocumentUpload
 * ===============
 * Premium drag-and-drop PDF uploader with background-task polling.
 *
 * Flow:
 *  1. User drops/selects PDF → validate client-side
 *  2. POST /api/v1/rag/upload → 202 + job_id
 *  3. Poll GET /api/v1/rag/jobs/{job_id} every 2s
 *  4. Progress bar animates based on elapsed time + final status
 *  5. On complete: refresh document list from Zustand
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useDropzone }                              from 'react-dropzone'
import {
  FileText, Upload, CheckCircle2, XCircle,
  Loader2, X, AlertTriangle,
} from 'lucide-react'

import { ragApi }             from '@/lib/api'
import {
  useFinSightStore,
  selectActions,
  selectRAG,
} from '@/store/useFinSightStore'
import type { JobStatus }     from '@/types'

// ── Constants ────────────────────────────────────────────────

const MAX_FILE_SIZE_MB = 20
const MAX_FILE_SIZE    = MAX_FILE_SIZE_MB * 1024 * 1024
const POLL_INTERVAL_MS = 2_000
const PROGRESS_FILL_MS = 8_000 // approx time for progress to reach ~85%

// ── Progress animation helper ────────────────────────────────
// Simulates progress 0→85% over PROGRESS_FILL_MS then waits for real status.

function useProgressAnimation(isActive: boolean): number {
  const [progress, setProgress] = useState(0)
  const startRef = useRef<number | null>(null)
  const rafRef   = useRef<number>()

  useEffect(() => {
    if (!isActive) {
      setProgress(0)
      startRef.current = null
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      return
    }

    startRef.current = performance.now()

    const tick = (now: number) => {
      const elapsed  = now - (startRef.current ?? now)
      const fraction = Math.min(elapsed / PROGRESS_FILL_MS, 1)
      // Ease-out cubic: fast start, slow approach to 85%
      const eased = 1 - Math.pow(1 - fraction, 3)
      setProgress(Math.round(eased * 85))

      if (fraction < 1) {
        rafRef.current = requestAnimationFrame(tick)
      }
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [isActive])

  return progress
}

// ── Sub-component: Job Progress Bar ──────────────────────────

interface ProgressPanelProps {
  filename:      string
  status:        JobStatus
  chunks:        number | null
  error:         string | null
  storeProgress: number
  onDismiss:     () => void
}

function ProgressPanel({
  filename, status, chunks, error, storeProgress, onDismiss,
}: ProgressPanelProps) {
  const animProgress = useProgressAnimation(status === 'processing')
  const displayProgress =
    status === 'complete' ? 100 :
    status === 'failed'   ? 0   :
    Math.max(animProgress, storeProgress)

  return (
    <div className="glass-card p-4 mt-3 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-4 h-4 text-blue-400 flex-shrink-0" />
          <span className="text-sm text-fs-text truncate font-medium">
            {filename}
          </span>
        </div>
        <button
          onClick={onDismiss}
          className="text-fs-muted hover:text-fs-text transition-colors flex-shrink-0"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-fs-subtle rounded-full overflow-hidden mb-2">
        <div
          className={[
            'h-full rounded-full transition-all duration-500',
            status === 'complete' ? 'bg-green-500' :
            status === 'failed'   ? 'bg-red-500'   :
            'bg-blue-500',
          ].join(' ')}
          style={{ width: `${displayProgress}%` }}
        />
      </div>

      {/* Status row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-fs-muted">
          {status === 'processing' && (
            <>
              <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
              <span>Embedding document…</span>
            </>
          )}
          {status === 'complete' && (
            <>
              <CheckCircle2 className="w-3 h-3 text-green-400" />
              <span className="text-green-400">
                Ready — {chunks?.toLocaleString()} chunks indexed
              </span>
            </>
          )}
          {status === 'failed' && (
            <>
              <AlertTriangle className="w-3 h-3 text-red-400" />
              <span className="text-red-400 truncate max-w-[200px]" title={error ?? ''}>
                {error ?? 'Failed to index document'}
              </span>
            </>
          )}
        </div>
        <span className="text-xs font-mono text-fs-muted">
          {displayProgress}%
        </span>
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────

export function DocumentUpload() {
  const rag     = useFinSightStore(selectRAG)
  const actions = useFinSightStore(selectActions)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Stop polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  // ── Polling logic ──────────────────────────────────────────

  const startPolling = useCallback((jobId: string) => {
    let attempts = 0
    const MAX_ATTEMPTS = 150 // 5 minutes at 2s intervals

    pollRef.current = setInterval(async () => {
      attempts++

      if (attempts > MAX_ATTEMPTS) {
        clearInterval(pollRef.current!)
        actions.failUploadJob('Embedding timed out. Please try again.')
        return
      }

      try {
        const job = await ragApi.getJobStatus(jobId)

        // Nudge progress forward so it doesn't stall at 85%
        if (job.status === 'processing') {
          const nudge = Math.min(85 + Math.floor(attempts / 5), 95)
          actions.updateUploadJob({ progress: nudge })
        }

        if (job.status === 'complete') {
          clearInterval(pollRef.current!)
          actions.completeUploadJob(job.chunks_indexed ?? 0)
          // Refresh document list
          ragApi.listDocuments().then(r => actions.setDocuments(r.documents))
        } else if (job.status === 'failed') {
          clearInterval(pollRef.current!)
          actions.failUploadJob(job.error ?? 'Embedding failed')
        }
      } catch {
        // Network hiccup — keep polling
      }
    }, POLL_INTERVAL_MS)
  }, [actions])

  // ── Upload handler ─────────────────────────────────────────

  const handleUpload = useCallback(async (file: File) => {
    if (pollRef.current) clearInterval(pollRef.current)

    try {
      const resp = await ragApi.uploadDocument(file)
      actions.startUploadJob(resp.job_id, resp.filename)
      startPolling(resp.job_id)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      actions.startUploadJob('failed', file.name)
      actions.failUploadJob(msg)
    }
  }, [actions, startPolling])

  // ── Dropzone ───────────────────────────────────────────────

  const { getRootProps, getInputProps, isDragActive, fileRejections } =
    useDropzone({
      onDropAccepted: ([file]) => handleUpload(file!),
      accept:         { 'application/pdf': ['.pdf'] },
      maxFiles:       1,
      maxSize:        MAX_FILE_SIZE,
      disabled:       rag.isUploading,
    })

  const rejectionError = fileRejections[0]?.errors[0]?.message

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={[
          'transition-all duration-200 cursor-pointer',
          isDragActive  ? 'dropzone-active' : 'dropzone-idle',
          rag.isUploading ? 'opacity-50 cursor-not-allowed pointer-events-none' : '',
        ].join(' ')}
        role="button"
        aria-label="Upload PDF document"
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-2 py-2">
          {rag.isUploading ? (
            <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
          ) : (
            <Upload className={[
              'w-6 h-6 transition-colors',
              isDragActive ? 'text-blue-400' : 'text-fs-muted',
            ].join(' ')} />
          )}
          <div className="text-center">
            <p className="text-sm font-medium text-fs-text">
              {isDragActive ? 'Drop PDF here' : 'Upload PDF'}
            </p>
            <p className="text-xs text-fs-muted mt-0.5">
              10-K, 10-Q, earnings transcripts · Max {MAX_FILE_SIZE_MB} MB
            </p>
          </div>
        </div>
      </div>

      {/* Validation error */}
      {rejectionError && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          <XCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>{rejectionError}</span>
        </div>
      )}

      {/* Progress panel */}
      {rag.activeJob && (
        <ProgressPanel
          filename={rag.activeJob.filename}
          status={rag.activeJob.status}
          chunks={rag.activeJob.chunksIndexed}
          error={rag.activeJob.error}
          storeProgress={rag.activeJob.progress}
          onDismiss={() => actions.clearUploadJob()}
        />
      )}
    </div>
  )
}
