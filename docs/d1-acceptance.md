# D1 — Matriz de aceite (spec × evidência)

Legenda: ✅ atendido e verificado · ⚠️ atendido com ressalva · ➖ opcional, não feito.

| § | Requisito | Evidência | |
|---|---|---|---|
| 1 | Stack (React, TS, Vite, Tailwind, Router, cliente HTTP, ESLint; Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, pytest, logging estruturado) | `pyproject.toml`, `frontend/package.json` | ✅ |
| 2 | Estrutura do monorepo | árvore do repositório (acréscimos: `devtools/`, `.github/`, `Makefile`) | ✅ |
| 3 | API → Service → Repository → DB; sem regra/SQL nas rotas | `docs/api-and-domain.md`; rotas só convertem schemas | ✅ |
| 4 | UUID e timestamps timezone-aware | `tests/unit/test_models_metadata.py` | ✅ |
| 5 | Single-user com `user_id`; usuário padrão documentado | `UserService`, `get_current_user`, `docs/api-and-domain.md` | ✅ |
| 6–17 | Entidades D1 (User … ApplicationEvent) | `app/models/`, migration `0001` | ✅ |
| 14, 15 | JobMatch / ResumeVersion: só persistência | sem repository/API (por spec) | ✅ |
| 18 | FKs, índices, unique, NOT NULL, cascades deliberados | `test_models_metadata.py`, `test_schema_constraints.py`, `docs/database-schema.md` | ✅ |
| 19 | Alembic; upgrade em banco vazio; rollback; sem `create_all` | `test_migrations.py` (upgrade, downgrade, drift); `grep create_all` vazio | ✅ |
| 20 | Gerenciamento de sessão | `Database`, `get_session`, `transactional` | ✅ |
| 21 | Repositories (Profile, Job, Application) | `app/repositories/`; métodos apenas onde há uso | ⚠️ |
| 22 | Services | `app/services/` | ✅ |
| 23 | Versionamento `/api/v1` | `app/api/v1/` | ✅ |
| 24 | `/health` e `/ready` (503 sem banco) | `test_health.py`, `test_database_integration.py` | ✅ |
| 25–27 | Profile, Jobs (paginação ≤ 100) e Applications (status validado + evento) | `tests/integration/test_api_*.py` | ✅ |
| 28 | Schemas Create/Update/Read e validações | `tests/unit/test_schemas.py` | ✅ |
| 29 | Modelo de erro (400/404/409/422/500, +413/503) | `test_errors.py`, `docs/api-and-domain.md` | ✅ |
| 30 | Logging estruturado sem segredos | `test_logging.py`, `test_config.py` (URL mascarada) | ✅ |
| 31 | Request ID | `test_request_id.py`, `http.test.ts` | ✅ |
| 32 | Configuração central e `.env.example` | `app/core/config.py`, `.env.example` | ✅ |
| 33 | CORS explícito, sem `*` em produção | `test_config.py`, `test_cors_and_limits.py`, verificação de preflight | ✅ |
| 34–35 | Shell e rotas (+404) | `App.test.tsx` | ✅ |
| 36 | Dashboard só com dados reais | `DashboardPage.test.tsx` | ✅ |
| 37–39 | Páginas de Profile, Jobs, Applications | `src/pages/*.test.tsx` | ✅ |
| 34 | Visual limpo, responsivo, dark | implementado por classes Tailwind; **não verificado em navegador real** | ⚠️ |
| 40 | Cliente HTTP centralizado | `services/http.ts` (único `fetch`) | ✅ |
| 41 | Loading / erro / vazio / sucesso | `AsyncView` + testes de página | ✅ |
| 42 | Docker: PostgreSQL | `docker-compose.yml` (validado só como YAML; sem Docker no ambiente de desenvolvimento do assistente) | ⚠️ |
| 42 | Docker: backend containerizado ("preferencialmente") | não feito — ver `technical-debt.md` TD-04 | ➖ |
| 43 | Comandos de desenvolvimento documentados | `README.md`, `Makefile` | ✅ |
| 44 | Os 16 testes nomeados | verificados por `grep`: todos existem (e passam) | ✅ |
| 45 | Banco de teste isolado e reprodutível | `tests/integration/conftest.py`, guard `_test` | ✅ |
| 46 | `build`, `lint`, TypeScript sem erros | `npm run lint && npm run build` | ✅ |
| 47 | ruff + mypy | `ruff check`, `mypy --strict` | ✅ |
| 48 | Baseline de segurança | sem segredos no código; payload limitado (só `Content-Length`); sem autenticação | ⚠️ |
| 49 | Sem perfil duplicado; `UNIQUE(user_id)` | `test_create_profile_twice_is_409` | ✅ |
| 50 | Status + evento atômicos | `test_status_change_and_event_are_atomic` (+ teste de mutação) | ✅ |
| 51 | Máquina de status V0 centralizada e documentada | `domain/application_status.py`, `test_application_status.py` | ✅ |
| 52 | Auditabilidade (events, `analysis_version`, timestamps) | trigger append-only, `test_events_are_immutable…` | ✅ |
| 53–57 | Sem IA, scraping, automação de candidatura, billing, auth completa | `grep` por termos proibidos: vazio | ✅ |
| 58 | Seed de desenvolvimento | `app/devtools/seed.py`, `test_seed.py`, `test_seed_guard.py` | ✅ |
| 59 | README completo | `README.md` (todas as seções pedidas) | ✅ |
| — | Revisão de segurança (autorizada na D1.5) | `docs/security-review.md` | ✅ |
| — | Relatório de fechamento | `docs/D1-FINAL-STATUS.md` | ✅ |

**Não verificado por mim (precisa do seu ambiente; detalhes em `D1-FINAL-STATUS.md` §4):** `docker compose up` (sem Docker no ambiente do assistente),
execução do workflow no GitHub Actions (validado com `actionlint` e replicando os passos localmente),
visual/acessibilidade em navegador real.
