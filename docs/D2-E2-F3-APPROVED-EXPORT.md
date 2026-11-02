# D2-E2.F.3 — Exportação PDF/DOCX com revisão humana verificável

**Status:** **PASS TÉCNICO CONDICIONAL** no commit `ae915cfb14d97bca4bb48c1391248f0e60cfe068`; produção e beta **NO-GO**.

**CI:** https://github.com/Arthur-Levi/Job-Agent/actions/runs/41497145868 — **316 passed, 3 xfailed, 1 warning** no backend, e os seis jobs (backend, frontend, browser-smoke, real-browser-postgres-e2e, sandbox-smoke, audit) concluíram com SUCCESS. O job audit é consultivo e não bloqueante. O Chromium valida a jornada anterior de React, API e PostgreSQL descartável, **não uma interface de exportação** (ainda pendente no F.4). A exportação foi verificada por novos testes de integração PDF/DOCX com dados sintéticos e PostgreSQL descartável.

## Contratos

`GET /api/v1/career/resume-export/preview` — autenticado. Consulta o mesmo `resume_draft` da etapa F.1 e devolve nome, seções, fatos com IDs, itens omitidos, `approval_sha256`, `approval_required=true`, formatos e limite de uma página.

`POST /api/v1/career/resume-export/{pdf|docx}` — autenticado. Corpo:
```json
{"approved": true, "approval_sha256": "<64-character SHA-256 from preview>"}
```
A exportação reconsulta o Fact Ledger ativo e recalcula o SHA-256 de **nome, seções, itens omitidos e versão do template**. A aprovação é rejeitada se não for afirmativa (422), se a versão mudou (409), se não há fatos estruturados (422) ou se o PDF de referência extrapola uma página (422). **Não** truncamos o currículo para fazê-lo caber.

## Princípios preservados

- Apenas fatos ativos da conta autenticada; nada de históricos substituídos, dados de outros candidatos ou conquistas inventadas.
- Informações ausentes permanecem ausentes; nenhuma habilidade, data, instituição ou resultado é inferido.
- Saída de uma coluna, sem tabelas, imagens ou gráficos. Nome do usuário vem do cadastro. Fatos são os do F.1. Rascunho omite registros não estruturados, apontados explicitamente no preview.
- PDF gerado por ReportLab e checado por pypdf (máximo 1 página); DOCX gerado por python-docx sem macros. É emitido apenas depois do mesmo preflight PDF. **A paginação do DOCX depende do renderizador e ainda demanda verificação visual em LibreOffice/Word**; portanto, o limite rigorosamente verificado até aqui se aplica ao PDF.
- Download com `Cache-Control: no-store, private`, arquivo com nome constante, sem gravar documento em disco e sem enviar conteúdo para serviços externos.
- Hash de aprovação não é uma assinatura de revisão persistida nem controle de sessão; a autenticação e o `approved=true` são obrigatórios. Auditoria durável da aprovação e UI de revisão completa pertencem ao F.4/Beta Acceptance.

## Testes e limites

Os testes usam PostgreSQL efêmero em CI, pois o fixture pode executar `DROP SCHEMA public CASCADE`: **nunca executar em banco preservado**, ainda que tenha sufixo `_test`. Casos: PDF legível com uma página, conteúdo DOCX inspecionável, dados de outro usuário/histórico excluídos, aprovação negada, digest obsoleto, perfil vazio, currículo extenso e escape de marcação.

**Pendências posteriores:** validação visual do DOCX/PDF em diferentes renderizadores e fontes; acessibilidade, metadados e tratamento de fontes Unicode; interface para revisar/aprovar/baixar (D2-E2.F.4); homologação ponta a ponta com Chromium (D2-E2.F.5). O `503 CV_SANDBOX_REQUIRED` para parsing de currículos reais em produção permanece intocado. Sem merge para main.
