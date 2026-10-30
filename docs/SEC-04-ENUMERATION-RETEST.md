# SEC-04 — Reteste de enumeração de contas

## Evidência do operador
Teste realizado na worktree `/workspaces/Job-Agent-SEC04/production_api` contra API local isolada `http://127.0.0.1:8003`, banco descartável `jobagent_ux`.

```text
PASS: login returns indistinguishable 401 body for existing/unknown account
PASS: registration hides existence of account in both status and body
CLEANUP: ephemeral account deleted
```

A alteração do cadastro foi publicada no commit `dd115a8` da branch `test/sec04-abuse-rate-limit`; o operador informou o resultado do reteste, não execução direta do assistente.

## Veredito
**PASS restrito aos casos de enumeração cobertos pelo teste**. Login devolve 401 com corpo idêntico para senha errada/conta inexistente; cadastro devolve status/corpo idênticos para email novo/existente no teste. Conta fictícia excluída.

## Pendências
- Limitação compartilhada entre processos/reinícios ou política equivalente aplicada pelo gateway.
- Verificação de tempo de resposta, concorrência no cadastro e fluxo de verificação de e-mail.
- Não presumir proteção contra abuso distribuído ou ausência de outros vetores de enumeração.
- Nenhum merge autorizado em `main` ou PR #2; preservar bancos originais.
