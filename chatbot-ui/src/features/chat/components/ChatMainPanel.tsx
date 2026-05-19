import type { RefObject } from 'react'
import type { ChatMessage, ChatThread } from '../types'
import { ChatComposer } from './ChatComposer'
import { ChatHeader } from './ChatHeader'
import { ChatMessageList } from './ChatMessageList'

type ChatMainPanelProps = {
  activeThread: ChatThread | undefined
  composer: string
  onComposerChange: (value: string) => void
  isThinking: boolean
  error: string | null
  listRef: RefObject<HTMLDivElement | null>
  onSend: () => void
  onStop: () => void
}

export function ChatMainPanel({
  activeThread,
  composer,
  onComposerChange,
  isThinking,
  error,
  listRef,
  onSend,
  onStop,
}: ChatMainPanelProps) {
  const title = activeThread?.title ?? 'Chat'
  const statusLine = error
    ? `Error: ${error}`
    : isThinking
      ? 'Assistant is thinking…'
      : 'Ready'

  const messages: ChatMessage[] = activeThread?.messages ?? []

  return (
    <main className="flex min-h-[70dvh] flex-col overflow-hidden rounded-3xl border border-white/10 bg-white/5 shadow-[0_10px_50px_-20px_rgba(0,0,0,0.8)] backdrop-blur-xl">
      <ChatHeader title={title} statusLine={statusLine} />
      <ChatMessageList messages={messages} listRef={listRef} isThinking={isThinking} />
      <ChatComposer
        value={composer}
        onChange={onComposerChange}
        onSend={onSend}
        isThinking={isThinking}
        onStop={onStop}
      />
    </main>
  )
}
