'use client'

/**
 * ChatPanel
 * ==========
 * Streaming AI chat interface powered by Claude via SSE.
 *
 * Architecture:
 *  - Reads/writes chat history from Zustand store.
 *  - On submit: adds user message, creates empty assistant placeholder,
 *    then streams token deltas via appendAssistantDelta.
 *  - AbortController cancels in-flight streams on component unmount
 *    or when user sends a new message.
 *  - Auto-scrolls to bottom on new content.
 *  - Supports Markdown via dangerouslySetInnerHTML on assistant messages.
 */

import {
  useCallback, useEffect, useRef,
  useState, type KeyboardEvent,
} from 'react'
import {
  Send, Bot, User, Trash2, Copy,
  CheckCheck, Loader2, AlertCircle, X,
} from 'lucide-react'

import { streamChat, APIResponseError } from '@/lib/api'
import {
  useFinSightStore,
  selectChat,
  selectActions,
  selectRAG,
} from '@/store/useFinSightStore'
import type { ChatMessage } from '@/types'

// ── Markdown renderer (lightweight, no dependency) ───────────

function renderMarkdown(text: string): string {
  return text
    // Code blocks
    .replace(/```[\s\S]*?```/g, m =>
      `<pre class="bg-fs-subtle border border-fs-border rounded-lg p-3 my-2 text-xs font-mono overflow-x-auto whitespace-pre-wrap">${m.slice(3, -3).replace(/^\w+\n/, '')}</pre>`)
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="bg-fs-subtle text-blue-300 px-1.5 py-0.5 rounded text-xs font-mono">$1</code>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-fs-text font-semibold">$1</strong>')
    // H3 headings
    .replace(/^### (.+)$/gm, '<h3 class="text-sm font-semibold text-fs-text mt-3 mb-1">$1</h3>')
    // H2 headings
    .replace(/^## (.+)$/gm, '<h2 class="text-sm font-bold text-fs-text mt-3 mb-1.5">$1</h2>')
    // Unordered list items
    .replace(/^[•\-\*] (.+)$/gm, '<li class="ml-4 list-disc text-fs-muted text-sm">$1</li>')
    // Numbered list items
    .replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal text-fs-muted text-sm">$1</li>')
    // Paragraphs (double newline)
    .replace(/\n\n/g, '</p><p class="text-sm text-fs-muted leading-relaxed mt-2">')
    // Single newlines
    .replace(/\n/g, '<br/>')
}

// ── Copy button (single message) ─────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      className="opacity-0 group-hover:opacity-100 text-fs-muted hover:text-fs-text transition-all"
      aria-label="Copy message"
    >
      {copied
        ? <CheckCheck className="w-3.5 h-3.5 text-green-400" />
        : <Copy       className="w-3.5 h-3.5" />}
    </button>
  )
}

// ── Message bubble ────────────────────────────────────────────

interface MessageBubbleProps {
  message:    ChatMessage
  isLast:     boolean
  isStreaming:boolean
}

