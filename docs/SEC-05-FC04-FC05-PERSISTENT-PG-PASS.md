# SEC05 — Checkpoint FC04 + FC05 no PostgreSQL persistente

Data: 2026-10-31
Branch isolada: `test/sec05-stripe-prebeta`
Status: **PASS reportado pelo operador para a execução integrada FC04 e FC05**.

## Evidência desta execução

O operador informou a linha final:

```text
SEC05: TESTES INTEGRADOS APROVADOS
```

O roteiro fornecido executa sequencialmente:
1. `tests/test_sec05_postgres_live.py`
2. `tests/test_sec05_postgres_race.py`

O roteiro interrompe a execução quando algum pytest retorna código diferente de zero e só imprime a mensagem de aprovação após ambos terminarem com código zero. Assim, esta evidência fundamenta o sucesso dos dois **processos pytest**, sem comprovar a contagem detalhada de asserts ou o transcript individual dos casos.

## Ambiente

- PostgreSQL 16 em `jobagent-sec05-db`, volume nomeado `jobagent-sec05-pgdata`, porta local `127.0.0.1:55434`.
- Banco descartável `jobagent_ux`, usuário `ux_test`, schema na revisão `0006_subscription_price_guard`.
- Credencial gerada localmente e lida de `/workspaces/.jobagent-sec05-postgres.env`; nenhum segredo deve ser versionado.
- Stripe simulado: **nenhuma cobrança ou assinatura Stripe Test Mode real**.
- `INFRA-01D: PERSISTENCE PASS` já reportado após reinício controlado do container e verificação/limpeza de marcador.

## Garantias limitadas

- FC04 exercita ciclo HTTP FastAPI com PG real: persistência de assinatura, duplicata sequencial, cancelamento, webhook fora de ordem e bloqueio de preço não autorizado.
- FC05 executa teste adversarial de **duas entregas simultâneas do mesmo evento**, com sincronização para intensificar condição de corrida, e exige respostas de sucesso, somente um registro webhook/assinatura, e limpeza direcionada.
- Uma execução aprovada não prova resistência a todas as interleavings, multi-processo distribuído ou falhas de rede.
- Os 21 testes em SQLite/Stripe mock permaneceram PASS em execução anterior, mas **não foram reexecutados neste checkpoint**.

## Pendências para SEC-05 completa e beta público

1. Reexecutar suíte geral, verificações de contrato e build frontend.
2. Testes de idempotência sob repetição/alta concorrência, exceções transacionais e múltiplos processos.
3. Stripe SDK com webhook assinado e credenciais **somente modo de teste**; checkout e portal Test Mode, evento de fatura paga/falha, cancelamento no período e mudança de plano.
4. Reconciliação financeira com Stripe (faturas, pagamentos, reembolsos e disputa), eventos fora de ordem, retries e observabilidade.
5. Corrigir a migration histórica `0001_initial` que importa modelo dinâmico, sem comprometer upgrades legados.
6. Persistência sob reconstrução do Codespaces, rotacionar segredo descartável anteriormente exposto e preparar backups de produção.
7. Política de autorização a partir de eventos íntegros e estado/price/owner, com revisão de segurança.

## Segurança de escopo

**Não** tocar em `main`, PR #2, worktree original `/workspaces/Job-Agent`, bancos originais `jobagent-postgres-v2` e `jobagent-postgres-recovered`, nem executar `docker rm`, `docker volume prune`, `docker compose down -v` ou `alembic stamp head`.

Arquivo de evidências; nenhuma alteração de lógica de produção neste commit.
