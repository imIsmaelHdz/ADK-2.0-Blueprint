export type Role = 'user' | 'assistant'

export type ChatMessage = {
  id: string
  role: Role
  content: string
  createdAt: number
}

export type ChatThread = {
  id: string
  title: string
  sessionId: string
  messages: ChatMessage[]
  updatedAt: number
}
