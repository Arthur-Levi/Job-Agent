# SEC-04 — Teste controlado de limitação de login

Registro do resultado informado pelo operador no Codespaces.

## Ambiente
- Branch isolada: `test/sec04-abuse-rate-limit`
- API exclusiva: `http://127.0.0.1:8002` (processo único)
- Banco descartável: `jobagent_ux` em `127.0.0.1:55433`
- Script: `production_api/tests/verify_sec04_rate_limit.py`
- Não executar contra bancos originais ou serviços públicos.

## Evidência fornecida
```text
PASS: 10 invalid-login attempts rejected 401; attempt 11 throttled 429 + Retry-After=60
PASS: no stack traces or password hashes exposed in error bodies
PASS: strictly bounded 11 requests against disposable isolated API at 127.0.0.1:8002
```

## Veredito
**PASS para o smoke test de força bruta em instância única**, conforme logs enviados pelo operador. Não houve execução direta pelo assistente.

## Riscos ainda abertos
- Limitador no código é em memória e não é compartilhado entre processos, instâncias ou reinicializações.
- Limitação por IP pode causar bloqueio de usuários legítimos atrás de NAT e não substitui limites por conta/identificador.
- Ainda faltam testes controlados para distinção de erros de e-mails existentes/inexistentes, comportamento de erros inesperados, registro de observabilidade e validação de gateway em implantação real.
- Não extrapolar este PASS para proteção contra ataques distribuídos.

## Próximo gate
Completar SEC-04 com cenários adicionais isolados e estratégia de proteção distribuída (gateway/limitação compartilhada), antes da homologação final.

Nenhum merge em `main` ou PR #2 foi autorizado.