function MessageBubble({ message, isLast, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const showCursor = isLast && isStreaming && !isUser

  return (
    <div className={[
      'group flex gap-3 px-1 animate-fade-in',
      isUser ? 'flex-row-reverse' : 'flex-row',
    ].join(' ')}>

      {/* Avatar */}
      <div className={[
        'w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5',
        isUser
          ? 'bg-blue-600/20 border border-blue-500/30'
          : 'bg-purple-600/20 border border-purple-500/30',
      ].join(' ')}>
        {isUser
          ? <User className="w-3.5 h-3.5 text-blue-400" />
          : <Bot  className="w-3.5 h-3.5 text-purple-400" />}
      </div>

      {/* Bubble */}
      <div className={[
        'flex flex-col gap-1 max-w-[85%]',
        isUser ? 'items-end' : 'items-start',
      ].join(' ')}>
        <div className={[
          'rounded-xl px-3.5 py-2.5',
          isUser
            ? 'bg-blue-600/15 border border-blue-500/25 text-fs-text text-sm'
            : 'bg-fs-surface border border-fs-border',
        ].join(' ')}>

          {isUser ? (
            <p className="text-sm text-fs-text leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          ) : (
            <div
              className={[
                'text-sm text-fs-muted leading-relaxed prose-sm',
                showCursor ? 'streaming-cursor' : '',
              ].join(' ')}
              dangerouslySetInnerHTML={{
                __html: message.content.length > 0
                  ? `<p class="text-sm text-fs-muted leading-relaxed">${renderMarkdown(message.content)}</p>`
                  : '<span class="text-fs-muted/50">Thinking…</span>',
              }}
            />
          )}
        </div>

        {/* Actions row */}
        {!isUser && message.content.length > 0 && (
          <div className="flex items-center gap-1 px-1">
            <CopyButton text={message.content} />
          </div>
        )}
      </div>
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────

function EmptyChat() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 py-8">
      <div className="w-12 h-12 rounded-2xl bg-purple-600/15 border border-purple-500/25 flex items-center justify-center">
        <Bot className="w-6 h-6 text-purple-400" />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-fs-text">FinSight AI</p>
        <p className="text-xs text-fs-muted mt-1 max-w-[200px] leading-relaxed">
          Ask about markets, valuations, SEC filings, or any financial concept.
        </p>
      </div>
      {/* Quick prompts */}
      <div className="w-full space-y-1.5 mt-2">
        {[
          'Explain P/E vs EV/EBITDA',
          'What signals an inverted yield curve?',
          'How to read a 10-K filing?',
        ].map(prompt => (
          <QuickPromptButton key={prompt} prompt={prompt} />
        ))}
      </div>
    </div>
  )
}

// ── Quick prompt button ───────────────────────────────────────

function QuickPromptButton({ prompt }: { prompt: string }) {
  const actions = useFinSightStore(selectActions)
  const chat    = useFinSightStore(selectChat)

  // Only show when chat is empty
  if (chat.messages.length > 0) return null

  return (
    <button
      onClick={() => {
        actions.addUserMessage(prompt)
        // Trigger submission via custom event (ChatPanel listens)
        window.dispatchEvent(new CustomEvent('finsight:quickprompt', { detail: prompt }))
      }}
      className="w-full text-left px-3 py-2 rounded-lg text-xs text-fs-muted
                 border border-fs-border hover:border-fs-border-2 hover:text-fs-text
                 hover:bg-white/5 transition-all duration-150"
    >
      → {prompt}
    </button>
  )
}

// ── Main Component ────────────────────────────────────────────

interface ChatPanelProps {
  /** Optionally inject RAG context from the Document Q&A workflow */
  extraContext?: string
}

export function ChatPanel({ extraContext }: ChatPanelProps) {
  const chat    = useFinSightStore(selectChat)
  const rag     = useFinSightStore(selectRAG)
  const actions = useFinSightStore(selectActions)

  const [inputValue, setInputValue]   = useState('')
  const abortRef                      = useRef<AbortController | null>(null)
  const scrollRef                     = useRef<HTMLDivElement>(null)
  const inputRef                      = useRef<HTMLTextAreaElement>(null)

  // ── Auto-scroll to bottom ──────────────────────────────────
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top:      scrollRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [chat.messages, chat.isStreaming])

  // ── Listen for quick prompt events ────────────────────────
  useEffect(() => {
    const handler = (e: Event) => {
      const prompt = (e as CustomEvent<string>).detail
      sendMessage(prompt)
    }
    window.addEventListener('finsight:quickprompt', handler)
    return () => window.removeEventListener('finsight:quickprompt', handler)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Cleanup on unmount ─────────────────────────────────────
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  // ── Core streaming logic ───────────────────────────────────

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || chat.isStreaming) return

    // Cancel any in-flight request
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    actions.addUserMessage(trimmed)
    actions.addAssistantMessage('')   // placeholder for streaming
    actions.setStreaming(true)
    actions.setStreamError(null)
    setInputValue('')

    const messages = [
      ...chat.messages,
      { role: 'user' as const, content: trimmed },
    ]

    try {
      const reader = await streamChat(
        messages,
        extraContext,
        abortRef.current.signal,
      )

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        actions.appendAssistantDelta(value)
      }
    } catch (err: unknown) {
      if ((err as { name?: string }).name === 'AbortError') return

      const message = err instanceof APIResponseError
        ? err.message
        : err instanceof Error
          ? err.message
          : 'Something went wrong. Please try again.'

      actions.setStreamError(message)
    } finally {
      actions.setStreaming(false)
    }
  }, [chat.messages, chat.isStreaming, extraContext, actions])

  const handleSubmit = () => sendMessage(inputValue)

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleAbort = () => {
    abortRef.current?.abort()
    actions.setStreaming(false)
  }

  // ── Render ─────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-fs-border flex-shrink-0">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-semibold text-fs-text">AI Chat</span>
          <span className="section-label ml-1">claude-sonnet-4-6</span>
        </div>
        <div className="flex items-center gap-1">
          {rag.documents.length > 0 && (
            <div className="text-[10px] font-mono text-green-400 bg-green-500/10 border border-green-500/20 px-2 py-0.5 rounded-full">
              RAG · {rag.documents.length} doc{rag.documents.length > 1 ? 's' : ''}
            </div>
          )}
          {chat.messages.length > 0 && (
            <button
              onClick={() => actions.clearChat()}
              className="btn-ghost p-1.5"
              aria-label="Clear chat"
              title="Clear conversation"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar"
      >
        {chat.messages.length === 0 ? (
          <EmptyChat />
        ) : (
          chat.messages.map((msg, i) => (
            <MessageBubble
              key={i}
              message={msg}
              isLast={i === chat.messages.length - 1}
              isStreaming={chat.isStreaming}
            />
          ))
        )}
      </div>

      {/* Error banner */}
      {chat.streamError && (
        <div className="mx-4 mb-2 flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 animate-fade-in">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span className="flex-1">{chat.streamError}</span>
          <button
            onClick={() => actions.setStreamError(null)}
            className="hover:text-red-300"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Input area */}
      <div className="px-4 pb-4 pt-2 border-t border-fs-border flex-shrink-0">
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about markets, valuations, filings…"
            rows={1}
            style={{ resize: 'none' }}
            className={[
              'input-premium flex-1 py-2.5 leading-relaxed',
              'min-h-[42px] max-h-[120px] overflow-y-auto',
              // Auto-grow via JS
            ].join(' ')}
            onInput={(e) => {
              const el = e.currentTarget
              el.style.height = 'auto'
              el.style.height = `${Math.min(el.scrollHeight, 120)}px`
            }}
            disabled={chat.isStreaming}
            aria-label="Chat input"
          />

          {chat.isStreaming ? (
            <button
              onClick={handleAbort}
              className="btn-outline px-3 py-2.5 text-red-400 border-red-500/30 hover:bg-red-500/10 flex-shrink-0"
              aria-label="Stop generation"
              title="Stop"
            >
              <X className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!inputValue.trim() || chat.isStreaming}
              className="btn-primary px-3 py-2.5 flex-shrink-0"
              aria-label="Send message"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>
        <p className="text-[10px] text-fs-muted mt-1.5 text-center">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
