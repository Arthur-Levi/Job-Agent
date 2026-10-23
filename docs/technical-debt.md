# Dívida técnica e decisões pendentes (fechamento da D1)

Lista consolidada D1.1–D1.5 + impactos do [Addendum A01](architecture/addendum-A01-multichannel-acquisition.md).
Severidade = impacto se ignorada na hora errada. "Quando" = fase/gatilho em que deve ser tratada.

## 1. Segurança e operação

| ID | Item | Risco | Sev. | Quando |
|---|---|---|---|---|
| TD-01 | **Sem autenticação.** Qualquer cliente que alcance a API opera como o usuário local, inclusive com `force` em status. | Exposição de dados e correção de status por qualquer um. | **Alta** | Antes de qualquer exposição fora do localhost |
| TD-02 | Limite de payload só por `Content-Length`; corpos *chunked* passam. | Consumo de memória. | Média | Antes de produção (limitar no proxy/ASGI) |
| TD-03 | Respostas 500 não levam headers CORS. | O navegador mostra erro de CORS no lugar do 500 (diagnóstico via `X-Request-ID` e log). | Baixa | Quando houver deploy |
| TD-04 | **Backend não containerizado**; sem config de produção (workers, proxy, TLS). Compose só tem PostgreSQL. | Ambiente de deploy não reproduzível. | Média | Pré-deploy |
| TD-05 | **CI nunca executou no GitHub** (validado com `actionlint` e replicando cada passo localmente). | Surpresas no primeiro push. | Média | Primeiro push |
| TD-06 | Observabilidade só em logs JSON (sem métricas/tracing). | Diagnóstico limitado em produção. | Baixa | Pré-deploy |
| TD-07 | Sem política de atualização de dependências (Dependabot/Renovate); majors recentes (React 19, Vite 8, TS 6, Tailwind 4). | Atraso em correções de segurança. | Baixa | Primeiro push |

## 2. Persistência

| ID | Item | Risco | Sev. | Quando |
|---|---|---|---|---|
| TD-08 | SQLAlchemy **síncrono**. | Migrar para async reescreve repositories e services. | Média | Só se houver necessidade de concorrência |
| TD-09 | **Ownership não é garantido pelo banco**: nada impede `applications.user_id` ≠ `jobs.user_id`; só os services. | Vazamento entre usuários se um service errar. | **Média/Alta** | Antes de multiusuário (FK composta ou RLS) |
| TD-10 | Enums como `VARCHAR + CHECK`: valor novo = migration. | Atrito; taxonomias abertas (fonte, setor) não podem ser enum. | Média | D3+ (tabelas para taxonomias abertas) |
| TD-11 | `updated_at` só é atualizado via ORM (SQL cru/bulk não). | Timestamps desatualizados. | Baixa | Se surgirem bulk updates (trigger) |
| TD-12 | Candidaturas (e vagas com candidaturas) **não são apagáveis**; sem processo de retenção/expurgo. | Atrito com privacidade (LGPD) e limpeza. | Média | D6 (política de retenção) |
| TD-13 | Testes recriam o schema `public` do banco `*_test` (destrutivo por design; guard pelo nome). | Perda de dados se alguém criar um banco real chamado `*_test`. | Baixa | — (documentado) |
| TD-14 | Paginação por offset. | Itens repetidos/omitidos se os dados mudarem durante a navegação. | Baixa | Se o volume crescer (keyset) |
| TD-15 | Índice `candidate_skills.candidate_profile_id` redundante com o índice único. | Custo marginal de escrita. | Baixa | D2 |

## 3. API e domínio

| ID | Item | Risco | Sev. | Quando |
|---|---|---|---|---|
| TD-16 | Duplicidade de vaga só por `source_url` **exata** (sem normalizar parâmetros de rastreamento). | Duplicatas passam. | Média | D3 (Duplicate Intelligence) |
| TD-17 | Mesmo erro de salário com dois códigos (`VALIDATION_ERROR` no payload; `JOB_INVALID_SALARY` no estado mesclado). | Tratamento inconsistente no cliente. | Baixa | Quando houver mais clientes |
| TD-18 | O usuário padrão é criado num GET (efeito colateral). | Surpresa; some com auth. | Baixa | Com TD-01 |
| TD-19 | `NOTE_UPDATED` reservado sem emissão; `resume_version_id` fora da API; candidatura nasce sempre em `DISCOVERED`. | Importar histórico exige `force`. | Baixa | D5/D6 |
| TD-20 | Concorrência testada só com 2 threads; sem testes de carga/pool. | Comportamento sob carga desconhecido. | Baixa | Pré-deploy |
| TD-21 | Repositories têm só os métodos em uso (sem `delete` de profile, `list` genérico etc.). | Quem esperar CRUD completo estranha. | Baixa | Sob demanda |

## 4. Frontend

| ID | Item | Risco | Sev. | Quando |
|---|---|---|---|---|
| TD-22 | **Nunca aberto em navegador real**: visual, responsividade e acessibilidade não verificados; sem E2E. | Defeitos visuais/de uso. | **Média** | Já: abrir `make frontend-dev`; depois E2E (Playwright) |
| TD-23 | Tipos TS escritos à mão; o teste de contrato é opt-in e **não roda no CI**. | Divergência silenciosa com o backend. | Média | Gerar tipos do OpenAPI e/ou rodar o contrato no CI |
| TD-24 | Sem cache nem estado global; cada tela recarrega ao navegar. | Chamadas repetidas. | Baixa | Se pesar |
| TD-25 | Dashboard = 5 chamadas (`total` de listas com `limit=1`). | Latência; acoplamento a listas. | Baixa | D7 (endpoint de métricas) |
| TD-26 | Histórico de eventos da candidatura não aparece na UI (a API já devolve). | Auditoria invisível ao usuário. | Baixa | D6 |
| TD-27 | Tema escuro fixo; UI só em inglês. | — | Baixa | Se necessário |

