import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { careerApi } from '../services/careerApi'
import type { CareerDiagnostic } from '../services/careerApi'
import { CareerDiagnosticPage } from './CareerDiagnosticPage'

vi.mock('../services/careerApi', () => ({
  careerApi: { diagnostic: vi.fn() },
}))

const fixture: CareerDiagnostic = {
  status: 'preliminary',
  basis: 'active_fact_ledger',
  total_active_facts: 1,
  coverage: [
    {
      category: 'experience',
      title: 'Experiências profissionais',
      state: 'documented',
      count: 1,
      evidence: [{ fact_id: 'fact-1', title: 'Analista de Dados', verification: 'USER_DECLARED' }],
    },
    { category: 'education', title: 'Formação', state: 'not_documented', count: 0, evidence: [] },
    { category: 'project', title: 'Projetos', state: 'not_documented', count: 0, evidence: [] },
    { category: 'skill', title: 'Competências declaradas', state: 'not_documented', count: 0, evidence: [] },
  ],
  review_actions: [
    {
      kind: 'review_documented_fact',
      priority: 'high',
      fact_id: 'fact-1',
      evidence_fact_ids: ['fact-1'],
      fields: ['organization', 'start_date'],
      message: 'Revise informações não preenchidas nesta experiência.',
      next_step: 'Confira empresa e período em seus documentos originais.',
    },
    {
      kind: 'verify_missing_records',
      priority: 'normal',
      category: 'education',
      evidence_fact_ids: [],
      message: 'Não há registros desta categoria no Fact Ledger.',
      next_step: 'Confirme somente registros reais.',
    },
  ],
  limitations: ['Ausência de registro não comprova ausência de competência.'],
}

function renderPage() {
  return render(<MemoryRouter><CareerDiagnosticPage /></MemoryRouter>)
}

beforeEach(() => vi.resetAllMocks())

describe('CareerDiagnosticPage', () => {
  it('shows traceable evidence and specific actions without invented skills or scores', async () => {
    vi.mocked(careerApi.diagnostic).mockResolvedValue(fixture)
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Diagnóstico de carreira' })).toBeInTheDocument()
    expect(screen.getByText('Analista de Dados')).toBeInTheDocument()
    expect(screen.getAllByText(/fact-1/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Declaração do candidato/)).toBeInTheDocument()
    expect(screen.getByText(/Campos não preenchidos: empresa ou instituição, início do período/)).toBeInTheDocument()
    expect(screen.getAllByText(/Sem registros documentados nesta categoria/)).toHaveLength(3)
    expect(screen.getByRole('link', { name: 'Consultar fato no Fact Ledger' })).toHaveAttribute('href', '/career')
    expect(screen.getByRole('link', { name: 'Revisar importação de currículo' })).toHaveAttribute('href', '/resume-import')
    expect(screen.queryByText(/chance de contratação/i)).not.toBeInTheDocument()
  })

  it('renders an empty diagnostic as absence of records, not lack of competence', async () => {
    vi.mocked(careerApi.diagnostic).mockResolvedValue({
      ...fixture, total_active_facts: 0,
      coverage: fixture.coverage.map(section => ({
        ...section, state: 'not_documented', count: 0, evidence: [],
      })),
      review_actions: [],
    })
    renderPage()
    expect(await screen.findByText('0 fatos ativos')).toBeInTheDocument()
    expect(screen.getAllByText(/Sem registros documentados nesta categoria/)).toHaveLength(4)
    expect(screen.getByText(/não significa ausência de experiência ou competência/)).toBeInTheDocument()
  })

  it('offers retry on network failure and reloads the current facts', async () => {
    vi.mocked(careerApi.diagnostic)
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce(fixture)
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível consultar o diagnóstico')
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(careerApi.diagnostic).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('Analista de Dados')).toBeInTheDocument()
  })
})
