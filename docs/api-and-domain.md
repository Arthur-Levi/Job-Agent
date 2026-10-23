# API e domínio (D1.3)

## Camadas
`Route → Service → Repository → PostgreSQL`
- **Routes** (`app/api/v1`): HTTP apenas; convertem para schemas `*Read` (ORM nunca sai da API).
- **Services** (`app/services`): regras e transações. Dependem de repositories injetados e do
  protocolo `UnitOfWork` (`commit`/`rollback`; a `Session` o satisfaz). Não importam SQLAlchemy.
- **Repositories** (`app/repositories`): persistência e consultas, sempre escopadas por `user_id`.
  Traduzem `IntegrityError` em `ConstraintViolationError(constraint)`; os services mapeiam o
  nome da constraint para erros de negócio (sem pré-checagem sujeita a corrida).
- **Domain** (`app/domain`): enums, máquina de status e regra de salário — Python puro.
- Composição (DI) em `app/api/deps.py`. Services não têm `GenericRepository`; cada repository
  só tem os métodos que algum service usa.

## Usuário padrão (single-user)
`get_current_user` → `UserService.get_or_create_default()`: procura por `DEFAULT_USER_EMAIL`
(sem diferenciar caixa) e cria na primeira requisição (seguro contra corrida). Com auth real,
somente `get_current_user` muda; nenhuma rota/service/repository precisa mudar.

## Transações
Cada operação de escrita roda em `transactional(uow)`: commit único no fim, rollback em qualquer
exceção. Candidatura + evento `CREATED`, e mudança de status + evento `STATUS_CHANGED`, são
atômicos. A mudança de status carrega a candidatura com `SELECT … FOR UPDATE`, então duas
mudanças concorrentes são serializadas e a segunda valida contra o estado já commitado.

## Máquina de status (`app/domain/application_status.py`)
Sem `force`: avanço de um passo em
`DISCOVERED → QUALIFIED → PREPARED → READY → APPLIED → RESPONSE → INTERVIEW → TECHNICAL → OFFER`;
`WITHDRAWN` de qualquer etapa; `REJECTED` de APPLIED em diante (inclui OFFER); `GHOSTED` de
APPLIED a TECHNICAL; de `GHOSTED` volta-se a `RESPONSE` ou encerra-se em `REJECTED`/`WITHDRAWN`.
`REJECTED` e `WITHDRAWN` são terminais. Mesmo status = no-op (200, sem evento).
**Correção administrativa**: `PATCH {"status": "...", "force": true}` ignora a política e grava
`{"forced": true}` no evento. `applied_at` é preenchido ao entrar em APPLIED (se vazio).

## `allowed_next_statuses`
Toda `Application` (lista e detalhe) traz `allowed_next_statuses`: os destinos permitidos SEM `force`,
calculados pela mesma `TRANSITIONS` do domínio. O frontend usa esta lista para montar o seletor de
status e nunca duplica a política.

## Erros
Envelope: `{"error": {"code", "message", "details", "request_id"}}`.

| Status | Códigos |
|---|---|
| 400 | `INVALID_JSON`, `BAD_REQUEST` |
| 404 | `PROFILE_NOT_FOUND`, `JOB_NOT_FOUND`, `APPLICATION_NOT_FOUND` |
| 409 | `PROFILE_ALREADY_EXISTS`, `JOB_SOURCE_URL_EXISTS`, `JOB_HAS_APPLICATIONS`, `APPLICATION_ALREADY_EXISTS`, `INVALID_STATUS_TRANSITION` (details: from/to/allowed) |
| 413 | `PAYLOAD_TOO_LARGE` |
| 422 | `VALIDATION_ERROR` (schema), `JOB_INVALID_SALARY` (estado mesclado no PATCH), `INVALID_JOB_REFERENCE` |
| 503 | `DATABASE_UNAVAILABLE` (/ready) |

## Convenções de entrada
- Campos desconhecidos → 422. Strings obrigatórias: trim, não vazias. Opcionais: `""` vira `null`.
- PATCH parcial: campo ausente = intocado; `null` explícito limpa (rejeitado em obrigatórios).
- URLs só `http(s)`, normalizadas (ex.: `https://x.com` → `https://x.com/`).
- Dinheiro é `Decimal` e trafega como **string** (`"5000.00"`); moeda ISO 4217 em maiúsculas.
- Datas/horas exigem timezone. Resposta em UTC.
- Listas: `{items, total, limit, offset}`, mais recentes primeiro, desempate por `id`.

## Fora do escopo desta fase (por decisão)
Skills/projetos/experiências/formação (D2), `resume_version_id` e eventos de notas (não há
API de currículos), criação de candidatura em status diferente de DISCOVERED (usar PATCH).
