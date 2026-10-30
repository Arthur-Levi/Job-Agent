# SEC-04 — Homologação do limite distribuído

Resultado apresentado pelo operador na worktree `/workspaces/Job-Agent-SEC04-Redis`, branch `feature/sec04-distributed-rate-limit`, usando duas instâncias de teste (`127.0.0.1:8004` e `:8005`), PostgreSQL descartável `jobagent_ux` e Redis descartável `127.0.0.1:56379/15`.

```text
PASS: two independent API processes share a Redis limit: 10 x 401 + 1 x 429
PASS: 429 returned with valid Retry-After; no real users created
PASS: exactly 11 bounded requests against 127.0.0.1:8004/8005
```

**PASS** para teste controlado de contador compartilhado Redis entre duas instâncias. Evidência fornecida pelo operador; não executada diretamente pelo assistente.

## Pendente para fechar SEC-04
- Testar Redis indisponível: autenticação deve falhar de modo fechado (HTTP 503) sem acessar dados reais.
- Revisar comportamento de erro, concorrência, limites para IPs/NATs e confirmação da configuração de produção.
- Não efetuar merge para `main` nem PR #2 sem aprovação expressa.
