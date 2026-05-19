import { parseSseStream } from '@/shared/lib/sse'

export type ChatStreamEvent =
  | { type: 'delta'; text: string }
  | { type: 'final' }
  | { type: 'error'; message: string }

/**
 * Maps SSE `data:` JSON lines from the travel helper API into typed events.
 */
export async function* readChatStreamEvents(
  body: ReadableStream<Uint8Array>,
  signal: AbortSignal,
): AsyncGenerator<ChatStreamEvent, void, void> {
  for await (const msg of parseSseStream(body, signal)) {
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
      if (typeof delta === 'string' && delta) {
        yield { type: 'delta', text: delta }
      }
    } else if (type === 'final') {
      yield { type: 'final' }
      return
    } else if (type === 'error') {
      const message = (payload as { message?: unknown }).message
      yield {
        type: 'error',
        message: typeof message === 'string' ? message : 'Agent execution failed',
      }
      return
    }
  }
}
