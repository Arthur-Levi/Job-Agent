import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-sky-500 text-slate-950 hover:bg-sky-400',
  secondary: 'bg-slate-800 text-slate-100 hover:bg-slate-700 ring-1 ring-slate-700',
  danger: 'bg-rose-500/15 text-rose-300 hover:bg-rose-500/25 ring-1 ring-rose-400/30',
  ghost: 'text-slate-300 hover:bg-slate-800',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
}

export function Button({ variant = 'primary', className = '', type = 'button', ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  )
}
