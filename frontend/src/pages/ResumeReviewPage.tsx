import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { useApiQuery } from '../hooks/useApiQuery'
import { careerApi } from '../services/careerApi'
import type { ResumeCategory } from '../services/careerApi'
import { downloadApprovedResume } from '../services/resumeExportApi'
import type { ExportFormat } from '../services/resumeExportApi'
import { ApiError } from '../services/http'

const HEADINGS: Record<ResumeCategory, string> = {
  experience: 'Experiências profissionais',
  education: 'Formação',
  project: 'Projetos',
  skill: 'Competências',
}

export function ResumeReviewPage() {
  const loader = useCallback((signal: AbortSignal) => careerApi.exportPreview(signal), [])
  const query = useApiQuery(loader)
  const [approvedDigest, setApprovedDigest] = useState<string | null>(null)
  const [busy, setBusy] = useState<ExportFormat | null>(null)
  const [notice, setNotice] = useState('')
  const [downloadError, setDownloadError] = useState('')

  const digest = query.state.status === 'success' ? query.state.data.approval_sha256 : null
  const approved = Boolean(digest && digest === approvedDigest && !query.refreshing)
  const entries = query.state.status === 'success'
    ? query.state.data.sections.reduce((sum, section) => sum + section.entries.length, 0)
    : 0

  // A successful preview refresh always invalidates the previous human approval,
  // even if a cached response is displayed during loading.
  const visibleDigest = query.state.status === 'success' && !query.refreshing ? digest : null
  useEffect(() => {
    setApprovedDigest(null)
    setNotice('')
  }, [visibleDigest])

  async function download(format: ExportFormat) {
    if (!approved || !digest || busy) return
    setBusy(format)
    setDownloadError('')
    setNotice('')
    try {
      const blob = await downloadApprovedResume(format, digest)
      const url = URL.createObjectURL(blob)
      try {
        const link = document.createElement('a')
        link.href = url
        link.download = `job-agent-resume.${format}`
        document.body.appendChild(link)
        link.click()
        link.remove()
      } finally {
        URL.revokeObjectURL(url)
      }
      setNotice(`Arquivo ${format.toUpperCase()} solicitado. Confira o conteúdo antes de enviar.`)
    } catch (error) {
      setApprovedDigest(null)
      if (error instanceof ApiError && error.code === 'RESUME_APPROVAL_STALE') {
        setDownloadError('Seus fatos mudaram. Confira novamente o currículo atualizado.')
        query.reload()
      } else {
        setDownloadError(error instanceof ApiError ? error.message : 'Não foi possível exportar.')
      }
    } finally {
      setBusy(null)
    }
  }

  return (
    <>
      <PageHeader title="Revisar e exportar currículo" subtitle="Cada linha deriva de um fato ativo do seu Fact Ledger." />
      <Card className="mb-5">
        <p className="text-sm text-slate-300">
          Leia os itens incluídos e omitidos. O Job Agent não completa lacunas com informações
          inventadas. Esta aprovação vale somente para a versão exibida.
        </p>
        <div className="mt-3 flex gap-4 text-sm">
          <Link className="text-sky-300 underline" to="/career">Abrir Fact Ledger</Link>
          <Link className="text-sky-300 underline" to="/career/diagnostic">Ver diagnóstico</Link>
        </div>
      </Card>
      {query.state.status === 'loading' && <p role="status">Carregando rascunho…</p>}
      {query.state.status === 'error' && (
        <Card>
          <p role="alert" className="text-rose-300">Não foi possível carregar a prévia do currículo.</p>
          <Button onClick={query.reload} className="mt-3">Tentar novamente</Button>
        </Card>
      )}
      {query.state.status === 'success' && (
        <div className="space-y-5">
          <Card>
            <h2 className="text-xl font-semibold">{query.state.data.candidate_name}</h2>
            <p className="mt-1 text-sm text-slate-300">{entries} item(ns) incluído(s). Modelo ATS em uma coluna.</p>
            <Button variant="secondary" className="mt-3" disabled={busy !== null || query.refreshing}
              onClick={() => { setApprovedDigest(null); setNotice(''); query.reload() }}>
              {query.refreshing ? 'Atualizando…' : 'Recarregar fatos atuais'}
            </Button>
          </Card>
          {query.state.data.sections.map(section => (
            <Card key={section.category}>
              <h2 className="text-lg font-semibold">{HEADINGS[section.category]}</h2>
              {section.entries.length === 0 ? <p className="mt-2 text-sm text-slate-400">Sem fatos estruturados nesta seção.</p> : (
                <ul className="mt-3 space-y-3">
                  {section.entries.map(entry => (
                    <li className="border-b border-slate-700 pb-3 last:border-0" key={entry.fact_id}>
                      <p className="font-semibold">{entry.title}</p>
                      <p className="text-sm text-slate-300">
                        {[entry.organization, [entry.start_date, entry.end_date].filter(Boolean).join(' – ')].filter(Boolean).join(' | ')}
                      </p>
                      {entry.description && <p className="mt-1 whitespace-pre-wrap text-sm">{entry.description}</p>}
                      {entry.requires_review && <p className="text-sm text-amber-300">Registro incompleto: revise no Fact Ledger antes de exportar.</p>}
                      <p className="mt-1 break-all text-xs text-slate-400">
                        Fonte: {entry.fact_id} · {entry.verification === 'USER_DECLARED' ? 'Declarado pelo candidato' : entry.verification}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          ))}
          <Card>
            <h2 className="font-semibold">Registros omitidos ({query.state.data.omitted.length})</h2>
            {query.state.data.omitted.length === 0 ? (
              <p className="mt-2 text-sm text-slate-300">Nenhum registro adicional foi omitido.</p>
            ) : (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                {query.state.data.omitted.map((item, index) => (
                  <li className="break-all" key={`${item.fact_id}-${index}`}>Fato {item.fact_id}: {item.reason}</li>
                ))}
              </ul>
            )}
          </Card>
          <Card>
            <h2 className="font-semibold">Aprovação do candidato</h2>
            <label className="mt-3 flex items-start gap-3 text-sm">
              <input type="checkbox" className="mt-1" checked={approved}
                disabled={query.refreshing || busy !== null || entries === 0}
                onChange={(event) => setApprovedDigest(event.target.checked ? digest : null)} />
              <span>Revisei os itens incluídos e omitidos e aprovo esta versão para exportação. Sei que os dados são declarações que devo conferir.</span>
            </label>
            <p className="mt-2 text-xs text-slate-400">A versão é conferida novamente no servidor antes do download.</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button disabled={!approved || busy !== null} onClick={() => { void download('pdf') }}>
                {busy === 'pdf' ? 'Gerando PDF…' : 'Baixar PDF'}
              </Button>
              <Button variant="secondary" disabled={!approved || busy !== null} onClick={() => { void download('docx') }}>
                {busy === 'docx' ? 'Gerando DOCX…' : 'Baixar DOCX'}
              </Button>
            </div>
            {downloadError && <p role="alert" className="mt-3 text-sm text-rose-300">{downloadError}</p>}
            {notice && <p role="status" className="mt-3 text-sm text-emerald-300">{notice}</p>}
            <p className="mt-3 text-xs text-slate-400">
              O PDF é validado para uma página; a paginação do DOCX pode variar conforme o editor.
            </p>
          </Card>
        </div>
      )}
    </>
  )
}
