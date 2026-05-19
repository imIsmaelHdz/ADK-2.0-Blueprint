import { Bot, Plus, Settings2, Sparkles } from 'lucide-react'
import { cn } from '@/shared/lib/cn'
import type { ChatThread } from '../types'
import { formatTime } from '../utils'

type ChatSidebarProps = {
  threads: ChatThread[]
  activeThreadId: string
  onNewChat: () => void
  onSelectThread: (id: string) => void
}

export function ChatSidebar({
  threads,
  activeThreadId,
  onNewChat,
  onSelectThread,
}: ChatSidebarProps) {
  return (
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
          onClick={onNewChat}
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
                onClick={() => onSelectThread(t.id)}
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
            <div className="text-xs font-semibold text-white/80">UX notes</div>
            <div className="mt-1 text-xs leading-relaxed text-white/55">
              Designed for fast scanning, strong contrast, and keyboard-first controls.
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
