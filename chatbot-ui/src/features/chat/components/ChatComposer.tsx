import { OctagonX, Send } from 'lucide-react'
import { cn } from '@/shared/lib/cn'

type ChatComposerProps = {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  isThinking: boolean
  onStop: () => void
}

export function ChatComposer({
  value,
  onChange,
  onSend,
  isThinking,
  onStop,
}: ChatComposerProps) {
  return (
    <div className="border-t border-white/10 bg-white/5 p-3 sm:p-4">
      <div className="mx-auto flex w-full max-w-3xl items-end gap-2">
        <div className="flex-1 rounded-3xl border border-white/10 bg-white/5 px-3 py-2 focus-within:border-violet-400/30 focus-within:ring-2 focus-within:ring-violet-400/20">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void onSend()
              }
            }}
            placeholder="Ask about visas, weather, currency, airport transfer…"
            rows={1}
            className="max-h-40 w-full resize-none bg-transparent text-sm text-white/90 placeholder:text-white/40 focus:outline-none"
          />
          <div className="mt-1 flex items-center justify-between text-[11px] text-white/45">
            <div>Enter to send · Shift+Enter for newline</div>
            <div className="tabular-nums">{value.length}/2000</div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void onSend()}
          disabled={!value.trim() || isThinking}
          className={cn(
            'inline-flex h-12 items-center justify-center gap-2 rounded-2xl px-4 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400/60',
            !value.trim() || isThinking
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
            onClick={onStop}
            className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/10 px-4 text-sm font-semibold text-white/80 transition hover:bg-white/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400/60"
          >
            <OctagonX className="h-4 w-4" />
            Stop
          </button>
        )}
      </div>
    </div>
  )
}
