import type {
  Application,
  ApplicationDetail,
  ApplicationStatus,
  ApplicationStatusChange,
  ListParams,
  Page,
} from '../types/api'
import { request } from './http'

export interface ApplicationListParams extends ListParams {
  status?: ApplicationStatus
  job_id?: string
}

export const applicationsApi = {
  list: (params: ApplicationListParams = {}, signal?: AbortSignal) =>
    request<Page<Application>>('GET', '/api/v1/applications', { query: { ...params }, signal }),
  get: (id: string, signal?: AbortSignal) =>
    request<ApplicationDetail>('GET', `/api/v1/applications/${id}`, { signal }),
  create: (jobId: string) =>
    request<ApplicationDetail>('POST', '/api/v1/applications', { body: { job_id: jobId } }),
  changeStatus: (id: string, change: ApplicationStatusChange) =>
    request<ApplicationDetail>('PATCH', `/api/v1/applications/${id}`, { body: change }),
}
