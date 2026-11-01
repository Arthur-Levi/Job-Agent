import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { resumeImportApi } from '../services/resumeImportApi'
import type { ResumePreview } from '../services/resumeImportApi'
import { ResumeImportPage } from './ResumeImportPage'

vi.mock('../services/resumeImportApi', () => ({
  resumeImportApi: { preview: vi.fn(), confirm: vi.fn() },
}))

const preview = vi.mocked(resumeImportApi.preview)
const confirm = vi.mocked(resumeImportApi.confirm)

const fixture: ResumePreview = {
  preview_id: 'synthetic-uuid',
  preview_ticket: 'synthetic-signed-ticket',
  format: 'txt',
  character_count: 142,
  sections_detected: ['experience'],
  fields_detected: { email: true, phone: false },
  items: [{
    draft_id: 'synthetic-draft',
    category: 'experience',
    title: 'Analista de Dados',
    organization: 'Empresa Exemplo',
    start_date: '2023',
    end_date: '2024',
    description: 'Dashboards sintéticos',
    source_excerpt: 'Empresa Exemplo | Analista de Dados | 2023-2024',
    review_status: 'pending',
    warnings: [],
  }],
  limitations: ['Revise antes de salvar.'],
  ats_check: {
    method: 'local_text_parser',
    text_extractable: true,
    sections_detected: ['experience'],
    unrecognized_fields: ['phone'],
    notice: 'Teste local; não garante aprovação em ATS de terceiros.',
  },
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('ResumeImportPage', () => {
  it('previews and lets the candidate edit and discard without persistence', async () => {
    preview.mockResolvedValue(fixture)
    confirm.mockResolvedValue({import_id:'import1', created_fact_ids:['fact1'], skipped_duplicates:[], verification:'USER_DECLARED'})
    render(<MemoryRouter><ResumeImportPage /></MemoryRouter>)
    const file = new File(['texto sintético para upload de currículo'], 'sample.txt', { type: 'text/plain' })
    fireEvent.change(screen.getByLabelText(/Arquivo PDF, DOCX ou TXT/), {
      target: { files: [file] },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Verificar leitura do currículo' }))
    expect(await screen.findByText(/Item 1 · experience/)).toBeInTheDocument()
    expect(preview).toHaveBeenCalledWith(file)
    fireEvent.change(screen.getByLabelText('Título / cargo'), {
      target: { value: 'Analista de BI' },
    })
    expect(screen.getByDisplayValue('Analista de BI')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Descartar item'))
    expect(screen.getByLabelText('Título / cargo')).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Descartar item'))
    fireEvent.click(screen.getByLabelText('Revisei as sugestões e entendo que são declarações não verificadas.'))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar e salvar fatos no perfil' }))
    expect(await screen.findByText(/Confirmação salva/)).toBeInTheDocument()
    expect(confirm).toHaveBeenCalledTimes(1)
    expect(preview).toHaveBeenCalledTimes(1)
  })

  it('blocks oversized upload before calling the API', async () => {
    render(<MemoryRouter><ResumeImportPage /></MemoryRouter>)
    const file = new File([new Uint8Array(2_000_001)], 'large.txt', { type: 'text/plain' })
    fireEvent.change(screen.getByLabelText(/Arquivo PDF, DOCX ou TXT/), {
      target: { files: [file] },
    })
    expect(screen.getByRole('alert')).toHaveTextContent('limite é 2 MB')
    expect(screen.getByRole('button', { name: 'Verificar leitura do currículo' })).toBeDisabled()
    await waitFor(() => expect(preview).not.toHaveBeenCalled())
  })
})
