export type ChatStreamRequestBody = {
  user_id: string
  session_id: string
  message: string
}

export function postChatStream(body: ChatStreamRequestBody, signal: AbortSignal) {
  return fetch('/v1/chat/stream', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    signal,
    body: JSON.stringify(body),
  })
}
