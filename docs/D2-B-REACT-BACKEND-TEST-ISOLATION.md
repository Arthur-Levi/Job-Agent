# D2 — Backend React identificado e testes isolados (2026-10-31)

## Evidência do usuário
- Repositório contém `backend/app/main.py`, `production_api/main.py` e `mvp_fullstack/app.py`.
- `backend/tests` possui testes de API, unitários e integração próprios, incluindo migrations, perfis, vagas e candidaturas.
- `backend/alembic.ini` e `backend/migrations/env.py` foram encontrados.
- `npm ls` revela: `zod@4.6.5` via eslint-plugin-react-hooks; `undici@8.11.2` via jsdom; `minimatch@3.1.5` via eslint e `minimatch@10.2.6` via typescript-eslint. `npm audit --omit=dev` anteriormente reportou 0; audit geral reportou 14.
- Branch sincronizada em `4b35786` antes deste checkpoint.

## Auditoria de código confirmada
- `frontend/src/services/*` chama `/api/v1/profile`, `/api/v1/jobs` e `/api/v1/applications`, fornecidos por `backend/app/api/v1`.
- `production_api/main.py` usa contratos `/api/profile` etc. e contém a maioria das funções de importação/ledger/diagnóstico. Não executar contrato frontend live contra `production_api`.
- `backend/tests/integration/conftest.py` **DROPS SCHEMA public CASCADE** em `TEST_DATABASE_URL` cujo database termina em `_test` e depois aplica migrations e faz rollback por teste. Este critério nominal sozinho NÃO prova que banco é seguro; requer database dedicado, isolado, de propriedade do teste, previamente identificado. Nunca apontar para `jobagent_ux` (SEC05), nenhum banco original, nem simplesmente renomear DB de produção para terminar em `_test`.
- Recomenda-se rodar primeiro testes unitários e de API de `backend/` que usam FakeSession e URL dummy sem conexão, em ambiente Python com dependências instaladas; registrar resultados antes da integração real.
- Banco dedicado do backend React deve ser provisionado separadamente antes dos testes de integração, e confirmar que será irreversivelmente descartável. Não fazer operações destrutivas até haver evidência da identidade do alvo.

## Próximos passos
1. `cd /workspaces/Job-Agent-SEC05/backend`; com ambiente Python apropriado, `python -m pytest tests/unit tests/api -q --tb=short` (SEM `TEST_DATABASE_URL`).
2. Verificar build/teste do backend React em separado, sem confundir com os 72 testes `production_api`.
3. Projetar integração progressiva dos módulos carreira de `production_api` em `backend/app` com contrato React, testes de aceitação e nenhuma invenção de fatos.
4. Auditar remediation de `zod`, `undici`, `minimatch` via lockfile; não usar `npm audit fix --force` automaticamente.
5. Preparar PostgreSQL dedicado apenas para `backend/tests/integration` e live contract, com segurança explícita, mais adiante.

## Proteções
Preservar branch `main`, PR #2, worktree original, containers originais `jobagent-postgres-v2`, `jobagent-postgres-recovered`, e o novo `jobagent-sec05-db`/volume. Stripe Test Mode adiado.
