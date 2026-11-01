# D2-E2.D — Confirmação transacional + Master Profile / Fact Ledger + worker limitado

**Estado:** código implementado em `feature/d2-e2d-confirm-fact-ledger`, PR #8 Draft; aprovação CI documentada somente após run em HEAD.  
**Deriva de:** `feature/d2-e2c-ats-preview`.  
**NÃO altera:** `main`, PR #2–#7, banco do Codespaces `jobagent_react_test`, migração `0004` nesse banco, nem volumes PostgreSQL preservados. Sem migration nova: usa `0005` do PR #5 validada no CI descartável.

## Novo fluxo

1. Candidato autentica-se e envia PDF/DOCX/TXT (limites da D2-E2.C).
2. `POST /api/v1/resume-imports/preview`: o backend extrai em subprocesso, devolve prévia revisável e `preview_ticket` HMAC contendo identidade, origem e expiração 15 minutos. **Nenhuma prévia é gravada no PostgreSQL.** Token contém trechos pessoais em base64 assinado, **não criptografado**; não transmitir em URL, logs ou analytics.
3. React permite corrigir campos ou descartar cada item. A confirmação somente ocorre ao clicar em **Confirmar e salvar fatos no perfil**, após marcar declaração explícita.
4. `POST /api/v1/resume-imports/confirm` recebe `Idempotency-Key` (16–128 caracteres), token assinado, preview ID e todos os itens revisados. Garante dono, prazo, identidades e trechos de origem; recusa campos de origem manipulados, repetições de chave com conteúdo diferente e conflitos conservadores.
5. Transação única cria `ResumeImportRecord`, `CareerFact` ativos com `USER_DECLARED` e garante que existe `CandidateProfile`. Master Profile é **projeção dinâmica dos fatos ativos**, sem replicar experiências em tabelas `CandidateExperience` que ficariam desatualizadas após correção.
6. `GET /api/v1/career/profile` fornece visão resumida por origem, `GET /api/v1/career/facts?include_history=true` fornece fatos/histórico, `POST /api/v1/career/facts/{id}/corrections` substitui um fato ativo por outra versão com `supersedes_id`. Leitura/correção são filtradas pelo UUID do usuário. Correções são novamente `USER_DECLARED`.

## Garantias e limitações

- A mesma `Idempotency-Key` e payload devolvem o mesmo recibo. Uma chave com outro payload dá 409. Importação equivalente com outra chave não duplica fatos ativos com mesmo conteúdo literal. Mesmo cargo/empresa/período e conteúdo divergente dá 409 para revisão manual. **Não existe detector semântico completo de near-duplicates**.
- Um usuário não consegue confirmar a prévia assinada por outro nem corrigir seus fatos. Referências para imports e fatos usam FKs compostas por dono UUID.
- `source_excerpt` é preservado como referência assinada na prévia; cada fato confirmado armazena os campos revisados e `source_reference`. Não equivale a verificação independente. Não afirmar competência, vaga garantida ou score ATS universal.
- Correção altera `value` com `subject` original; editor de categoria/cargo e provenance FK detalhado nas tabelas filhas continuam pendentes. Motivo é exigido e registrado como digest em source_reference, não como texto pessoal aberto.
- As prévias não são persistidas; expiram em 15 minutos. Em desenvolvimento o segredo é aleatório por processo; reinício invalida tickets. Para futura topologia multiworker exigir `RESUME_PREVIEW_SIGNING_SECRET` compartilhada e rotacionável (mínimo 32 caracteres). A configuração de produção **recusa upload por padrão**, independentemente do segredo, até sandbox externo homologado.
- Nos testes/dev, parsing ocorre em **subprocesso** (`app.workers.resume_parser`) com tempo máximo de 10 segundos no pai, `RLIMIT_CPU=5` segundos, `RLIMIT_AS=768 MiB`, `RLIMIT_NOFILE=32`, `RLIMIT_FSIZE=0` em Linux; entrada 2 MB e resposta limitada. Ambiente sanitizado sem `DATABASE_URL`/tokens. **Não é sandbox de rede/arquivos**: subproc ainda pode alcançar interfaces de rede e arquivos legíveis no host. Portanto NÃO usar currículos reais até deploy de worker contêiner externo com egress negado, usuário não root, FS read-only, seccomp e quotas/concorrência.
- `POST /preview` **responde 503 `CV_SANDBOX_REQUIRED` com `APP_ENV=production`** até implementar o worker endurecido, impedindo liberação acidental.
- Permanece pendente criação de contêiner sandbox externo, no-store verificado no ingress, rate limit/concurrency especificamente do importador, métricas sem PII, privacidade/retention/exclusão e homologação operacional Codespaces em PostgreSQL **novo e descartável**. Proibido `pytest` destrutivo ou `alembic upgrade head` no `jobagent_react_test` antigo.

## Testes

- `backend/tests/integration/test_d2e2d_confirmation.py`: HMAC e expiração, cross-user, recibo, idempotência, duplicata, payload divergente, alteração de origem e correção/histórico.
- `backend/tests/integration/test_d2e2d_api_flow.py`: fluxo HTTP real via ASGI e PostgreSQL descartável `*_test` de CI: prévia → confirmação → retry → fatos → Master Profile.
- `backend/tests/unit/test_d2e2c_ats_preview.py`: parser, auth, 413 e bloqueio de produção `CV_SANDBOX_REQUIRED`.
- `frontend/src/pages/ResumeImportPage.test.tsx`: prévia, revisão, exclusão, confirmação e limite de upload.
- Os testes RED da D2-E2.A permanecem **3 xfail esperados**: contradições, diagnóstico e geração de currículo. Não são endpoints implementados.

## Próximos gates antes do beta

1. Sincronizar a branch Git em `/workspaces/Job-Agent-D2-E2` via `git fetch` e `git merge --ff-only` (depois de conferir `git status`). **Nenhuma migration/testes de banco no Codespaces protegido.**
2. Configurar um **novo banco descartável** de homologação D2-E2 e rodar migration `0005` sob verificação de alvo. Em staging real, criar estratégia segura de migração, backup e rollback.
3. Worker isolado com rede desabilitada, contêiner descartável, usuário não privilegiado, seccomp, FS read-only, credenciais ausentes e taxa/concorrência limitada. Substituir bloqueio de produção apenas após prova.
4. Testes reais de navegador, isolamento cross-user, restart, repetição concorrente, incidentes, retenção/exclusão, backups/restore e envio de email verificado.
5. Depois integrar D2-E2.E diagnóstico ATS keyword, D2-E2.F currículo e D2-E2.H aceite completo.

**Status de lançamento:** produção/beta com currículos reais **NÃO LIBERADOS**. Sem garantias universais de leitura/seleção por ATS.
