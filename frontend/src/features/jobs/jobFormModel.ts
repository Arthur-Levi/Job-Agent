import type {
  EmploymentType,
  Job,
  JobInput,
  JobStatus,
  Seniority,
  WorkModel,
} from '../../types/api'
import { blankToNull, dateInputToIso, isoToDateInput } from '../../utils/format'

export interface JobFormValues {
  title: string
  company: string
  description: string
  location: string
  source: string
  source_url: string
  work_model: WorkModel | ''
  employment_type: EmploymentType | ''
  seniority: Seniority | ''
  salary_min: string
  salary_max: string
  currency: string
  published_at: string
  status: JobStatus
}

export function toJobValues(job?: Job): JobFormValues {
  return {
    title: job?.title ?? '',
    company: job?.company ?? '',
    description: job?.description ?? '',
    location: job?.location ?? '',
    source: job?.source ?? '',
    source_url: job?.source_url ?? '',
    work_model: job?.work_model ?? '',
    employment_type: job?.employment_type ?? '',
    seniority: job?.seniority ?? '',
    salary_min: job?.salary_min ?? '',
    salary_max: job?.salary_max ?? '',
    currency: job?.currency ?? '',
    published_at: isoToDateInput(job?.published_at ?? null),
    status: job?.status ?? 'OPEN',
  }
}

/** Validação de conveniência (a verdade continua no backend; 422 também é exibido por campo). */
export function validateJob(values: JobFormValues): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!values.title.trim()) errors.title = 'Title is required'
  if (!values.company.trim()) errors.company = 'Company is required'
  if (!values.description.trim()) errors.description = 'Description is required'

  const amount = (raw: string) => (raw.trim() === '' ? null : Number(raw))
  const low = amount(values.salary_min)
  const high = amount(values.salary_max)
  if (low !== null && (Number.isNaN(low) || low < 0)) errors.salary_min = 'Enter a valid amount'
  if (high !== null && (Number.isNaN(high) || high < 0)) errors.salary_max = 'Enter a valid amount'
  if (!errors.salary_min && !errors.salary_max && low !== null && high !== null && low > high) {
    errors.salary_max = 'Must be greater than or equal to the minimum'
  }
  const currency = values.currency.trim()
  if (currency && !/^[A-Za-z]{3}$/.test(currency)) errors.currency = 'Use a 3-letter code (e.g. BRL)'
  if ((low !== null || high !== null) && !currency) errors.currency = 'Required when a salary is set'
  return errors
}

/** Envia todos os campos: vazio vira null, o que limpa o valor no PATCH. */
export function toJobInput(values: JobFormValues): JobInput {
  return {
    title: values.title.trim(),
    company: values.company.trim(),
    description: values.description.trim(),
    location: blankToNull(values.location),
    source: blankToNull(values.source),
    source_url: blankToNull(values.source_url),
    work_model: values.work_model || null,
    employment_type: values.employment_type || null,
    seniority: values.seniority || null,
    salary_min: blankToNull(values.salary_min),
    salary_max: blankToNull(values.salary_max),
    currency: blankToNull(values.currency)?.toUpperCase() ?? null,
    published_at: dateInputToIso(values.published_at),
    status: values.status,
  }
}
