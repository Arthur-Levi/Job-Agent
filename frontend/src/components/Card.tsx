import type { HTMLAttributes } from 'react'

export function Card({ className = '', ...props }: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={`rounded-lg border border-slate-800 bg-slate-900/60 p-4 ${className}`}
      {...props}
    />
  )
}
