import { useState } from 'react'
import type { ChangeEvent } from 'react'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { ApiError } from '../services/http'
import { resumeImportApi } from '../services/resumeImportApi'
import type { ResumeDraftItem, ResumePreview } from '../services/resumeImportApi'

const MAX_BYTES = 2_000_000

export function ResumeImportPage() {
  const [preview, setPreview] = useState<ResumePreview | null>(null)
  const [items, setItems] = useState<ResumeDraftItem[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [acknowledged, setAcknowledged] = useState(false)

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null
    setFile(selected)
    setPreview(null)
    setItems([])
    setAcknowledged(false)
    setError(selected && selected.size > MAX_BYTES ? 'O limite é 2 MB por arquivo.' : '')
  }

  async function inspect() {
    if (!file || file.size > MAX_BYTES || working) return
    setWorking(true)
    setError('')
    setPreview(null)
    setItems([])
    setAcknowledged(false)
    try {
      const next = await resumeImportApi.preview(file)
      setPreview(next)
      setItems(next.items)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Não foi possível ler este arquivo.')
    } finally {
      setWorking(false)
    }
  }

  function change(id: string, field: keyof ResumeDraftItem, value: string) {
    setAcknowledged(false)
    setItems((old) => old.map((item) => item.draft_id === id
      ? { ...item, [field]: value, review_status: 'edited' } : item))
  }

  function mark(id: string, rejected: boolean) {
    setAcknowledged(false)
    setItems((old) => old.map((item) => item.draft_id === id
      ? { ...item, review_status: rejected ? 'rejected' : 'pending' } : item))
  }

  return (
    <>
      <PageHeader title="Importar currículo" subtitle="Prévia de leitura ATS e revisão humana — nenhuma informação é salva nesta etapa." />
      <Card className="mb-5">
        <div className="flex flex-col gap-3">
          <label htmlFor="resume-file" className="text-sm font-medium text-slate-200">Arquivo PDF, DOCX ou TXT (até 2 MB)</label>
          <input
            id="resume-file"
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={onFile}
            className="block w-full text-sm text-slate-200 file:mr-4 file:rounded file:border-0 file:bg-sky-500 file:px-3 file:py-2 file:text-slate-950"
          />
          <p className="text-xs text-slate-400">Somente arquivos de sua titularidade ou que você tenha autorização para utilizar. PDFs digitalizados sem texto não são reconhecidos nesta versão.</p>
          <div><Button disabled={!file || file.size > MAX_BYTES || working} onClick={() => { void inspect() }}>{working ? 'Analisando…' : 'Verificar leitura do currículo'}</Button></div>
          {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
        </div>
      </Card>

      {preview && (
        <div className="space-y-4">
          <Card>
            <h2 className="mb-2 font-semibold text-slate-100">ATS Parser Check — prévia, não certificação</h2>
            <p className="text-sm text-slate-300">Texto extraível: {preview.ats_check.text_extractable ? 'sim' : 'não'} · Formato: {preview.format.toUpperCase()} · Caracteres: {preview.character_count}</p>
            <p className="mt-2 text-sm text-slate-300">Seções identificadas: {preview.sections_detected.join(', ') || 'nenhuma'}</p>
            <p className="mt-1 text-sm text-slate-300">Contatos reconhecidos: email {preview.fields_detected.email ? 'sim' : 'não'}; telefone {preview.fields_detected.phone ? 'sim' : 'não'}.</p>
            <p className="mt-2 text-xs text-amber-200">{preview.ats_check.notice}</p>
            <ul className="mt-2 list-inside list-disc text-sm text-slate-400">
              {preview.limitations.map((line) => <li key={line}>{line}</li>)}
            </ul>
          </Card>
          <h2 className="text-lg font-semibold text-slate-100">Itens sugeridos para revisão ({items.length})</h2>
          {items.length === 0 && <p role="status" className="text-sm text-amber-200">Não foram identificados itens estruturados. Revise os cabeçalhos do documento ou informe os dados manualmente na próxima etapa.</p>}
          {items.map((item, index) => (
            <Card key={item.draft_id}>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-medium text-slate-100">Item {index + 1} · {item.category}</h3>
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input type="checkbox" checked={item.review_status === 'rejected'} onChange={(e) => mark(item.draft_id, e.target.checked)} />
                  Descartar item
                </label>
              </div>
              {item.warnings.map((warning) => <p key={warning} className="mb-1 text-xs text-amber-200">{warning}</p>)}
              <div className="grid gap-3 md:grid-cols-2">
                <label className="text-sm text-slate-300">Título / cargo
                  <input disabled={item.review_status === 'rejected'} value={item.title} onChange={(e) => change(item.draft_id, 'title', e.target.value)} className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2" />
                </label>
                <label className="text-sm text-slate-300">Empresa / instituição (não inferida)
                  <input disabled={item.review_status === 'rejected'} value={item.organization ?? ''} onChange={(e) => change(item.draft_id, 'organization', e.target.value)} className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2" />
                </label>
                <label className="text-sm text-slate-300">Início (informar manualmente)
                  <input disabled={item.review_status === 'rejected'} placeholder="AAAA-MM" value={item.start_date ?? ''} onChange={(e) => change(item.draft_id, 'start_date', e.target.value)} className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2" />
                </label>
                <label className="text-sm text-slate-300">Fim (informar manualmente)
                  <input disabled={item.review_status === 'rejected'} placeholder="AAAA-MM ou atual" value={item.end_date ?? ''} onChange={(e) => change(item.draft_id, 'end_date', e.target.value)} className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2" />
                </label>
              </div>
              <label className="mt-3 block text-sm text-slate-300">Descrição
                <textarea disabled={item.review_status === 'rejected'} value={item.description} onChange={(e) => change(item.draft_id, 'description', e.target.value)} rows={3} className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2" />
              </label>
              <details className="mt-2 text-xs text-slate-400"><summary className="cursor-pointer">Ver trecho original extraído</summary><pre className="mt-1 whitespace-pre-wrap">{item.source_excerpt}</pre></details>
            </Card>
          ))}
          <Card>
            <label className="flex items-start gap-2 text-sm text-slate-200">
              <input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} />
              Revisei as sugestões e entendo que são declarações não verificadas.
            </label>
            <p role="status" className="mt-2 text-sm text-amber-200">
              {acknowledged
                ? 'Revisão local concluída. A gravação e confirmação segura no Fact Ledger serão implementadas na D2-E2.D. Nada foi salvo.'
                : 'Edite ou descarte os itens. Esta prévia fica apenas na memória do navegador; ao sair, as alterações serão perdidas.'}
            </p>
          </Card>
        </div>
      )}
    </>
  )
}
