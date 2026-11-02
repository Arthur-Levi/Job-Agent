import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { careerApi } from '../services/careerApi'
import type { ResumeExportPreview } from '../services/careerApi'
import { downloadApprovedResume } from '../services/resumeExportApi'
import { ApiError } from '../services/http'
import { ResumeReviewPage } from './ResumeReviewPage'

vi.mock('../services/careerApi', () => ({ careerApi: { exportPreview: vi.fn() } }))
vi.mock('../services/resumeExportApi', () => ({ downloadApprovedResume: vi.fn() }))

const preview: ResumeExportPreview = {
  status: 'draft_requires_candidate_review',
  basis: 'active_fact_ledger',
  candidate_name: 'Pessoa Sintética',
  approval_sha256: 'a'.repeat(64),
  approval_required: true,
  page_limit: 1,
  export_formats: ['pdf', 'docx'],
  sections: [
    { category: 'experience', entries: [{
      fact_id: 'fact-1', verification: 'USER_DECLARED', title: 'Analista de Dados',
      description: 'Painéis sintéticos', organization: 'Empresa Exemplo',
      start_date: '2023', end_date: '2024', requires_review: false,
    }] },
    { category: 'education', entries: [] },
    { category: 'project', entries: [] },
    { category: 'skill', entries: [] },
  ],
  omitted: [{ fact_id: 'fact-2', reason: 'unstructured_fact' }],
  limitations: ['Revisão obrigatória'],
}

function show() {
  return render(<MemoryRouter><ResumeReviewPage /></MemoryRouter>)
}

beforeEach(() => vi.resetAllMocks())

describe('ResumeReviewPage', () => {
  it('does not enable download until candidate approves a visible snapshot', async () => {
    vi.mocked(careerApi.exportPreview).mockResolvedValue(preview)
    show()
    expect(await screen.findByText('Pessoa Sintética')).toBeInTheDocument()
    expect(screen.getByText('Analista de Dados')).toBeInTheDocument()
    expect(screen.getByText(/Fato fact-2: unstructured_fact/)).toBeInTheDocument()
    const pdf = screen.getByRole('button', { name: 'Baixar PDF' })
    const docx = screen.getByRole('button', { name: 'Baixar DOCX' })
    expect(pdf).toBeDisabled()
    expect(docx).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox'))
    expect(pdf).toBeEnabled()
    expect(docx).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Recarregar fatos atuais' }))
    expect(pdf).toBeDisabled()
  })

  it('invalidates approval and reloads the preview if the ledger changed', async () => {
    vi.mocked(careerApi.exportPreview).mockResolvedValue(preview)
    vi.mocked(downloadApprovedResume).mockRejectedValue(new ApiError({
      status: 409, code: 'RESUME_APPROVAL_STALE', message: 'Mudou',
    }))
    show()
    await screen.findByText('Pessoa Sintética')
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Baixar PDF' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Seus fatos mudaram')
    expect(screen.getByRole('button', { name: 'Baixar PDF' })).toBeDisabled()
    await waitFor(() => expect(careerApi.exportPreview).toHaveBeenCalledTimes(2))
    expect(downloadApprovedResume).toHaveBeenCalledWith('pdf', 'a'.repeat(64))
  })

  it('does not permit export when no structured records exist', async () => {
    vi.mocked(careerApi.exportPreview).mockResolvedValue({
      ...preview, sections: preview.sections.map(section => ({ ...section, entries: [] })),
    })
    show()
    await screen.findByText('Pessoa Sintética')
    expect(screen.getByRole('checkbox')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Baixar DOCX' })).toBeDisabled()
  })
})
