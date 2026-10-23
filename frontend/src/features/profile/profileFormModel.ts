import type { Profile, ProfileInput, Seniority, WorkModel } from '../../types/api'
import { blankToNull } from '../../utils/format'

export interface ProfileFormValues {
  headline: string
  summary: string
  city: string
  state: string
  country: string
  desired_work_model: WorkModel | ''
  desired_seniority: Seniority | ''
}

export function toProfileValues(profile: Profile | null): ProfileFormValues {
  return {
    headline: profile?.headline ?? '',
    summary: profile?.summary ?? '',
    city: profile?.city ?? '',
    state: profile?.state ?? '',
    country: profile?.country ?? '',
    desired_work_model: profile?.desired_work_model ?? '',
    desired_seniority: profile?.desired_seniority ?? '',
  }
}

/** Envia TODOS os campos: em PATCH, `null` limpa o que o usuário apagou. */
export function toProfileInput(values: ProfileFormValues): ProfileInput {
  return {
    headline: blankToNull(values.headline),
    summary: blankToNull(values.summary),
    city: blankToNull(values.city),
    state: blankToNull(values.state),
    country: blankToNull(values.country),
    desired_work_model: values.desired_work_model || null,
    desired_seniority: values.desired_seniority || null,
  }
}
