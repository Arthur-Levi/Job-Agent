# Job Agent — checkpoint consolidado D2-E2 (2026-11-02)

**Estado do desenvolvimento:** **D2-E2.F.5 PASS TÉCNICO CONDICIONAL** exclusivamente com dados sintéticos. **PRODUÇÃO E BETA COM CURRÍCULOS REAIS: NO-GO**.

**Repositório:** `Arthur-Levi/Job-Agent`  
**Branch da homologação:** `audit/d2-e2f5-full-acceptance`  
**Ponto de referência técnico com CI SUCCESS:** `3deda77fa90e9efc496de07bfb4c9de1cdcd4da7`  
**GitHub Actions:** https://github.com/Arthur-Levi/Job-Agent/actions/runs/41504828361  
**PR principal de homologação:** https://github.com/Arthur-Levi/Job-Agent/pull/17 (Draft)  
**Checkpoint consolidado:** a branch `checkpoint/d2-e2-completo-2026-11-02` apontará para este documento quando criada.

Este documento organiza o estado verificável do trabalho. Não autoriza merge, migrations em instância persistente, upload de documentos de pessoas reais, implantação pública ou início da cobrança.

## 1. Linha do tempo técnica e PRs em cascata

| Fase | Entrega | PR / branch | Checkpoint |
| --- | --- | --- | --- |
| D2-E2.C | ATS parser conservador, preview e revisão humana | #7 `feature/d2-e2c-ats-preview` | `a11f59d` |
| D2-E2.D | Confirmação transacional, Master Profile, Fact Ledger | #8 `feature/d2-e2d-confirm-fact-ledger` | `e32c602` |
| D2-E2.D.1 | Broker/sandbox e controles de concorrência | #9 `audit/d2-e2d1-security-acceptance` | `c50e16d` |
| D2-E2.D.1-D | Importação, rollback e persistência ponta a ponta | #10 `audit/d2-e2d1-d-acceptance` | `5eacb5e` |
| D2-E2.E | Motor Career Diagnostic baseado em evidências | #11 `feature/d2-e2e-evidence-diagnostic` | `8670645` |
| D2-E2.E.2 | Interface React de diagnóstico e recomendações | #12 `feature/d2-e2e2-diagnostic-react` | `0316a63` |
| D2-E2.F.1 | Rascunho ATS só com fatos ativos e rastreáveis | #13 `feature/d2-e2f1-evidence-resume` | `422369b` |
| D2-E2.F.2 | Matching explicável de requisitos de vagas | #14 `feature/d2-e2f2-explainable-matching` | `eaa68b0` |
| D2-E2.F.3 | Exportação PDF/DOCX com SHA-256 e revisão explícita | #15 `feature/d2-e2f3-pdf-docx-export` | `97b32a6` |
| D2-E2.F.4 | Revisão e exportação React + matching React | #16 `feature/d2-e2f4-react-review-matching` | `b145947` |
| D2-E2.F.5 | Homologação integral, isolamentos e documentos | #17 `audit/d2-e2f5-full-acceptance` | `3deda77` |

Os PRs #7–#17 foram conferidos como **OPEN/DRAFT**, sem merge. As bases estão em cascata; **não mesclar diretamente todos em main sem planejamento e revisão dos diffs**.

## 2. Arquitetura funcional que passou em integração sintética

1. React autenticado registra candidato sintético e importa currículo de teste. A API faz parsing conservador e apresenta trechos para revisão humana.
2. O candidato confirma dados declarados. A persistência usa PostgreSQL descartável, confirmação idempotente, Master Profile e Fact Ledger com histórico e correção transacional.
3. O Career Diagnostic apresenta somente evidências ativas e recomendações; não inventa competências nem interpreta falta de informação como falta real de habilidade.
4. O matching recebe requisitos fornecidos pelo candidato e retorna correspondência textual fundamentada, ausência documental ou incompatibilidade explícita apenas na modalidade de trabalho inequívoca. Não há score ATS nem previsão de contratação.
5. O currículo é montado de fatos estruturados ativos pertencentes ao usuário autenticado; campos excessivamente longos não podem ser truncados silenciosamente.
6. O candidato revisa fatos incluídos e omitidos, aprova digest SHA-256 da versão e recebe PDF ou DOCX, com recusa de aprovação obsoleta.
7. O CI fez login de duas contas sintéticas, isolou fatos/diagnóstico/matching, recusou digest de outra conta e token revogado.

## 3. Evidência de aceitação final verificada

CI: `41504828361` em `3deda77fa90e9efc496de07bfb4c9de1cdcd4da7` — **6/6 jobs SUCCESS**:

