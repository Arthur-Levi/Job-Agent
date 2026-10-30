# SEC-04 — Aceitação final dos gates planejados

## Evidências fornecidas pelo operador

1. Uma instância, rate limit: `10 x HTTP 401`, tentativa 11 `HTTP 429`, cabeçalho `Retry-After: 60`.
2. Enumeração de contas: login retorna status e corpo indistinguíveis para conta existente e inexistente; cadastro idem após correção. Conta de teste fictícia excluída.
3. Redis compartilhado, duas instâncias `127.0.0.1:8004` e `:8005`: `10 x HTTP 401 + 1 x HTTP 429`, com cabeçalho Retry-After; 11 requisições limitadas a localhost; sem contas reais.
4. Indisponibilidade do Redis, terceira instância de teste `127.0.0.1:8006`, Redis deliberadamente inacessível em `127.0.0.1:56380/15`: resposta recebida pelo operador:
```
HTTP/1.1 503 Service Unavailable
{"detail":"Proteção de autenticação indisponível"}
```

## Veredito
**PASS para os gates da SEC-04 definidos e executados**, no ambiente descartável. Esses são resultados relatados pelo operador, não testes executados diretamente pelo assistente.

## Escopo e limites
- Branch isolada: `feature/sec04-distributed-rate-limit`.
- PostgreSQL descartável `jobagent_ux` na porta 55433; Redis descartável na porta 56379.
- Não houve autorização para merge na `main`, PR #2 ou modificação dos bancos originais.
- A limitação atual é por endereço IP e endpoint; é necessário validar proxy real, balanceador, política de IPs compartilhados (NAT), cenários concorrentes, limites por conta, métricas e disponibilidade.
- A proteção de enumeração cobre status e corpo HTTP, não garante igualdade temporal nem resolve fluxos de confirmação por e-mail.
- O bloqueio 503 durante indisponibilidade do Redis é intencional e deve ser monitorado operacionalmente.
- Antes de rollout de produção, executar CI, revisão de dependências, smoke de deploy e configuração segura de segredos.

## Próximas etapas
SEC-05: Stripe em modo de testes; SEC-06: privacidade; SEC-07: backups/restauração; integração das branches somente com aprovação explícita.
