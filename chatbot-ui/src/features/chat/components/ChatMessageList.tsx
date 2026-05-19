import { AnimatePresence, motion } from 'framer-motion'
import { cn } from '@/shared/lib/cn'
import type { ChatMessage } from '../types'
import { formatTime } from '../utils'

type ChatMessageBubbleProps = {
  message: ChatMessage
}

export function ChatMessageBubble({ message: m }: ChatMessageBubbleProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -6, scale: 0.98 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
      className={cn('flex w-full', m.role === 'user' ? 'justify-end' : 'justify-start')}
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
        <div className="mt-2 text-[11px] text-white/45">{formatTime(m.createdAt)}</div>
      </div>
    </motion.div>
  )
}

type ChatMessageListProps = {
  messages: ChatMessage[]
  listRef: React.RefObject<HTMLDivElement | null>
  isThinking: boolean
}

export function ChatMessageList({ messages, listRef, isThinking }: ChatMessageListProps) {
  return (
    <div
      ref={listRef}
      className="scroll-smooth flex-1 overflow-y-auto px-3 py-4 sm:px-6"
    >
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
        <AnimatePresence initial={false}>
          {messages.map((m) => (
            <ChatMessageBubble key={m.id} message={m} />
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
  )
}
