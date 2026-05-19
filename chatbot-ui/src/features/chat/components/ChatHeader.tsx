type ChatHeaderProps = {
  title: string
  statusLine: string
}

export function ChatHeader({ title, statusLine }: ChatHeaderProps) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/10 px-4 py-4 sm:px-6">
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold text-white/90">{title}</div>
        <div className="mt-0.5 text-xs text-white/55">{statusLine}</div>
      </div>
      <div className="hidden items-center gap-2 sm:flex">
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/60">
          Local prototype
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/60">
          Tailwind + Motion
        </div>
      </div>
    </div>
  )
}
