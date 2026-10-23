/** 'FULL_TIME' -> 'Full time' */
export function labelize(value: string): string {
  const spaced = value.toLowerCase().replaceAll('_', ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeZone: 'UTC' }).format(date)
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function formatAmount(value: string, currency: string | null): string {
  const number = Number(value)
  if (!currency) return value
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(number)
  } catch {
    return `${currency} ${value}`
  }
}

/** Só para EXIBIÇÃO: o valor monetário continua string de ponta a ponta. */
export function formatSalary(
  min: string | null,
  max: string | null,
  currency: string | null,
): string {
  if (min && max) return `${formatAmount(min, currency)} – ${formatAmount(max, currency)}`
  if (min) return `from ${formatAmount(min, currency)}`
  if (max) return `up to ${formatAmount(max, currency)}`
  return '—'
}

/** <input type="date"> ('2026-10-01') -> ISO UTC aceito pelo backend. */
export function dateInputToIso(value: string): string | null {
  return value ? `${value}T00:00:00Z` : null
}

/** ISO (UTC) -> valor de <input type="date">. */
export function isoToDateInput(iso: string | null): string {
  return iso ? iso.slice(0, 10) : ''
}

export function blankToNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}
