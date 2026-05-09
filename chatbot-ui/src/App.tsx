import { AnimatePresence, motion } from 'framer-motion'
import { Bot, OctagonX, Plus, Send, Settings2, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { cn } from './lib/cn'
import { parseSseStream } from './lib/sse'

type Role = 'user' | 'assistant'

type ChatMessage = {
  id: string
  role: Role
  content: string
  createdAt: number
}

type ChatThread = {
  id: string
  title: string
  sessionId: string
  messages: ChatMessage[]
  updatedAt: number
}

function uid(prefix: string) {
  return `${prefix}_${Math.random().toString(16).slice(2)}_${Date.now().toString(16)}`
}

function stableUserId() {
  const key = 'adk_ui_user_id'
  const existing = localStorage.getItem(key)
  if (existing) return existing
  const created =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : uid('user')
  localStorage.setItem(key, created)
  return created
}

function formatTime(ms: number) {
  const d = new Date(ms)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function App() {
  const initialThreads = useMemo<ChatThread[]>(
    () => [
      {
        id: 'thread_default',
        title: 'Travel helper prototype',
        sessionId: 'session_default',
        updatedAt: Date.now() - 1000 * 60 * 13,
        messages: [
          {
            id: 'm1',
            role: 'assistant',
            createdAt: Date.now() - 1000 * 60 * 13,
            content:
              "Hi! Tell me where you're traveling from and to, plus your passport country. I can help with entry requirements, weather, currency, airport transfer, and top attractions.",
          },
          {
            id: 'm2',
            role: 'user',
            createdAt: Date.now() - 1000 * 60 * 12,
            content: 'From Austin (USA) to Tokyo (Japan). Passport: USA.',
          },
          {
            id: 'm3',
            role: 'assistant',
            createdAt: Date.now() - 1000 * 60 * 11,
            content:
              "Got it — gathering info now. While I work: do you prefer public transit or taxi from the airport, and what's your travel date?",
          },
        ],
      },
      {
        id: 'thread_ideas',
        title: 'UI ideas',
        sessionId: 'session_ideas',
        updatedAt: Date.now() - 1000 * 60 * 60 * 5,
        messages: [
          {
            id: 'i1',
            role: 'assistant',
            createdAt: Date.now() - 1000 * 60 * 60 * 5,
            content:
              'This UI is a standalone prototype. Next step: connect it to `travel_helper_api` (streaming) and persist threads in localStorage.',
          },
        ],
      },
    ],
    [],
  )

  const [threads, setThreads] = useState<ChatThread[]>(initialThreads)
  const [activeThreadId, setActiveThreadId] = useState(threads[0]?.id ?? '')
  const [composer, setComposer] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const activeThread = threads.find((t) => t.id === activeThreadId) ?? threads[0]
  const abortRef = useRef<AbortController | null>(null)

  const listRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    const el = listRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [activeThreadId, activeThread?.messages.length])

  function newChat() {
    const now = Date.now()
    const thread: ChatThread = {
      id: uid('thread'),
      title: 'New chat',
      sessionId:
        typeof crypto !== 'undefined' && 'randomUUID' in crypto
          ? crypto.randomUUID()
          : uid('session'),
      updatedAt: now,
      messages: [
        {
          id: uid('m'),
          role: 'assistant',
          createdAt: now,
          content:
            "Hey! Where are you traveling from/to and what's your passport country?",
        },
      ],
    }
    setThreads((prev) => [thread, ...prev])
    setActiveThreadId(thread.id)
    setComposer('')
  }

  function stop() {
    abortRef.current?.abort()
    abortRef.current = null
    setIsThinking(false)
  }

  async function send() {
    const text = composer.trim()
    if (!text || !activeThread) return

    setComposer('')
    setIsThinking(true)
    setError(null)

    const now = Date.now()
    const userMessage: ChatMessage = {
      id: uid('m'),
      role: 'user',
      createdAt: now,
      content: text,
    }

    setThreads((prev) =>
      prev.map((t) =>
        t.id !== activeThread.id
          ? t
          : {
              ...t,
              title: t.title === 'New chat' ? text.slice(0, 28) : t.title,
              updatedAt: now,
              messages: [...t.messages, userMessage],
            },
      ),
    )

    const assistantId = uid('m')
    const assistantCreatedAt = Date.now()
    setThreads((prev) =>
      prev.map((t) =>
        t.id !== activeThread.id
          ? t
          : {
              ...t,
              updatedAt: assistantCreatedAt,
              messages: [
                ...t.messages,
                {
                  id: assistantId,
                  role: 'assistant',
                  createdAt: assistantCreatedAt,
                  content: '',
                },
              ],
            },
      ),
    )

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const res = await fetch('/v1/chat/stream', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          user_id: stableUserId(),
          session_id: activeThread.sessionId,
          message: text,
        }),
      })

      if (!res.ok || !res.body) {
        throw new Error(`Request failed (${res.status})`)
      }

      for await (const msg of parseSseStream(res.body, controller.signal)) {
        // Backend sends: data: {"type":"delta","text":"..."}\n\n
        let payload: unknown
        try {
          payload = JSON.parse(msg.data)
        } catch {
          continue
        }
        if (!payload || typeof payload !== 'object') continue

        const type = (payload as { type?: unknown }).type
        if (type === 'delta') {
          const delta = (payload as { text?: unknown }).text
          if (typeof delta !== 'string' || !delta) continue
          setThreads((prev) =>
            prev.map((t) =>
              t.id !== activeThread.id
                ? t
                : {
                    ...t,
                    updatedAt: Date.now(),
                    messages: t.messages.map((m) =>
                      m.id !== assistantId ? m : { ...m, content: m.content + delta },
                    ),
                  },
            ),
          )
        } else if (type === 'final') {
          break
        } else if (type === 'error') {
          const message = (payload as { message?: unknown }).message
          throw new Error(typeof message === 'string' ? message : 'Agent execution failed')
        }
      }
    } catch (e) {
      if ((e as Error)?.name !== 'AbortError') {
        setError(e instanceof Error ? e.message : 'Failed to stream response')
      }
    } finally {
      abortRef.current = null
      setIsThinking(false)
    }
  }

  return (
    <div className="min-h-dvh p-4 sm:p-6">
      <div className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-[320px_1fr]">
        <aside className="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-[0_10px_50px_-20px_rgba(0,0,0,0.8)] backdrop-blur-xl">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="grid h-10 w-10 place-items-center rounded-2xl bg-white/10 ring-1 ring-white/10">
                <Bot className="h-5 w-5 text-white/90" />
              </div>
              <div>
                <div className="text-sm font-semibold tracking-tight text-white/90">
                  ADK Chat UI
                </div>
                <div className="text-xs text-white/60">Prototype</div>
              </div>
            </div>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/10 px-3 py-2 text-xs font-medium text-white/80 transition hover:bg-white/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400/60"
              onClick={newChat}
            >
              <Plus className="h-4 w-4" />
              New
            </button>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div className="text-xs font-medium text-white/60">Chats</div>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-xl px-2 py-1 text-xs text-white/55 transition hover:bg-white/10 hover:text-white/75 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400/60"
            >
              <Settings2 className="h-4 w-4" />
              Settings
            </button>
          </div>

          <div className="mt-2 grid gap-2">
            {threads
              .slice()
              .sort((a, b) => b.updatedAt - a.updatedAt)
              .map((t) => {
                const isActive = t.id === activeThreadId
                const last = t.messages[t.messages.length - 1]
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setActiveThreadId(t.id)}
                    className={cn(
                      'group rounded-2xl border px-3 py-3 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400/60',
                      isActive
                        ? 'border-white/15 bg-white/10'
                        : 'border-white/10 bg-white/5 hover:bg-white/10',
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="truncate text-sm font-medium text-white/85">
                        {t.title}
                      </div>
                      <div className="shrink-0 text-[11px] text-white/45">
                        {formatTime(t.updatedAt)}
                      </div>
                    </div>
                    <div className="mt-1 line-clamp-2 text-xs text-white/55">
                      {last?.content ?? '—'}
                    </div>
                  </button>
                )
              })}
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-gradient-to-b from-white/10 to-white/5 p-3">
            <div className="flex items-start gap-2">
              <div className="mt-0.5 grid h-8 w-8 place-items-center rounded-xl bg-violet-500/20 ring-1 ring-violet-400/20">
                <Sparkles className="h-4 w-4 text-violet-200" />
              </div>
              <div>
                <div className="text-xs font-semibold text-white/80">
                  UX notes
                </div>
                <div className="mt-1 text-xs leading-relaxed text-white/55">
                  Designed for fast scanning, strong contrast, and keyboard-first
                  controls.
                </div>
              </div>
            </div>
          </div>
        </aside>

        <main className="flex min-h-[70dvh] flex-col overflow-hidden rounded-3xl border border-white/10 bg-white/5 shadow-[0_10px_50px_-20px_rgba(0,0,0,0.8)] backdrop-blur-xl">
          <div className="flex items-center justify-between gap-4 border-b border-white/10 px-4 py-4 sm:px-6">
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-white/90">
                {activeThread?.title ?? 'Chat'}
              </div>
              <div className="mt-0.5 text-xs text-white/55">
                {error ? `Error: ${error}` : isThinking ? 'Assistant is thinking…' : 'Ready'}
              </div>
            </div>
            <div className="hidden items-center gap-2 sm:flex">
              <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/60">
                Local prototype
              </div>
              <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/60">
                Tailwind + Motion
              </div>
            </div>
          </div>

          <div
            ref={listRef}
            className="scroll-smooth flex-1 overflow-y-auto px-3 py-4 sm:px-6"
          >
            <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
              <AnimatePresence initial={false}>
                {(activeThread?.messages ?? []).map((m) => (
                  <motion.div
                    key={m.id}
                    initial={{ opacity: 0, y: 8, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -6, scale: 0.98 }}
                    transition={{ duration: 0.18, ease: 'easeOut' }}
                    className={cn(
                      'flex w-full',
                      m.role === 'user' ? 'justify-end' : 'justify-start',
                    )}
                  >
                    <div
                      className={cn(
                        'max-w-[92%] rounded-3xl border px-4 py-3 text-sm leading-relaxed shadow-sm sm:max-w-[80%]',
                        m.role === 'user'
                          ? 'border-violet-400/20 bg-violet-500/20 text-white'
                          : 'border-white/10 bg-white/10 text-white/90',
                      )}
                    >
                      <div className="whitespace-pre-wrap">{m.content}</div>
                      <div className="mt-2 text-[11px] text-white/45">
                        {formatTime(m.createdAt)}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {isThinking && (
                <div className="flex justify-start">
                  <div className="rounded-3xl border border-white/10 bg-white/10 px-4 py-3 text-sm text-white/75">
                    <span className="inline-flex items-center gap-1">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white/70" />
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white/50 [animation-delay:120ms]" />
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white/35 [animation-delay:240ms]" />
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="border-t border-white/10 bg-white/5 p-3 sm:p-4">
            <div className="mx-auto flex w-full max-w-3xl items-end gap-2">
              <div className="flex-1 rounded-3xl border border-white/10 bg-white/5 px-3 py-2 focus-within:border-violet-400/30 focus-within:ring-2 focus-within:ring-violet-400/20">
                <textarea
                  value={composer}
                  onChange={(e) => setComposer(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      void send()
                    }
                  }}
                  placeholder="Ask about visas, weather, currency, airport transfer…"
                  rows={1}
                  className="max-h-40 w-full resize-none bg-transparent text-sm text-white/90 placeholder:text-white/40 focus:outline-none"
                />
                <div className="mt-1 flex items-center justify-between text-[11px] text-white/45">
                  <div>Enter to send · Shift+Enter for newline</div>
                  <div className="tabular-nums">{composer.length}/2000</div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => void send()}
                disabled={!composer.trim() || isThinking}
                className={cn(
                  'inline-flex h-12 items-center justify-center gap-2 rounded-2xl px-4 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400/60',
                  !composer.trim() || isThinking
                    ? 'cursor-not-allowed bg-white/10 text-white/40'
                    : 'bg-violet-500/80 text-white hover:bg-violet-500',
                )}
              >
                <Send className="h-4 w-4" />
                Send
              </button>
              {isThinking && (
                <button
                  type="button"
                  onClick={stop}
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/10 px-4 text-sm font-semibold text-white/80 transition hover:bg-white/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400/60"
                >
                  <OctagonX className="h-4 w-4" />
                  Stop
                </button>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
