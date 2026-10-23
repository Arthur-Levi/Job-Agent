const APPLICATION: Record<string, string> = {
  DISCOVERED: 'bg-slate-700/60 text-slate-200 ring-slate-500/40',
  QUALIFIED: 'bg-sky-500/15 text-sky-300 ring-sky-400/30',
  PREPARED: 'bg-indigo-500/15 text-indigo-300 ring-indigo-400/30',
  READY: 'bg-violet-500/15 text-violet-300 ring-violet-400/30',
  APPLIED: 'bg-blue-500/15 text-blue-300 ring-blue-400/30',
  RESPONSE: 'bg-cyan-500/15 text-cyan-300 ring-cyan-400/30',
  INTERVIEW: 'bg-amber-500/15 text-amber-300 ring-amber-400/30',
  TECHNICAL: 'bg-orange-500/15 text-orange-300 ring-orange-400/30',
  OFFER: 'bg-emerald-500/15 text-emerald-300 ring-emerald-400/30',
  REJECTED: 'bg-rose-500/15 text-rose-300 ring-rose-400/30',
  WITHDRAWN: 'bg-slate-600/30 text-slate-400 ring-slate-500/30',
  GHOSTED: 'bg-zinc-600/30 text-zinc-400 ring-zinc-500/30',
  OPEN: 'bg-emerald-500/15 text-emerald-300 ring-emerald-400/30',
  CLOSED: 'bg-slate-600/30 text-slate-400 ring-slate-500/30',
  ARCHIVED: 'bg-zinc-600/30 text-zinc-400 ring-zinc-500/30',
}

export function statusClasses(status: string): string {
  return APPLICATION[status] ?? 'bg-slate-700/60 text-slate-200 ring-slate-500/40'
}
