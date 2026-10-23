# Runbook de desenvolvimento local

> Os comandos `docker compose`/`pg_dump` abaixo são padrão do ecossistema, mas **não foram executados no ambiente do
> assistente** (sem Docker). Teste-os uma vez na sua máquina antes de confiar neles.

## Rotina
| Objetivo | Comando |
|---|---|
| Subir tudo | `make up && make migrate && make backend-dev` (e `make frontend-dev` em outro terminal) |
| Dados de exemplo | `make seed` (só `APP_ENV=development`; idempotente) |
| Parar (mantém dados) | `make down` |
| Todos os gates | `make check` |
| Ver o estado da API | `curl localhost:8000/health` · `curl localhost:8000/ready` |

## Diagnóstico por `X-Request-ID`
Toda resposta (inclusive erro) traz `X-Request-ID`; a UI mostra "Request ID" nos erros. Os logs são JSON, um por linha:
`uvicorn … | jq 'select(.request_id=="<id>")'`. Cada request gera um log `request completed` (método, caminho, status, ms).

## Banco
- **Recomeçar do zero (apaga dados locais):** `make db-reset CONFIRM=yes && make migrate && make seed`.
- **Backup:** `docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql`
- **Restore (banco vazio, depois de `make db-reset`):** `docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB" < backup.sql`
- **Trocar a senha:** mudar `POSTGRES_PASSWORD` no `.env` **não** altera a senha de um volume já criado. Use
  `ALTER USER … PASSWORD …` dentro do container ou recrie o volume; atualize também as duas URLs.
- **Banco de teste:** `job_agent_test` só é criado na primeira inicialização do volume. Os testes **recriam o schema
  `public`** desse banco — nunca o aponte para dados que queira manter.
- Triggers: `application_events` é append-only; para limpar em dev use `TRUNCATE … CASCADE` (não aciona o trigger).

## Mudando o schema
1. Altere os models. 2. `alembic revision --autogenerate -m "…"` e **revise** o arquivo (CHECKs e triggers não são
detectados). 3. `alembic upgrade head`, `alembic downgrade -1`, `alembic upgrade head`. 4. `pytest` — o teste de *drift*
falha se model e migration divergirem. 5. Atualize `docs/database-schema.md`.

## Antes de começar uma nova fase (gate)
- `make check` verde e `REQUIRE_TEST_DATABASE=1` no CI.
- Dívida revisada (`docs/technical-debt.md`) e ADRs pendentes resolvidas (D3: ADR de `Opportunity`).
- Nada do Addendum A01 é implementado sem a fase correspondente e a autorização por fonte/operação.
