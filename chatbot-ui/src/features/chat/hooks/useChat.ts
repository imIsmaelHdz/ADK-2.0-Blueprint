import { useEffect, useMemo, useRef, useState } from 'react'
import { postChatStream } from '../api/postChatStream'
import { readChatStreamEvents } from '../api/readChatStreamEvents'
import { createSeedThreads } from '../constants'
import type { ChatMessage, ChatThread } from '../types'
import { stableUserId, uid } from '../utils'

export function useChat() {
  const initialThreads = useMemo(() => createSeedThreads(), [])
  const [threads, setThreads] = useState<ChatThread[]>(initialThreads)
  const [activeThreadId, setActiveThreadId] = useState(initialThreads[0]?.id ?? '')
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
      const res = await postChatStream(
        {
          user_id: stableUserId(),
          session_id: activeThread.sessionId,
          message: text,
        },
        controller.signal,
      )

      if (!res.ok || !res.body) {
        throw new Error(`Request failed (${res.status})`)
      }

      for await (const ev of readChatStreamEvents(res.body, controller.signal)) {
        if (ev.type === 'delta') {
          setThreads((prev) =>
            prev.map((t) =>
              t.id !== activeThread.id
                ? t
                : {
                    ...t,
                    updatedAt: Date.now(),
                    messages: t.messages.map((m) =>
                      m.id !== assistantId ? m : { ...m, content: m.content + ev.text },
                    ),
                  },
            ),
          )
        } else if (ev.type === 'final') {
          break
        } else if (ev.type === 'error') {
          throw new Error(ev.message)
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

  return {
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
    selectThread: setActiveThreadId,
  }
}
