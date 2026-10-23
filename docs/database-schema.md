# Database schema (D1.2)

12 tabelas, migration única `0001_initial_schema`. PostgreSQL 13+.

## Convenções
- PK `id` UUID (`gen_random_uuid()` no banco, `uuid4` no ORM). Timestamps `timestamptz` (UTC).
- Enums = `VARCHAR(32)` + `CHECK` nomeada (não enums nativos): adicionar valor é recriar a
  CHECK numa migration, sem `ALTER TYPE`. Enums vivem em `app/domain/enums.py`.
- Constraints com nomes determinísticos (`NAMING_CONVENTION` em `app/db/base.py`).
- `updated_at`: atualizado via ORM (`clock_timestamp()`); SQL cru/bulk NÃO o atualiza.

## Comportamento de DELETE (deliberado)
| FK | ON DELETE | Motivo |
|---|---|---|
| `*.user_id` → users | RESTRICT | apagar usuário nunca apaga dados em silêncio |
| candidate_{skills,projects,experiences,educations}.candidate_profile_id | CASCADE | composição do perfil |
| job_requirements.job_id | CASCADE | composição da vaga |
| job_matches.job_id / .candidate_profile_id | CASCADE | dado derivado, recomputável |
| resume_versions.candidate_profile_id | RESTRICT | currículos gerados não somem com o perfil |
| resume_versions.job_id | SET NULL | currículo sobrevive à vaga |
| applications.job_id | RESTRICT | vaga com candidatura não pode ser apagada (API → 409) |
| applications.resume_version_id | RESTRICT | currículo usado não pode ser apagado |
| application_events.application_id | RESTRICT | histórico nunca é apagado em cascata |

Consequência: toda candidatura tem ao menos um evento, logo **candidaturas não são apagáveis**;
use `WITHDRAWN`. Reset de dev: `TRUNCATE ... CASCADE` (TRUNCATE não aciona o trigger).

## application_events é append-only
Trigger `trg_application_events_append_only` bloqueia UPDATE/DELETE (SQLSTATE 23001, que
o SQLAlchemy expõe como `IntegrityError`). `created_at` usa `clock_timestamp()` para manter
ordem estrita entre eventos da mesma transação. O atributo ORM é `event_metadata` (coluna
`metadata`), porque `metadata` é reservado pelo SQLAlchemy.

## Unicidade e integridade
- 1 perfil por usuário (`UNIQUE(user_id)`); 1 candidatura por (usuário, vaga).
- Skill única por perfil e requisito único por vaga, ignorando caixa (`lower(name)`).
- Vaga: mesma `source_url` não repete por usuário (índice parcial; várias sem URL são ok).
- `job_matches`: uma linha por (vaga, perfil, `analysis_version`); NULL conta como `''`.
- Vaga: `salary_min <= salary_max`, salário exige `currency`, `currency` ISO 4217 maiúscula.
- Experiência: `current = true` ⇒ `end_date IS NULL`; `end_date >= start_date`.
- Strings obrigatórias rejeitam vazio/espaços (`nonblank_*`).

## Decisões de modelagem a confirmar (valores escolhidos por mim; a spec não os definia)
- `JobStatus`: OPEN, CLOSED, ARCHIVED. `JobMatchStatus`: PENDING, COMPLETED, FAILED.
  `ResumeVersionStatus`: DRAFT, READY, ARCHIVED. `ApplicationEventType`: CREATED,
  STATUS_CHANGED, NOTE_UPDATED. `Seniority`: INTERN, JUNIOR, MID, SENIOR, LEAD.
- `job_requirements.importance` é NOT NULL com default `UNKNOWN` (a spec dizia nullable;
  nullable + `UNKNOWN` seriam dois jeitos de dizer "não sei").
- `job_matches.score` limitado a 0–100 e `confidence` a 0–1.
