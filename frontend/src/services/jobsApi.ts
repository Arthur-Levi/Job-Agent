import type { Job, JobInput, JobStatus, ListParams, Page } from '../types/api'
import { request } from './http'

export interface JobListParams extends ListParams {
  status?: JobStatus
}

export const jobsApi = {
  list: (params: JobListParams = {}, signal?: AbortSignal) =>
    request<Page<Job>>('GET', '/api/v1/jobs', { query: { ...params }, signal }),
  get: (id: string, signal?: AbortSignal) => request<Job>('GET', `/api/v1/jobs/${id}`, { signal }),
  create: (input: Partial<JobInput>) => request<Job>('POST', '/api/v1/jobs', { body: input }),
  update: (id: string, input: Partial<JobInput>) =>
    request<Job>('PATCH', `/api/v1/jobs/${id}`, { body: input }),
  remove: (id: string) => request<void>('DELETE', `/api/v1/jobs/${id}`),
}
