import { ChatMainPanel } from './components/ChatMainPanel'
import { ChatSidebar } from './components/ChatSidebar'
import { useChat } from './hooks/useChat'

export function ChatPage() {
  const {
    threads,
    activeThreadId,
    activeThread,
    composer,
    setComposer,
    isThinking,
    error,
    listRef,
    newChat,
    send,
    stop,
    selectThread,
  } = useChat()

  return (
    <div className="min-h-dvh p-4 sm:p-6">
      <div className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-[320px_1fr]">
        <ChatSidebar
          threads={threads}
          activeThreadId={activeThreadId}
          onNewChat={newChat}
          onSelectThread={selectThread}
        />
        <ChatMainPanel
          activeThread={activeThread}
          composer={composer}
          onComposerChange={setComposer}
          isThinking={isThinking}
          error={error}
          listRef={listRef}
          onSend={send}
          onStop={stop}
        />
      </div>
    </div>
  )
}
