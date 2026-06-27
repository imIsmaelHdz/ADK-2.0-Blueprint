import type { ChatThread } from './types'

export function createSeedThreads(): ChatThread[] {
  return [
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
  ]
}
