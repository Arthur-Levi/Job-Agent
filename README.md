# Job Agent

Sistema pessoal de inteligência e operação para busca de oportunidades profissionais.
**D1 — Foundation & Architecture: concluída** (fundação de engenharia; sem IA, scraping ou automação de candidatura).

| Fase | Escopo | Status |
|---|---|---|
| D1.1 | Infra e núcleo do backend (config, logging, erros, request ID, health/ready) | ✅ |
| D1.2 | Schema, migrations Alembic, banco de teste isolado | ✅ |
| D1.3 | Repositories, services, máquina de status, API de profile/jobs/applications | ✅ |
| D1.4 | Frontend (shell, páginas, cliente HTTP tipado) | ✅ |
| D1.5 | Seed, README final, CI, fechamento e dívida técnica | ✅ |

Próximas fases (D2–D8+, aprovadas como planejamento): [`docs/architecture/addendum-A01-multichannel-acquisition.md`](docs/architecture/addendum-A01-multichannel-acquisition.md).

## Architecture

```
React (Vite)
   ↓  HTTP /api/v1
FastAPI (routes)
   ↓
Services        ← regras de aplicação, transações (commit explícito)
   ↓
Repositories    ← persistência, sempre escopada por user_id
   ↓
PostgreSQL      ← constraints, índices, trigger append-only em application_events
```

- `backend/app/{api,core,domain,models,schemas,repositories,services,db,devtools}`
- `frontend/src/{app,pages,features,components,services,hooks,types,utils}`
- `domain/` é Python puro (enums, máquina de status, regras); services dependem de um protocolo `UnitOfWork`,
  não de SQLAlchemy.
- Single-user, mas toda entidade do usuário tem `user_id`. **Não há autenticação**: todas as requisições operam
  como o usuário local padrão (`DEFAULT_USER_EMAIL`). **Não exponha esta API publicamente.**

Segurança: [`docs/security-review.md`](docs/security-review.md) · Operação: [`docs/runbook.md`](docs/runbook.md) · Fechamento: [`docs/D1-FINAL-STATUS.md`](docs/D1-FINAL-STATUS.md)

Documentação: [`docs/architecture-decisions.md`](docs/architecture-decisions.md) ·
[`docs/database-schema.md`](docs/database-schema.md) · [`docs/api-and-domain.md`](docs/api-and-domain.md) ·
[`docs/frontend.md`](docs/frontend.md) · [`docs/d1-acceptance.md`](docs/d1-acceptance.md) ·
[`docs/technical-debt.md`](docs/technical-debt.md)

## Requirements

| Ferramenta | Versão |
|---|---|
| Python | 3.12+ |
| Node.js | 20.19+ (22 LTS recomendado) |
| Docker + Compose | para o PostgreSQL 16 local |
| make | opcional (atalhos; todos os comandos também estão abaixo) |

## Setup

```bash
git clone <repo> && cd job-agent
cp .env.example .env                 # defina POSTGRES_PASSWORD e use a MESMA senha nas duas URLs
make up                              # docker compose up -d  (PostgreSQL + banco job_agent_test)

make backend-install                 # venv em backend/.venv + dependências
make migrate                         # alembic upgrade head
make seed                            # (opcional) dados de desenvolvimento
make backend-dev                     # API em http://localhost:8000  (docs em /docs)

make frontend-install                # npm ci
make frontend-dev                    # app em http://localhost:5173
```

Sem `make`: veja os comandos nas seções abaixo. Verificação rápida: `curl localhost:8000/ready`.

## Environment Variables

Backend (arquivo `.env` na raiz do repositório):

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | sim | `postgresql+psycopg://user:pass@host:5432/db` (`postgresql://` é normalizado). Nunca é logada com senha. |
| `TEST_DATABASE_URL` | para testes de banco | O **nome do banco deve terminar em `_test`**, senão os testes abortam. |
| `REQUIRE_TEST_DATABASE` | não | `1` faz a ausência de `TEST_DATABASE_URL` **falhar** os testes (CI) em vez de pulá-los. |
| `APP_ENV` | não | `development` (padrão), `test`, `production`. Em `production`: docs da API desligadas e `CORS_ORIGINS=*` rejeitado. |
| `APP_NAME` | não | Título da API. |
| `LOG_LEVEL` | não | `INFO` (padrão). |
| `CORS_ORIGINS` | não | Lista separada por vírgulas (padrão `http://localhost:5173`). |
| `DEFAULT_USER_EMAIL` / `DEFAULT_USER_NAME` | não | Identidade do usuário local do D1. |
| `MAX_REQUEST_BYTES` | não | Limite de `Content-Length` (padrão 1 MiB). |
| `DB_CONNECT_TIMEOUT_SECONDS` | não | Padrão 5. |
| `POSTGRES_USER/PASSWORD/DB/PORT` | só docker compose | Credenciais do container (`POSTGRES_PASSWORD` é obrigatória). |

