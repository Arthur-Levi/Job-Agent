import { request } from './http'

export type DraftCategory = 'experience' | 'education' | 'project' | 'skill'
export interface ResumeDraftItem {
  draft_id: string
  category: DraftCategory
  title: string
  description: string
  organization: string | null
  start_date: string | null
  end_date: string | null
  source_excerpt: string
  review_status: 'pending' | 'edited' | 'rejected' | 'confirmed'
  warnings: string[]
}
export interface ResumePreview {
  preview_id: string
  format: 'txt' | 'pdf' | 'docx'
  character_count: number
  sections_detected: string[]
  fields_detected: Record<string, boolean>
  items: ResumeDraftItem[]
  limitations: string[]
  ats_check: {
    method: string
    text_extractable: boolean
    sections_detected: string[]
    unrecognized_fields: string[]
    notice: string
  }
}

export const resumeImportApi = {
  preview(file: File): Promise<ResumePreview> {
    const form = new FormData()
    form.append('file', file, file.name)
    return request<ResumePreview>('POST', '/api/v1/resume-imports/preview', {
      body: form,
      timeoutMs: 30_000,
    })
  },
}
