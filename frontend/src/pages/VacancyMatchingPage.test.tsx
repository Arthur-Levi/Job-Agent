import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { careerApi } from '../services/careerApi'
import { VacancyMatchingPage } from './VacancyMatchingPage'

vi.mock('../services/careerApi', () => ({ careerApi: { vacancyMatch: vi.fn() } }))

beforeEach(() => vi.resetAllMocks())

describe('VacancyMatchingPage', () => {
  it('requires explicit candidate review and cites only provided response evidence', async () => {
    vi.mocked(careerApi.vacancyMatch).mockResolvedValue({
      status: 'preliminary_candidate_review', vacancy_title: 'Analista de Dados',
      vacancy_source: 'candidate_supplied_unverified',
      summary: { total: 1, documented_match: 1, not_documented: 0, explicit_incompatibility: 0 },
      requirements: [{
        position: 1, category: 'skill', name: 'Excel', importance: 'required',
        classification: 'documented_match',
        evidence: [{ fact_id: 'fact-1', title: 'Excel', verification: 'USER_DECLARED' }],
        explanation: 'Correspondência textual exata', next_step: 'Conferir fato',
      }],
      limitations: ['Não prevê contratação'],
    })
    render(<MemoryRouter><VacancyMatchingPage /></MemoryRouter>)
    fireEvent.change(screen.getByLabelText('Título da vaga'), { target: { value: 'Analista de Dados' } })
    fireEvent.change(screen.getByPlaceholderText('Escreva exatamente como no fato'), {
      target: { value: 'Excel' },
    })
    const submit = screen.getByRole('button', { name: 'Comparar com meu Fact Ledger' })
    expect(submit).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(submit)
    await waitFor(() => expect(careerApi.vacancyMatch).toHaveBeenCalledWith(
      'Analista de Dados', [{ category: 'skill', name: 'Excel', importance: 'required' }],
    ))
    expect(await screen.findByText('Correspondência documentada')).toBeInTheDocument()
    expect(screen.getByText(/fact-1/)).toBeInTheDocument()
    expect(screen.getByText('Não prevê contratação')).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText('Escreva exatamente como no fato'), {
      target: { value: 'Python' },
    })
    expect(screen.queryByText('Correspondência documentada')).not.toBeInTheDocument()
    expect(submit).toBeDisabled()
  })

  it('shows absent information as undocumented instead of disqualifying user', async () => {
    vi.mocked(careerApi.vacancyMatch).mockResolvedValue({
      status: 'preliminary_candidate_review', vacancy_title: 'Exemplo',
      vacancy_source: 'candidate_supplied_unverified',
      summary: { total: 1, documented_match: 0, not_documented: 1, explicit_incompatibility: 0 },
      requirements: [{
        position: 1, category: 'skill', name: 'Python', importance: 'preferred',
        classification: 'not_documented', evidence: [],
        explanation: 'Não há evidência estruturada.', next_step: 'Revisar dados',
      }],
      limitations: ['Informação insuficiente'],
    })
    render(<MemoryRouter><VacancyMatchingPage /></MemoryRouter>)
    fireEvent.change(screen.getByLabelText('Título da vaga'), { target: { value: 'Exemplo' } })
    fireEvent.change(screen.getByPlaceholderText('Escreva exatamente como no fato'), {
      target: { value: 'Python' },
    })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Comparar com meu Fact Ledger' }))
    expect(await screen.findByText('Não documentado', { exact: true })).toBeInTheDocument()
    expect(screen.getByText('Informação insuficiente')).toBeInTheDocument()
  })
})
