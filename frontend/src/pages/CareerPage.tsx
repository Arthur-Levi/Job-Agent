import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { useApiQuery } from '../hooks/useApiQuery'
import { careerApi } from '../services/careerApi'
import type { CareerFact } from '../services/careerApi'

export function CareerPage() {
  const [showHistory, setShowHistory] = useState(false)
  const [editing, setEditing] = useState<string | null>(null)
  const [value, setValue] = useState('')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const fetcher = useCallback(
    (signal: AbortSignal) => careerApi.facts(showHistory, signal),
    [showHistory],
  )
  const facts = useApiQuery(fetcher)

  function start(fact: CareerFact) {
    setEditing(fact.id)
    let description = fact.value
    try {
      const structured: unknown = JSON.parse(fact.value)
      if (structured && typeof structured === 'object' && 'description' in structured) {
        const field = structured.description
        if (typeof field === 'string') description = field
      }
    } catch {
      // Legacy plain-text facts remain editable as plain text.
    }
    setValue(description)
    setReason('')
    setError('')
  }

  async function save() {
    if (!editing || value.trim() === '' || reason.trim().length < 3 || saving) return
    setSaving(true)
    setError('')
    try {
      await careerApi.correct(editing, value, reason)
      setEditing(null)
      facts.reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao corrigir fato')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader title="Master Profile e Fact Ledger" subtitle="Declarações confirmadas, origem e histórico de correções." />
      <p className="mb-4 text-sm"><Link className="text-sky-300 underline" to="/career/diagnostic">Consultar diagnóstico de carreira</Link></p>
      <Card>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input type="checkbox" checked={showHistory} onChange={(e) => setShowHistory(e.target.checked)} />
          Mostrar versões substituídas e rejeitadas
        </label>
        {facts.state.status === 'loading' && <p role="status">Carregando fatos…</p>}
        {facts.state.status === 'error' && <p role="alert">Não foi possível consultar fatos.</p>}
        {facts.state.status === 'success' && facts.state.data && (
          <div className="mt-3 space-y-3">
            {facts.state.data.items.length === 0 && <p className="text-sm text-slate-400">Nenhum fato confirmado. Importe um currículo primeiro.</p>}
            {facts.state.data.items.map((fact) => (
              <section key={fact.id} className="rounded border border-slate-700 p-3">
                <div className="flex flex-wrap justify-between gap-2 text-sm">
                  <strong className="text-slate-100">{fact.subject}</strong>
                  <span className="text-slate-400">{fact.predicate} · {fact.status} · {fact.verification}</span>
                </div>
                {editing === fact.id ? (
                  <div className="mt-3 space-y-2">
                    <label className="block text-sm text-slate-200">Descrição corrigida
                      <textarea value={value} onChange={(e) => setValue(e.target.value)} rows={4} className="mt-1 w-full rounded bg-slate-950 p-2" />
                    </label>
                    <label className="block text-sm text-slate-200">Motivo da correção
                      <input value={reason} onChange={(e) => setReason(e.target.value)} className="mt-1 w-full rounded bg-slate-950 p-2" />
                    </label>
                    {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
                    <div className="flex gap-2">
                      <Button disabled={saving || reason.trim().length < 3} onClick={() => { void save() }}>{saving ? 'Salvando…' : 'Salvar nova versão'}</Button>
                      <Button variant="secondary" disabled={saving} onClick={() => setEditing(null)}>Cancelar</Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <pre className="mt-2 whitespace-pre-wrap break-words text-xs text-slate-300">{fact.value}</pre>
                    <p className="mt-2 break-all text-xs text-slate-400">Origem: {fact.source_reference}</p>
                    {fact.status === 'ACTIVE' && <Button variant="secondary" onClick={() => start(fact)}>Corrigir fato</Button>}
                  </>
                )}
              </section>
            ))}
          </div>
        )}
      </Card>
    </>
  )
}
