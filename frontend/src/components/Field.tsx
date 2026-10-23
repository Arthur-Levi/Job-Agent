import { useId } from 'react'
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'

const CONTROL =
  'w-full rounded-md border bg-slate-950 px-3 py-1.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500/60'

interface ShellProps {
  id: string
  label: string
  error?: string | undefined
  hint?: string | undefined
  children: ReactNode
}

function Shell({ id, label, error, hint, children }: ShellProps) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-slate-400">
        {label}
      </label>
      {children}
      {hint && !error ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
      {error ? (
        <p id={`${id}-error`} role="alert" className="mt-1 text-xs text-rose-400">
          {error}
        </p>
      ) : null}
    </div>
  )
}

interface FieldProps {
  label: string
  error?: string | undefined
  hint?: string | undefined
}

function borderFor(error?: string): string {
  return error ? 'border-rose-500/60' : 'border-slate-700'
}

export function TextField({
  label,
  error,
  hint,
  ...props
}: FieldProps & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId()
  return (
    <Shell id={id} label={label} error={error} hint={hint}>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className={`${CONTROL} ${borderFor(error)}`}
        {...props}
      />
    </Shell>
  )
}

export function TextAreaField({
  label,
  error,
  hint,
  ...props
}: FieldProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId()
  return (
    <Shell id={id} label={label} error={error} hint={hint}>
      <textarea
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className={`${CONTROL} ${borderFor(error)}`}
        {...props}
      />
    </Shell>
  )
}

export interface Option {
  value: string
  label: string
}

export function SelectField({
  label,
  error,
  hint,
  options,
  placeholder,
  ...props
}: FieldProps &
  SelectHTMLAttributes<HTMLSelectElement> & { options: readonly Option[]; placeholder?: string }) {
  const id = useId()
  return (
    <Shell id={id} label={label} error={error} hint={hint}>
      <select
        id={id}
        aria-invalid={error ? true : undefined}
        className={`${CONTROL} ${borderFor(error)}`}
        {...props}
      >
        {placeholder !== undefined ? <option value="">{placeholder}</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </Shell>
  )
}
