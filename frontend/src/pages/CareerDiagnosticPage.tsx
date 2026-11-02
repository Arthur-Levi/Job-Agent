import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { useApiQuery } from '../hooks/useApiQuery'
import { careerApi } from '../services/careerApi'
import type { DiagnosticAction } from '../services/careerApi'

const FIELDS: Record<string, string> = {
  organization: 'empresa ou instituição',
  start_date: 'início do período',
  end_date: 'fim do período',
}

function ActionCard({ action }: { action: DiagnosticAction }) {
  const hasEvidence = action.evidence_fact_ids.length > 0
  return (
    <li className="rounded-lg border border-slate-700 bg-slate-950/50 p-4">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
        {action.priority === 'high' ? 'Revisão de registro existente' : 'Conferência de registros'}
      </p>
      <p className="font-medium text-slate-100">{action.message}</p>
      {action.fields && action.fields.length > 0 && (
        <p className="mt-1 text-sm text-amber-300">
          Campos não preenchidos: {action.fields.map(field => FIELDS[field] ?? field).join(', ')}.
        </p>
      )}
      <p className="mt-2 text-sm text-slate-300">{action.next_step}</p>
      {hasEvidence && (
        <p className="mt-2 break-all text-xs text-slate-400">
          Evidência: {action.evidence_fact_ids.map(id => <code key={id} className="mr-2">{id}</code>)}
        </p>
      )}
      <Link
        className="mt-3 inline-block text-sm font-medium text-sky-300 underline underline-offset-2"
        to={hasEvidence ? '/career' : '/resume-import'}
      >
        {hasEvidence ? 'Consultar fato no Fact Ledger' : 'Revisar importação de currículo'}
      </Link>
    </li>
  )
}

export function CareerDiagnosticPage() {
  const fetcher = useCallback((signal: AbortSignal) => careerApi.diagnostic(signal), [])
  const result = useApiQuery(fetcher)

  return (
    <>
      <PageHeader
        title="Diagnóstico de carreira"
        subtitle="Leitura preliminar e rastreável dos seus fatos profissionais confirmados."
      />
      <Card className="mb-4">
        <p className="text-sm text-slate-300">
          Este diagnóstico avalia somente registros ativos do seu Fact Ledger. Um campo não
          documentado não significa ausência de experiência ou competência.
        </p>
        <div className="mt-3 flex flex-wrap gap-3">
          <Link to="/career" className="text-sm font-medium text-sky-300 underline">Abrir Fact Ledger</Link>
          <Link to="/resume-import" className="text-sm font-medium text-sky-300 underline">Importar currículo</Link>
        </div>
      </Card>

      {result.state.status === 'loading' && <p role="status">Carregando diagnóstico…</p>}
      {result.state.status === 'error' && (
        <Card>
          <p role="alert" className="text-rose-300">Não foi possível consultar o diagnóstico.</p>
          <Button className="mt-3" onClick={result.reload} variant="secondary">Tentar novamente</Button>
        </Card>
      )}
      {result.state.status === 'success' && (
        <div className="space-y-5">
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase text-slate-400">Cobertura documental</p>
                <p className="text-2xl font-semibold text-slate-100">
                  {result.state.data.total_active_facts} fatos ativos
                </p>
                <p className="text-xs text-slate-400">Não é nota de empregabilidade.</p>
              </div>
              <Button onClick={result.reload} disabled={result.refreshing} variant="secondary">
                {result.refreshing ? 'Atualizando…' : 'Atualizar diagnóstico'}
              </Button>
            </div>
          </Card>

          <section aria-labelledby="diagnostic-coverage" className="space-y-3">
            <h2 id="diagnostic-coverage" className="text-lg font-semibold">Informações documentadas</h2>
            <div className="grid gap-3 lg:grid-cols-2">
              {result.state.data.coverage.map(category => (
                <Card key={category.category}>
                  <h3 className="font-semibold text-slate-100">{category.title}</h3>
                  <p className="mt-1 text-sm text-slate-300">
                    {category.state === 'documented'
                      ? `${category.count} registro(s) documentado(s)`
                      : 'Sem registros documentados nesta categoria'}
                  </p>
                  {category.evidence.length > 0 && (
                    <ul className="mt-3 space-y-2">
                      {category.evidence.map(item => (
                        <li key={item.fact_id} className="rounded border border-slate-700 p-2">
                          <p className="font-medium text-slate-100">{item.title}</p>
                          <p className="text-xs text-slate-400">
                            {item.verification === 'USER_DECLARED'
                              ? 'Declaração do candidato (sem verificação externa)'
                              : 'Verificação registrada no Fact Ledger'}
                          </p>
                          <p className="break-all text-xs text-slate-500">Fato: {item.fact_id}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>
              ))}
            </div>
          </section>

          <section aria-labelledby="diagnostic-actions" className="space-y-3">
            <h2 id="diagnostic-actions" className="text-lg font-semibold">Próximas correções recomendadas</h2>
            {result.state.data.review_actions.length === 0
              ? <p className="text-sm text-slate-300">Nenhuma revisão documental sugerida para os fatos atuais.</p>
              : (
                <ol className="space-y-3">
                  {result.state.data.review_actions.map((action, index) => (
                    <ActionCard key={`${action.kind}-${action.fact_id ?? action.category ?? index}`} action={action} />
                  ))}
                </ol>
              )}
          </section>

          <Card>
            <h2 className="font-semibold">Limitações desta análise</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">
              {result.state.data.limitations.map(text => <li key={text}>{text}</li>)}
            </ul>
          </Card>
        </div>
      )}
    </>
  )
}