- Backend: **320 passed, 3 xfailed, 1 warning**. Inclui concorrência de exportações de duas contas com sessões PostgreSQL separadas, correção persistida invalidando digest antigo, falha injetada no renderer sem alterar ledger, e regressões anteriores de idempotência, rollback, duplicatas e tickets expirados.
- Frontend: lint/build e testes React PASS.
- `browser-smoke`: PASS com dados sintéticos.
- `real-browser-postgres-e2e`: PASS, sem API simulada, PostgreSQL efêmero, importação, correção, novo login, diagnóstico, revisão, download, matching, isolamento de contas, revogação e navegação básica por teclado.
- Documentos: PDF gerado no Chromium **1 página**; DOCX real convertido com **LibreOffice** também **1 página**; arquivos reabertos e comparados contra conteúdo sintético esperado. PNGs temporários foram inspecionados visualmente; sem cortes/sobreposições evidentes. Persistem redundâncias de redação vindas dos dados do fixture.
- `sandbox-smoke`: SUCCESS em contêiner efêmero de CI; **não** significa homologação do broker operacional em produção.
- `audit`: SUCCESS, mas **advisory / continue-on-error**, não aprovação de segurança bloqueante.

Artefato de prévias sintéticas da execução foi produzido com retenção de 3 dias. Os arquivos gerados são apenas exemplos sintéticos, não currículos reais.

## 4. Segurança e banco: invariantes de retomada

- **NUNCA** executar a suíte de integração em `DATABASE_URL`/instância persistente. Os fixtures podem rodar `DROP SCHEMA public CASCADE`. Somente `TEST_DATABASE_URL` de PostgreSQL descartável comprovado e/ou o job GitHub Actions isolado.
- No E2E, `APP_ENV=test`, `E2E_DISPOSABLE_DATABASE=1`, `CI=true`, database `job_agent_e2e_test` no `127.0.0.1:5432`; o guard confere todos antes de migrations.
- O parser de currículos reais em produção permanece **503 CV_SANDBOX_REQUIRED**.
- Nenhum merge de PRs Draft em main; não abrir endpoints de upload real sem gate operacional.
- O teste de navegação por teclado não é certificação WCAG; LibreOffice CI não substitui validação do Word.

## 5. Pendências — ordem de bloqueio para primeiros 10 betas

**P0 — obrigatórias antes de tratar arquivos reais**

1. **Sandbox operacional:** serviço broker com identidade de sistema separada, Docker host/daemon protegido, permissões do Unix socket, quotas distribuídas, timeouts, cancelamento, filas, limites CPU/RAM/rede/FS, logs sem PII, supervisão e exercícios de falha. Validar TLS, proxy e firewall da implantação real.
2. **Privacidade e gestão de dados:** finalidade, avisos, retenção/exclusão, LGPD, política de acesso, tratamento de currículos e excerpts, exportação de dados e processo de incidentes.
3. **Recuperação:** backup externo criptografado, teste de restauração independente, medidas contra perda, RPO/RTO acordados, monitoramento e procedimento de rollback.
4. **Segurança bloqueante:** revisão de dependências e serviços, controle de segredos, revisão de autorização e testes de abuso/limites; CI de auditoria atualmente consultivo precisa de gate formal.

**P1 — qualidade e operação beta**

5. Refinar duplicações do PDF/DOCX mantendo fatos originais; verificar diferentes tamanhos, nomes, acentos e Microsoft Word.
6. Teste abrangente de acessibilidade (WCAG/teclado/leitores de tela/contraste), usabilidade e tratamento de erros no React.
7. Testes de indisponibilidade API/worker/banco, fila/carga, concorrência entre réplicas, observabilidade e alertas.
8. Homologar onboarding, suporte, termos, cancelamento, Stripe em modo apropriado, métricas de retenção e plano de atendimento.

**Regra de lançamento:** 10 usuários beta convidados, somente depois de todos os P0 com evidência de aprovação e autorização explícita. Meta comercial futura não comprova prontidão técnica.

## 6. Comandos seguros para retomada no Codespaces

```bash
cd /workspaces/Job-Agent-D2-E2F4
git status --short
git fetch origin
git worktree add --detach /workspaces/Job-Agent-D2-E2F5-CKPT \
  origin/checkpoint/d2-e2-completo-2026-11-02
cd /workspaces/Job-Agent-D2-E2F5-CKPT
git log -1 --oneline
git status --short
```

Se a pasta da worktree já existir, não recriá-la antes de conferir alterações locais. Não executar migrações nem testes de banco nesses comandos.

## 7. Missão seguinte

**Beta Acceptance — SEC/OPS Gate 1: sandbox operacional do parser**.

Primeiro verificar identidade separada do broker/parser, permissões do socket, quotas distribuídas e isolamento de produção, com cenários sintéticos adversariais e documentação de implantação. O `503 CV_SANDBOX_REQUIRED` só poderá ser revisto depois de gates de segurança, privacidade, recuperação e operação devidamente aprovados.

A branch de checkpoint preserva o código e as evidências; **não é deploy e não dá autorização de produção**.
