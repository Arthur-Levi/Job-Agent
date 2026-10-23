# Architecture decisions

## D1.1

1. **SQLAlchemy síncrono + psycopg 3.** Rotas `def` rodam no threadpool do FastAPI. Para um
   app single-user é mais simples e testável; migrar para async exigiria reescrever a camada de
   repositories (ver dívida técnica).
2. **App factory (`create_app`).** Permite injetar `Settings` nos testes e evita efeitos
   colaterais no import. Execução: `uvicorn app.main:create_app --factory`
   (desvio deliberado de `app.main:app`, que exigiria `DATABASE_URL` já no import).
3. **Commit é responsabilidade do service.** A sessão por request nunca faz commit
   automático: o commit ocorre antes da resposta e operações compostas
   (status + `ApplicationEvent`) são atômicas por construção. O `get_session` só faz rollback
   em erro e close.
4. **Envelope de erro** `{"error": {code, message, details, request_id}}`. `request_id` é
   acréscimo ao exemplo da spec, para correlacionar com logs. 422 só para validação de schema
   (e regras de negócio via `UnprocessableError`); JSON malformado → 400.
5. **Request ID**: aceita `X-Request-ID` do cliente só se casar `[A-Za-z0-9._-]{8,64}`;
   senão gera UUID hex. Vai para logs (contextvar) e para a resposta.
6. **Segredos**: `DATABASE_URL` é `SecretStr`, só é logada mascarada e os erros de validação
   não ecoam o valor.
7. **`/health` (liveness) não toca no banco; `/ready` faz `SELECT 1` e responde 503**
   com `DATABASE_UNAVAILABLE` se falhar.
8. **Testes sem Postgres** usam um `FakeSession` via `dependency_overrides`. O guard
   `safe_test_database_url()` aborta se o banco de testes não terminar em `_test`.

## D1.5

1. **Seed é código de aplicação testado**, em `app/devtools/seed.py`, e usa os services (regras, transações
   e eventos reais). Guard duro: só `APP_ENV=development`; a aplicação nunca o importa. Dados em `.invalid`.
2. **Makefile** só como atalho: nenhum passo existe apenas nele (tudo está no README). `.env` é carregado
   por `source` no alvo de testes, por isso valores com espaço ficam entre aspas.
3. **CI** roda os mesmos gates do `make check`, com `REQUIRE_TEST_DATABASE=1` (banco ausente = falha) e a
   cadeia de migrations upgrade → downgrade → upgrade pela CLI.
4. **Fechamento honesto:** `d1-acceptance.md` mapeia cada seção da spec à evidência e marca o que não foi
   verificado; `technical-debt.md` consolida riscos e decisões pendentes.

## Addenda
- **A01 — Multi-Channel Acquisition & Resume Intelligence** (**aprovado**, não implementado):
  [`architecture/addendum-A01-multichannel-acquisition.md`](architecture/addendum-A01-multichannel-acquisition.md).
  Distribui os requisitos entre D2–D8, registra a entidade conceitual `Opportunity` e lista os impactos sobre o D1.
