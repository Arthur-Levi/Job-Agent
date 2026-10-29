# SEC-02 — Homologação de isolamento real (PostgreSQL descartável)

Data informada pelo operador: 2026-10-29.

## Ambiente
- Worktree de segurança: `/workspaces/Job-Agent-Security` (HEAD detached durante execução).
- Branch de testes: `test/prebeta-isolation-live`.
- API isolada: `http://127.0.0.1:8001`.
- PostgreSQL descartável: container `jobagent-ux-a-db`, database `jobagent_ux`, usuário `ux_test`, porta local 55433.
- Alembic aplicado pelo operador: `0005_master_profile_fact_ledger (head)`.
- Sem autorização para tocar em `jobagent-postgres-v2`, banco recovered, `main` ou PR #2.

## Comando executado pelo operador
```bash
JOB_AGENT_DISPOSABLE=YES_I_CONFIRM_DISPOSABLE \
JOB_AGENT_URL=http://127.0.0.1:8001 \
/workspaces/Job-Agent/production_api/.venv/bin/python \
  tests/verify_prebeta_live_isolation.py
```

## Resultado apresentado
```
PASS: 38 live API status checks; isolation, sessions, export, deletion on ephemeral accounts
```

**Avaliação:** PASS para os 38 checks executados pelo script no ambiente descartável **conforme saída fornecida pelo operador**. O assistente não executou nem observou diretamente a conexão da API ao banco durante a execução, além das validações anteriores apresentadas pelo operador. O número 38 representa asserções de status do script, não 38 auditorias independentes.

### Escopo coberto pela suíte
- Autenticação e rejeição sem token.
- Verificações de propriedade entre contas fictícias A e B, usando evidências, vagas, tarefas, candidaturas, perfil mestre e Fact Ledger.
- Consultas de listagem e exportação sem textos da conta A no retorno da conta B.
- Logout e revogação de sessão por alteração de senha.
- Exportação e exclusão de contas descartáveis.

### Limites
- Teste de integração pontual, não pentest; não prova ausência geral de IDOR, concorrência insegura ou vazamento de dados por todos os endpoints.
- Não cobre Stripe checkout/webhook/test mode, taxa de tentativas de login, browser XSS, segurança de deploy, backups/restauração e LGPD completos.
- Q2.2 browser mock (45/45) permanece separado; captura específica `q22-feedback-mobile-375.png` ainda pendente de inspeção.
- Não presume que a base descartável esteja vazia após testes em caso de eventual falha futura.

## Estado dos gates
- SEC-02: **PASS no escopo da suíte**; expandir cobertura para demais endpoints e execução recorrente CI antes de produção.
- SEC-03: **PARCIAL PASS** para logout e troca de senha; browser e expiração pendentes.
- SEC-05 cobrança: pendente.
- SEC-06 privacidade: parcial (export/delete fictícios); revisão legal/operacional pendente.
- Q2.2 e PR #2: pendentes; **não fazer merge automaticamente**.

## Próximo passo
Validar sessão expirada e isolamento em navegação assíncrona com navegador, confirmar fechamento visual Q2.2, depois executar Stripe em modo de testes, sem pagamentos reais.
