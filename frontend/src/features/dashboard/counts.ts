import { applicationsApi } from '../../services/applicationsApi'
import { jobsApi } from '../../services/jobsApi'

export interface DashboardCounts {
  jobs: number
  applications: number
  ready: number
  interviews: number
}

/**
 * Só números REAIS do banco, via `total` de listas com limit=1 (sem endpoint de métricas no D1).
 * "Interviews" = candidaturas em INTERVIEW + TECHNICAL.
 */
export async function fetchDashboardCounts(signal: AbortSignal): Promise<DashboardCounts> {
  const [jobs, applications, ready, interview, technical] = await Promise.all([
    jobsApi.list({ limit: 1 }, signal),
    applicationsApi.list({ limit: 1 }, signal),
    applicationsApi.list({ limit: 1, status: 'READY' }, signal),
    applicationsApi.list({ limit: 1, status: 'INTERVIEW' }, signal),
    applicationsApi.list({ limit: 1, status: 'TECHNICAL' }, signal),
  ])
  return {
    jobs: jobs.total,
    applications: applications.total,
    ready: ready.total,
    interviews: interview.total + technical.total,
  }
}