## 5. Impactos do Addendum A01 sobre o que existe

| ID | Item | Sev. | Fase |
|---|---|---|---|
| A01-1 | `jobs.source` + `source_url` único assumem **uma vaga = um link**; falta registro de fontes e proveniência. Migrar para `job_sources` + links/postings, **após a ADR de Opportunity**. | **Alta** | D3 (primeiro item) |
| A01-2 | `applications.job_id NOT NULL` + `UNIQUE(user_id, job_id)` não comportam recrutador/candidatura espontânea. Resolvido **conceitualmente** pela entidade `Opportunity` (adendo 3.K); **ADR obrigatória antes de migrar**. | **Alta** | ADR no início da D3; D6 |
| A01-3 | `jobs.company` é texto: falta entidade `Company` (aliases, setor). | Média | D3 |
| A01-4 | `ApplicationStatus` único (CHECK por enum) → um workflow de cinco; `app/domain/application_status.py` vira a definição do workflow 1. | Média | D6 |
| A01-5 | `application_events` sem `workflow_type`, versão, ator e confirmação humana (preservar o trigger append-only). | Média | D6 |
| A01-6 | `candidate_profiles` sem dados de contato (exigidos pelo Quality Gate). | Média | D2 |
| A01-7 | Fatos do perfil sem verificação/evidência (base do Truth Validator). | Média | D2 |
| A01-8 | `resume_versions` sem template, plano, ledger, relatório do gate e hash do arquivo. | Média | D5 |
| A01-9 | Segredos de conectores: só referências (env/cofre) no banco. | Média | D3 |
| A01-10 | Dimensões de analytics (fonte, canal, setor, modelo) precisam ser fotografadas no evento. | Média | D6–D7 |
| A01-11 | **Revisão LGPD** antes de armazenar dados de recrutadores. | **Alta** | Antes da D6 |
| A01-13 | **ADR de Opportunity** (Opportunity / JobPosting / Application): bloqueia a deduplicação da D3. Sem migração na D1. | **Alta** | Início da D3 |
| A01-14 | **Política de retenção** de dados de recrutadores: documentar prazos concretos antes da D6. | Média | Antes da D6 |
| A01-12 | **Termos/APIs oficiais** de cada fonte precisam ser lidos e registrados antes de qualquer conector; sem isso, só importação manual. | **Alta** | D3 |

## 5b. Achados da revisão de segurança da D1.5 (ver `security-review.md`)

| ID | Item | Risco | Sev. | Quando |
|---|---|---|---|---|
| TD-28 | Sem headers de segurança (`X-Content-Type-Options`, `Cache-Control`, CSP no frontend). | Hardening ausente; baixo risco em localhost. | Baixa | Pré-deploy |
| TD-29 | Sem lockfile do Python (dependências por faixa; o npm tem `package-lock.json`). | Builds não reproduzíveis bit a bit. | Média | Pré-deploy |
| TD-30 | Ações do CI fixadas por tag (`@v4`/`@v5`), não por SHA. | Cadeia de suprimentos do CI. | Baixa | Primeiro push |
| TD-31 | Sem rate limiting. | Abuso se exposta (ver TD-01). | Média | Com a autenticação |
| TD-32 | `.env.example` traz senha de exemplo fraca (`change-me-locally`); o compose exige que seja definida, mas não que seja forte. | Senha fraca em máquinas compartilhadas. | Baixa | — (documentado) |
| TD-33 | A auditoria de dependências (`pip-audit`, `npm audit`) roda no CI só de forma informativa (`continue-on-error`). | Vulnerabilidade nova não bloqueia o merge. | Baixa | Quando houver política |

## 6. Decisões

### 6.1 Aprovadas pelo usuário (2026-10-08)
Numeração D4–D8 (sujeita a gates) · fontes-alvo só com autorização verificada por fonte e operação · Headhunter CRM com
dados mínimos e retenção documentada · quatro setores iniciais editáveis · 20 candidaturas por setor = limiar
exploratório (sem alegações conclusivas) · entidade conceitual `Opportunity` (sem migração na D1.5).

### 6.2 Minhas, ainda aguardando confirmação

1. Valores de enum que a spec não definia: `JobStatus` (OPEN/CLOSED/ARCHIVED), `JobMatchStatus`, `ResumeVersionStatus`, `ApplicationEventType`, `Seniority` (INTERN…LEAD).
2. `job_requirements.importance` NOT NULL com default `UNKNOWN` (a spec dizia nullable).
3. `score` 0–100 e `confidence` 0–1 em `job_matches`.
4. Candidaturas e vagas com candidaturas não são apagáveis (usar `WITHDRAWN`).
5. `force` livre para qualquer cliente; confirmação só na UI.
6. "Interviews" no dashboard = `INTERVIEW` + `TECHNICAL`.
7. Campos opcionais em branco viram `null` (no PATCH, limpam o valor).
8. Perguntas ainda abertas na seção 5 do adendo (acessos às fontes, prazos de retenção, ADR de Opportunity).
