export function uid(prefix: string) {
  return `${prefix}_${Math.random().toString(16).slice(2)}_${Date.now().toString(16)}`
}

export function stableUserId() {
  const key = 'adk_ui_user_id'
  const existing = localStorage.getItem(key)
  if (existing) return existing
  const created =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : uid('user')
  localStorage.setItem(key, created)
  return created
}

export function formatTime(ms: number) {
  const d = new Date(ms)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
