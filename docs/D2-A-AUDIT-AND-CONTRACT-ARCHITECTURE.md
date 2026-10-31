# D2 — Auditoria das dependências e identificação de contratos (2026-10-31)

Branch: `test/sec05-stripe-prebeta`
**Estado: diagnóstico de arquitetura, sem alterações de código nem instalações.**

## Resultado reportado: npm audit
- `npm audit --omit=dev`: **0 vulnerabilities** nas dependências classificadas como produção pelo npm.
- `npm audit`: **14 vulnerabilities (12 moderate, 2 high)** na árvore total.
- Pacotes destacados: `minimatch <11.0.1` (moderate); `undici 8.0.0–8.12.1` (high); `zod <4.6.6` (high). O report vincula minimatch à cadeia de eslint/typescript-eslint, e menciona correções `npm audit fix` para undici e zod, mas `--force` com mudança potencialmente breaking na cadeia de typescript-eslint. Não atualizar cegamente sem inspecionar lockfile e execução dos testes.
- **Cuidado de interpretação**: 0 no `--omit=dev` NÃO prova segurança absoluta do produto nem elimina risco no CI/build. Não se declarou correção dos 14 alertas.

## Descoberta crítica: frontend React não aponta ao mesmo backend financeiro
Repositório contém:
- `backend/app/main.py`: app factory `create_app`, rotas versionadas `/api/v1/profile`, `/api/v1/jobs`, `/api/v1/applications`; modelos de domínio com UUID, páginas, enumeração de status e erro padronizado. Coincide estruturalmente com `frontend/src/services/profileApi.ts`, `jobsApi.ts` e `frontend/src/services/contract.live.test.ts` (5 testes saltados).
- `production_api/main.py`: API diferente com rotas `/api/profile`, `/api/jobs`, `/api/applications`, auth com Bearer, importação de currículo, Master Profile, Fact Ledger, diagnóstico fundamentado, Stripe. **Não é o contrato esperado pelo frontend React**.
- `mvp_fullstack/app.py`: terceira implementação legada; não foi validada nesta auditoria.

## Implicação para D2
A regressão backend anterior **72 PASS** foi da árvore `production_api/tests`, não é uma prova de compatibilidade com o frontend React. A regressão frontend **68 PASS**, 5 SKIPPED, typecheck/lint/build PASS também não prova integração com backend real.

**Não rodar `contract.live.test.ts` contra `production_api`**. Esse teste grava dados e pressupõe o contrato `backend/app`. Para execução live, provisionar ambiente dedicado com banco e migrations do `backend/` (não reaproveitar `jobagent-sec05-db` com esquema production_api sem estudo de compatibilidade). Verificar identidade de banco antes de gravações.

## Decisão recomendada para a jornada de valor
1. Identificar qual backend será canônico para beta. Atualmente funcionalidades de carreira importantes vivem em `production_api`, enquanto React usa `backend/app`.
2. Proposta: preservar `backend/app` como contrato React e **planejar integração por módulos** de importação/Fact Ledger/diagnóstico, sem redirecionar a UI para a API incompatível. Alternativa de redesenhar frontend para production_api exige decisão explícita.
3. Auditar migrações e segurança do backend canônico; criar testes de contrato em banco isolado antes de mover funcionalidades.
4. Executar suíte `backend/tests` em ambiente efêmero próprio (não confundir com `production_api`).
5. Dependências: analisar `npm ls undici zod minimatch`, obter report e avaliar atualizações controladas; repetir 68 testes/typecheck/lint/build após alterações.
6. D2-B depende da resolução do contrato para testar cadastro/importação/perfil/diagnóstico pela **mesma interface**.

## Isolamento
Preservar `main`, PR #2, `/workspaces/Job-Agent`, containers originais e volume SEC05. Stripe conta ausente: FC06B–D permanecem adiadas.

## Próximas leituras somente-leitura para operador
```bash
cd /workspaces/Job-Agent-SEC05/frontend
npm ls minimatch undici zod --all
cd /workspaces/Job-Agent-SEC05
find backend -maxdepth 3 -type f -name '*migration*' -o -name 'alembic.ini'
```