Frontend (`frontend/.env`, opcional): `VITE_API_URL` — URL base da API (padrão `http://localhost:8000`).

## Database

PostgreSQL 16 via `docker-compose.yml` (porta em `127.0.0.1`). O script de init cria também `job_agent_test`
— **só na primeira inicialização do volume**.

```bash
cd backend
alembic upgrade head              # schema completo em banco vazio (usa DATABASE_URL)
alembic downgrade base            # desfaz tudo (apenas dev; apaga dados)
alembic revision --autogenerate -m "descrição"   # após mudar models; REVISE o arquivo gerado
alembic upgrade head --sql        # imprime o SQL sem executar
make db-reset CONFIRM=yes         # DESTRÓI o volume local e recria (dev)
```

O schema nunca é criado por `create_all()`. Decisões (cascades, constraints, trigger append-only):
[`docs/database-schema.md`](docs/database-schema.md).

## Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:create_app --factory --reload      # http://localhost:8000
```

- Endpoints: `GET /health` (liveness) · `GET /ready` (verifica o banco; 503 se indisponível).
- API v1 (`/api/v1`): `profile` (GET/POST/PATCH), `jobs` (CRUD + paginação `limit` ≤ 100), `applications`
  (GET/POST/PATCH; mudança de status validada pela máquina de estados, grava `ApplicationEvent` na mesma transação).
- Erros: `{"error": {"code", "message", "details", "request_id"}}`; header `X-Request-ID` em toda resposta.
- Detalhes, códigos de erro e política de transições: [`docs/api-and-domain.md`](docs/api-and-domain.md).

## Frontend

```bash
cd frontend
cp .env.example .env     # opcional
npm ci
npm run dev              # http://localhost:5173
```

Rotas: `/dashboard`, `/profile`, `/jobs`, `/jobs/:jobId`, `/applications`, 404. Toda tela que lê a API trata
loading, erro, vazio e sucesso. O origin do frontend precisa estar em `CORS_ORIGINS`.
Arquitetura e decisões: [`docs/frontend.md`](docs/frontend.md).

## Tests

```bash
make check                       # todos os gates (lint, tipos, testes) — backend e frontend

# backend (a partir de backend/, com o venv ativo)
pytest                           # sem TEST_DATABASE_URL: testes de banco são pulados
REQUIRE_TEST_DATABASE=1 pytest   # CI: exige o banco de teste
ruff check . && ruff format --check . && mypy

# frontend
npm run lint && npm run build && npm test
```

**Banco de teste:** a URL precisa apontar para um banco `*_test`. No início da sessão o schema `public` desse banco
é **recriado** e as migrations rodam até `head`; cada teste roda em transação com rollback.
**Nunca aponte `TEST_DATABASE_URL` para um banco com dados que você queira manter.**

Teste de contrato contra um backend real (desligado por padrão; grava dados, use banco descartável):
`VITE_LIVE_CONTRACT=1 VITE_API_URL=http://127.0.0.1:8000 npm test -- contract`.

CI: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (PostgreSQL de serviço, migrations upgrade→downgrade→upgrade,
ruff, mypy, pytest, lint/build/test do frontend).

## Development Seed

```bash
make seed        # ou: cd backend && python -m app.devtools.seed
```

Cria, para o usuário padrão: 1 perfil, 2 vagas e 1 candidatura (em `QUALIFIED`, com seus 2 eventos).

- **Só roda com `APP_ENV=development`** (recusa `production` e `test`, com código de saída 2) e **nunca** é chamado
  pela aplicação.
- **Idempotente:** rodar de novo não duplica nada.
- **Obviamente fictício:** URLs em `.invalid` (TLD reservado), empresas "Example Corp"/"Sample Labs", textos `[DEV SEED]`.
- Usa os mesmos services da API (regras, transações e eventos reais); imprime o banco de destino com a senha mascarada.
- Para recomeçar do zero: `make db-reset CONFIRM=yes && make migrate && make seed`.

## Solução de problemas

| Sintoma | Causa provável |
|---|---|
| Tela mostra "Connection problem" | API fora do ar, `VITE_API_URL` errada ou origin fora de `CORS_ORIGINS`. |
| Banco `job_agent_test` não existe | O volume já existia antes do script de init: `make db-reset CONFIRM=yes` (apaga dados locais). |
| `DATABASE_URL` obrigatória ao iniciar | `.env` ausente ou fora da raiz do repositório. |
| Testes de banco "skipped" | `TEST_DATABASE_URL` não definida (use `make backend-test`, que carrega o `.env`). |
