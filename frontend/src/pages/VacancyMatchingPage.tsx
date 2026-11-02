import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { careerApi } from '../services/careerApi'
import type { VacancyMatch, VacancyRequirement } from '../services/careerApi'
import { ApiError } from '../services/http'

const CATEGORIES = [
  ['skill', 'Competência'],
  ['experience', 'Experiência'],
  ['education', 'Formação'],
  ['project', 'Projeto'],
  ['work_mode', 'Modalidade'],
] as const

const LABELS: Record<VacancyMatch['requirements'][number]['classification'], string> = {
  documented_match: 'Correspondência documentada',
  not_documented: 'Não documentado',
  explicit_incompatibility: 'Incompatibilidade explícita — requer conferência',
}

const initial: VacancyRequirement = { category: 'skill', name: '', importance: 'required' }

export function VacancyMatchingPage() {
  const [title, setTitle] = useState('')
  const [requirements, setRequirements] = useState<VacancyRequirement[]>([{ ...initial }])
  const [result, setResult] = useState<VacancyMatch | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [reviewed, setReviewed] = useState(false)

  function resetResult() {
    setResult(null)
    setReviewed(false)
    setError('')
  }

  function update(index: number, patch: Partial<VacancyRequirement>) {
    setRequirements(current => current.map((entry, i) => i === index ? { ...entry, ...patch } : entry))
    resetResult()
  }

  async function compare() {
    if (busy || !reviewed || title.trim().length < 2 ||
        requirements.length === 0 || requirements.some(item => item.name.trim().length < 2)) return
    setBusy(true)
    setError('')
    setResult(null)
    try {
      setResult(await careerApi.vacancyMatch(title.trim(), requirements.map(item => ({
        ...item, name: item.name.trim(),
      }))))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível comparar a vaga.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Matching explicável" subtitle="Compare requisitos que você informar com fatos ativos do Fact Ledger." />
      <Card className="mb-5">
        <p className="text-sm text-slate-300">
          Os requisitos são fornecidos por você e não foram conferidos com o empregador.
          Correspondências são textuais e não indicam probabilidade de contratação ou aprovação em ATS.
        </p>
        <div className="mt-3 flex flex-wrap gap-4 text-sm">
          <Link className="text-sky-300 underline" to="/career">Consultar Fact Ledger</Link>
          <Link className="text-sky-300 underline" to="/career/resume-review">Revisar currículo</Link>
        </div>
      </Card>
      <Card>
        <form onSubmit={event => { event.preventDefault(); void compare() }} className="space-y-4">
          <label className="block text-sm font-medium" htmlFor="vacancy-title">Título da vaga</label>
          <input id="vacancy-title" className="w-full rounded border border-slate-600 bg-slate-950 px-3 py-2"
            maxLength={160} value={title} onChange={event => { setTitle(event.target.value); resetResult() }}
            placeholder="Ex.: Analista de Dados" required minLength={2} />
          <h2 className="font-semibold">Requisitos informados</h2>
          {requirements.map((item, index) => (
            <fieldset key={index} className="grid gap-2 rounded border border-slate-700 p-3 md:grid-cols-3">
              <legend className="px-1 text-sm">Requisito {index + 1}</legend>
              <label className="text-sm">Categoria
                <select className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2"
                  value={item.category} onChange={event => update(index, {
                    category: event.target.value as VacancyRequirement['category'], name: '',
                  })}>
                  {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
              <label className="text-sm">Requisito
                {item.category === 'work_mode' ? (
                  <select className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2"
                    value={item.name} onChange={event => update(index, { name: event.target.value })} required>
                    <option value="">Selecione a modalidade</option>
                    <option value="remote_only">Exclusivamente remoto</option>
                    <option value="onsite_only">Exclusivamente presencial</option>
                  </select>
                ) : (
                  <input className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2"
                    value={item.name} onChange={event => update(index, { name: event.target.value })}
                    minLength={2} maxLength={120} required placeholder="Escreva exatamente como no fato" />
                )}
              </label>
              <label className="text-sm">Importância
                <select className="mt-1 block w-full rounded border border-slate-600 bg-slate-950 p-2"
                  value={item.importance} onChange={event => update(index, {
                    importance: event.target.value as VacancyRequirement['importance'],
                  })}>
                  <option value="required">Obrigatório</option>
                  <option value="preferred">Desejável</option>
                </select>
              </label>
              {requirements.length > 1 && (
                <Button variant="ghost" onClick={() => {
                  setRequirements(old => old.filter((_, i) => i !== index))
                  resetResult()
                }}>Remover requisito {index + 1}</Button>
              )}
            </fieldset>
          ))}
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" disabled={requirements.length >= 20 || busy} onClick={() => {
              setRequirements(old => [...old, { ...initial }])
              resetResult()
            }}>Adicionar requisito</Button>
          </div>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-1" checked={reviewed}
              onChange={event => setReviewed(event.target.checked)} />
            <span>Conferi os requisitos digitados e compreendo que a análise é documental e preliminar.</span>
          </label>
          <Button type="submit" disabled={busy || !reviewed}>
            {busy ? 'Comparando…' : 'Comparar com meu Fact Ledger'}
          </Button>
          {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
        </form>
      </Card>
      {result && (
        <section className="mt-5 space-y-4" aria-label="Resultado do matching">
          <Card>
            <h2 className="text-lg font-semibold">Análise: {result.vacancy_title}</h2>
            <p className="mt-2 text-sm">
              {result.summary.documented_match} documentado(s) · {result.summary.not_documented} não documentado(s) ·{' '}
              {result.summary.explicit_incompatibility} incompatibilidade(s) explícita(s)
            </p>
            <p className="mt-2 text-xs text-slate-400">Não é pontuação nem decisão de recrutamento.</p>
          </Card>
          {result.requirements.map(row => (
            <Card key={row.position}>
              <h3 className="font-semibold">{row.position}. {row.name}</h3>
              <p className="text-sm text-sky-300">{LABELS[row.classification]}</p>
              <p className="mt-2 text-sm">{row.explanation}</p>
              <p className="mt-2 text-sm text-slate-300">Próximo passo: {row.next_step}</p>
              {row.evidence.length > 0 && <ul className="mt-2 space-y-1 text-xs text-slate-400">
                {row.evidence.map(evidence => (
                  <li className="break-all" key={evidence.fact_id}>
                    Evidência: {evidence.title} · {evidence.fact_id} · {evidence.verification}
                  </li>
                ))}
              </ul>}
            </Card>
          ))}
          <Card>
            <h2 className="font-semibold">Limitações</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">
              {result.limitations.map(limitation => <li key={limitation}>{limitation}</li>)}
            </ul>
          </Card>
        </section>
      )}
    </>
  )
}
