# CHECKPOINT COMPLETO — Job Agent — 2026-10-29/30

## Estado do projeto
**Escopo**: homologações pré-beta isoladas, não release em produção. Nenhum merge em `main` e PR #2 deve permanecer draft sem autorização expressa. O backup do código no GitHub **não equivale** a backup dos volumes PostgreSQL, Redis, arquivos ignorados, segredos, ou alterações locais ainda não enviadas.

## Branches/worktrees locais observadas no Codespaces (último relato)
| Worktree | HEAD observado | Branch local |
|---|---|---|
| `/workspaces/Job-Agent` | `b4be15d` | `feature/d269b-ux-v15` |
| `/workspaces/Job-Agent-Q22` | `0ba8e20` | `q22-browser-validation` |
| `/workspaces/Job-Agent-SEC03` | `bc5754f` | detached |
| `/workspaces/Job-Agent-SEC04` | `dd115a8` | detached |
| `/workspaces/Job-Agent-SEC04-Redis` | `1ea95b3` | detached |
| `/workspaces/Job-Agent-Security` | `e152639` | detached |

GitHub branches de homologação:
- `test/prebeta-isolation-live`: SEC-02, registro commit `dca8b5b`.
- `test/sec03-session-hardening`: correção de limpeza browser e testes, aceitação `b67e4bd`.
- `test/sec04-abuse-rate-limit`: limite de instância única e correção de enumeração, registros `32d7d67` e `68d6b34`.
- `feature/sec04-distributed-rate-limit`: Redis compartilhado e relatórios, última aceitação SEC-04 `72af230` (antes deste checkpoint).
- Q2.2 `feature/q22-feedback-safe` PR #2 draft; verificar `q22-feedback-mobile-375.png` antes de merge.

## Evidências de testes
- SEC-02: **38/38 PASS** API real + PostgreSQL descartável; contas efêmeras.
- SEC-03: **11/11 PASS** expiração real / logout / exclusão, **4/4 PASS** navegador simulado após correção de rascunhos.
- SEC-04: **10 respostas HTTP 401 e 11ª HTTP 429 + Retry-After** em instância única; login e cadastro retornam status/corpo indistinguíveis para contas existentes ou não (reteste PASS).
- SEC-04 distribuído: **10 x HTTP 401 + 1 x HTTP 429** entre APIs 8004 e 8005, Redis compartilhado. Redis inacessível em API 8006 deu **HTTP 503**, `{"detail":"Proteção de autenticação indisponível"}`.
- Q2.2: **45/45 PASS** com navegador/API simulada, ainda pendem revisão visual e integração final com backend real.

## Infraestrutura DESCARTÁVEL
- PostgreSQL: Docker `jobagent-ux-a-db`, banco `jobagent_ux`, usuário `ux_test`, endpoint `127.0.0.1:55433`.
- Redis: Docker `jobagent-sec04-redis`, endpoint `127.0.0.1:56379`, DB 15.
- Migrations Alembic aplicadas **0005_master_profile_fact_ledger (head)** ao banco descartável após reconexão; a tabela `users` e `alembic_version` foram confirmadas.
- `/workspaces/Job-Agent-SEC04-Redis/sec04-env.sh` é um inicializador **LOCAL, não versionado**, não salvar credenciais. Se Codespaces reiniciar, container descartável pode estar parado ou vazio; verificar sem recriar o banco automaticamente.
- Portas de homologação: 8001 (SEC-02), 8003 (enumeração), 8004/8005 (distribuído), 8006 (falha Redis). Servidores temporários podem não estar ativos na retomada.

## Guardrails
**NÃO TOCAR**: banco/container `jobagent-postgres-v2`, `jobagent-postgres-recovered`, volumes e dados originais, `main`, PR #2; não usar `docker volume prune`, `git reset --hard`, `git clean -fd`, `alembic downgrade`. Nenhum merge cross-branch sem revisão/aprovação.

## Próximo checkpoint operacional
1. Verificar `git status --short` em **cada** worktree; alterações locais não estão automaticamente salvas no GitHub.
2. Fazer commit + push apenas de arquivos de código/documentação revisados na branch apropriada. **Nunca enviar `.env`, `sec04-env.sh`, credenciais, bancos, logs de usuários, volumes ou dumps sem criptografia**.
3. Atualizar `feature/sec04-distributed-rate-limit` no worktree SEC04-Redis para incorporar este checkpoint, sem sobrescrever trabalhos locais.
4. SEC-05: Stripe **test mode**, webhooks, eventos duplicados, cancelamento e entitlement premium; nenhuma cobrança real.
5. SEC-06/07: privacidade e backup/restauração **externalizados e criptografados**, sem prometer proteção sem validação.
6. Integração de branches Q2.2/SEC-02/03/04 somente depois de avaliação de conflitos, testes integrados e autorização.

## Limitações
Este checkpoint foi escrito no GitHub com base nos logs relatados pelo operador. Não verifica os untracked/ignored de todas as worktrees, segredos/volumes, nem equivale a backup do Codespaces. Fazer inspeção local antes de considerar o projeto inteiramente salvo.
