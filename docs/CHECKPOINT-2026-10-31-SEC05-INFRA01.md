# CHECKPOINT — SEC-05 Financial Core / INFRA-01
Data: 2026-10-31
Branch exclusiva: `test/sec05-stripe-prebeta`
Estado: **implementação e regressões simuladas aprovadas; ainda NÃO pronta para cobrança pública**.

## Histórico de evidências PASS
1. **SEC-02:** 38/38 testes de isolamento de API real (evidência anterior).
2. **SEC-03:** 4/4 testes de sessão/browser e 11/11 verificações de revogação/expiração, conforme checkpoints anteriores.
3. **SEC-04:** throttle Redis distribuído entre APIs, 11º login 429 com Retry-After; indisponibilidade Redis retorna 503 (fail closed), conforme checkpoints anteriores.
4. **SEC05-FC01:** reproduzido bug em que assinatura Stripe `active` de preço alheio liberava Premium. Alterado `production_api/main.py` para exigir cliente, ID de assinatura, `stripe_price_id` autorizado e status; webhook consulta assinatura remota e valida customer/ID/um único price esperado. `production_api/models.py` adicionou `stripe_price_id`. Testes negativos/positivos PASS.
5. **SEC05-FC02:** revision Alembic `0006_subscription_price_guard`, adaptada para reconhecer coluna já criada pela migration inicial dinâmica em bases novas. Revisão 0006 alcançada em PostgreSQL descartável anterior.
6. **SEC05-FC02B:** inserção e leitura de uma assinatura fictícia no PostgreSQL real, com ROLLBACK e confirmação de ausência de usuário residual: PASS (evidência em `docs/SEC-05-FC02B-POSTGRES-TRANSACTION-PASS.md`).
7. **SEC05-FC03:** 21/21 pytest PASS com SQLite temporário e Stripe mock (2 warnings). Inclui preço incorreto, preço correto, preço ausente, webhook repetido, cancelamento, evento obsoleto e troca de price. Evidência `docs/SEC-05-FC03-SIMULATED-21-PASS.md`.
8. **SEC05-FC04:** 1/1 teste integrado FastAPI + PostgreSQL real descartável + Stripe mock PASS, seis checkpoints internos (persistência, replay, cancelamento, stale event, mismatch price, limpeza). Evidência `docs/SEC-05-FC04-POSTGRES-WEBHOOK-PASS.md`.
9. **INFRA-01 novo ambiente:** `jobagent-sec05-db` PostgreSQL 16, health=healthy, porta `127.0.0.1:55434`, volume nomeado `jobagent-sec05-pgdata` montado em `/var/lib/postgresql/data`, restart `unless-stopped`, senha local em `/workspaces/.jobagent-sec05-postgres.env` fora do Git. Novo banco `jobagent_ux` migrado para `0006_subscription_price_guard (head)`, coluna `stripe_price_id` confirmada. **Ainda não foi demonstrado restart com dados preservados**.

## INFRA-01 diagnóstico
Container descartável anterior `jobagent-ux-a-db` porta 55433: mesmo ID, `Config.Volumes` declara `/var/lib/postgresql/data`, `Mounts=[]`, restart=no. Após interrupções, banco `jobagent_ux` passou a não ter tabelas. Não declarar causa exata comprovada. Nenhuma tentativa de remoção ou alteração dos bancos originais.

## SEC05-FC05 — situação exata
Arquivo `production_api/tests/test_sec05_postgres_race.py` criado e versionado. **Teste NÃO executou a condição de corrida**: falhou antes na ligação ao banco antigo 55433 (connection refused). Precisa ser adaptado para porta 55434 e nova credencial local; não creditar PASS nem vulnerabilidade reproduzida.

## Próxima sequência curta
1. INFRA-01D: com somente `jobagent-sec05-db`, inserir marcador em `audit`, reiniciar esse container, confirmar o marcador, removê-lo; preservar evidência de PASS ou falha.
2. Atualizar os testes `test_sec05_postgres_live.py` e `test_sec05_postgres_race.py` para parametrizar o alvo isolado 55434 SEM hardcode de senha e com guardrail de container/identidade/volume, com autorização explícita.
3. Rodar novamente FC04 no novo PG, executar FC05 com dois webhooks simultâneos; corrigir eventuais bugs reais em transações e deduplicação.
4. Cobrir falhas de pagamento, invoice, reembolso, portal, mudança de plano, replays/conflitos, assinatura SDK real no **Stripe Test Mode**, conciliação e monitoramento.
5. Corrigir o débito de migrations antigas que importam `Base.metadata` mutável, preservando compatibilidade. Tratar risco de concorrência no cadastro duplicado. Registrar custos de IA/receita e reconciliação sem construir carteira/custódia.
6. Fazer regressão total e checklist de segurança antes de beta pública.

## Isolamento não negociável
- NÃO mexer em `main`, PR #2, worktree `/workspaces/Job-Agent` ou contêineres/bancos originais `jobagent-postgres-v2` e `jobagent-postgres-recovered`.
- NÃO executar `docker rm`, `docker volume prune`, `docker compose down -v`, migrações em banco não validado, nem `alembic stamp head`.
- NÃO adicionar `.env`, senhas, `sec04-env.sh`, dumps ou backups ao Git.
- Não confundir teste de Stripe simulado com cobrança real: **nenhum pagamento real testado**.

## Código e documentos relevantes
- `production_api/main.py`, `production_api/models.py`.
- `production_api/alembic/versions/0006_subscription_price_guard.py`.
- `production_api/tests/test_homologation.py`, `test_sec05_postgres_live.py`, `test_sec05_postgres_race.py`.
- `docs/FINANCIAL-CORE-ADR-001.md`.
- Checkpoints FC02B, FC03 e FC04.

## Próximo checkpoint
Após o teste de persistência INFRA-01D e execução de FC05 contra PostgreSQL persistente. Atualizar este relatório ou criar checkpoint subsequente com logs reais; nunca declarar PASS antecipadamente.
