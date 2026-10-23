# Revisão de segurança — fechamento da D1

Escopo: baseline de uma ferramenta **single-user, local, sem autenticação** (spec §48). Não é um pentest nem
um modelo de ameaças para exposição pública. Data: 2026-10-08.

## 1. O que foi executado (e o resultado)

| # | Verificação | Como | Resultado |
|---|---|---|---|
| 1 | Análise estática de segurança do código da aplicação | `ruff check app --select S` (regras bandit) | Inicial: 4× `S101` (`assert` usado como *narrowing* em handlers de erro e no seed). **Corrigido** (verificações explícitas). Final: limpo. |
| 2 | Auditoria de dependências Python | `pip-audit --skip-editable` | Dependências de **runtime**: nenhuma advisory reportada (fastapi 0.142.2, starlette 1.7.0, uvicorn 0.54.0, pydantic 2.13.5, pydantic-settings 2.15.0, SQLAlchemy 2.0.54, alembic 1.20.0, psycopg 3.3.6). **`pytest` 8.4.2** (dev) com advisory PYSEC-2026-1845 (diretório temporário previsível, local) → **corrigido**: `pytest>=9.0.3,<10` (9.1.1 instalado; reauditoria sem o pytest). `pip` 24.0 do ambiente também aparece: não é dependência do projeto; mitigado com `pip install --upgrade pip` no `make backend-install`. |
| 3 | Auditoria de dependências npm | `npm audit` (prod e todas) | 0 vulnerabilidades. |
| 4 | Busca de segredos | `grep` por atribuições de senha/token/chave e por chaves privadas/prefixos de token | Nenhum achado. |
| 5 | Padrões perigosos | `grep` | Frontend: sem `dangerouslySetInnerHTML`/`eval`/`innerHTML`/`document.write`/`localStorage`. Backend: sem `exec`/`eval`/`subprocess`/`pickle`/`os.system`/`yaml.load`; único SQL cru é `SELECT 1` constante (readiness). |
| 6 | Eficácia do `.gitignore` | `git init` + `git add -A` numa cópia com `.env`, `node_modules/`, `dist/`, `.venv/` | `.env` não rastreado; `.env.example` rastreado; artefatos de build/caches não rastreados. |
| 7 | CORS real | `curl` do preflight que o navegador envia (PATCH + `X-Request-ID`), com origin permitido e não permitido | Permitido: `Access-Control-Allow-*` corretos e `X-Request-ID` exposto. Não permitido: 400 e sem `Access-Control-Allow-Origin`. |
| 8 | Defesa em profundidade no frontend | achado da revisão: `source_url` ia direto para `href` | **Corrigido**: só http(s) vira link (`utils/url.ts`), com `rel="noopener noreferrer"`; testes cobrem `javascript:`. |
| 9 | Docs da API fora de produção | achado da revisão: faltava teste | **Corrigido**: `tests/unit/test_app_factory.py` (`/docs` e `/openapi.json` retornam 404 em `production`). |

## 2. Controles existentes e a evidência (testes)

| Controle | Evidência |
|---|---|
| Sem segredos no código; `DATABASE_URL` é `SecretStr`, só logada mascarada; erros de validação não ecoam a URL | `test_config.py::test_safe_database_url_masks_password`, `::test_invalid_database_url_error_does_not_leak_the_url` |
| `CORS_ORIGINS=*` rejeitado em produção; CORS explícito; sem credenciais | `test_config.py`, `test_cors_and_limits.py` |
| Erros inesperados não vazam stack trace nem detalhes internos | `test_errors.py::test_unexpected_error_returns_500_without_leaking_details` |
| Validação de entrada (strings, URLs http/https, moeda, dinheiro, datas com timezone, enums, campos extras proibidos) | `test_schemas.py`, `test_api_jobs.py` (casos parametrizados) |
| Sem *mass assignment* (`user_id`, `id` não são aceitos no payload) | `StrictModel` (`extra="forbid"`) + `test_unknown_fields_are_rejected` |
| Isolamento por usuário (IDOR): recurso de outro usuário = 404; referência a vaga alheia = 422 | `test_job_of_another_user_is_404`, `test_create_application_rejects_unknown_or_foreign_job` |
| Queries parametrizadas (ORM) | revisão + `grep` (item 5) |
| Limite de payload (por `Content-Length`) e paginação ≤ 100 | `test_oversized_body_is_rejected_with_413`, `test_list_jobs_rejects_invalid_query` |
| Integridade/auditoria: histórico append-only no banco | `test_events_are_immutable_and_keep_strict_order` |
| Seed de dev nunca em produção/test | `test_seed_guard.py` |
| Banco só em loopback; senha do container obrigatória | `docker-compose.yml` (`127.0.0.1:…`, `POSTGRES_PASSWORD:?`) — não executado no ambiente do assistente |
| Testes de banco não tocam o banco de desenvolvimento | `test_support.py` (guard `*_test`) |
| CI com permissões mínimas | `permissions: contents: read` |

## 3. Riscos remanescentes (ver também `technical-debt.md`)

| Risco | Sev. | Observação |
|---|---|---|
| **Sem autenticação** (TD-01): qualquer cliente com acesso à porta opera como o usuário local, inclusive `force` em status | **Alta** | Mitigação atual: uso local; **não expor**. Bloqueante para qualquer deploy. |
| Sem rate limiting (TD-31) | Média | Acompanha TD-01. |
| Limite de payload só por `Content-Length` (TD-02) | Média | Corpos *chunked* passam. |
| Sem headers de segurança / CSP (TD-28) | Baixa | Hardening de pré-deploy. |
| Sem lockfile Python (TD-29); ações do CI por tag (TD-30) | Média/Baixa | Reprodutibilidade e cadeia de suprimentos. |
| Backend não containerizado; sem TLS/proxy (TD-04) | Média | Pré-deploy. |
| Senha de exemplo fraca no `.env.example` (TD-32) | Baixa | O compose exige definir, não exige força. |
| Auditoria de dependências informativa no CI (TD-33) | Baixa | Não bloqueia merge. |
| `docker compose` e GitHub Actions **não executados** por mim | — | Ver `D1-FINAL-STATUS.md`. |

## 4. Itens exigidos antes de qualquer exposição fora do localhost

1. Autenticação e autorização reais (TD-01), com restrição do `force`.
2. Rate limiting e limite de corpo robusto (TD-31, TD-02).
3. Backend containerizado atrás de proxy com TLS e headers de segurança (TD-04, TD-28).
4. `APP_ENV=production` com `CORS_ORIGINS` explícito (a aplicação já recusa `*` e desliga `/docs`).
5. Lockfile Python e política de atualização de dependências (TD-29, TD-07).
