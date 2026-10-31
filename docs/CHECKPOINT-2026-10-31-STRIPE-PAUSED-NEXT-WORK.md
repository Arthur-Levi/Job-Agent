# CHECKPOINT — Job Agent — Stripe pausado, próximos trabalhos
Data: 2026-10-31
Branch: test/sec05-stripe-prebeta

## Decisão
O usuário ainda não possui conta Stripe. Deixar a integração real em Stripe Test Mode pendente e prosseguir com atividades do Job Agent que independem da conta. Nada de cobrança real ou de declarar lançamento pago pronto.

## Resultados anteriormente reportados
- FC01: guarda de preço exato Stripe para Premium; correção testada.
- FC02/FC02B: migration 0006_subscription_price_guard e transação PostgreSQL com rollback PASS.
- FC03: 21/21 testes simulados PASS.
- FC04: FastAPI webhook + PostgreSQL real descartável, ciclo assinatura/replay/cancelamento/preço inválido PASS.
- FC05: dois webhooks simultâneos em cenário sincronizado, PASS reportado no PostgreSQL persistente.
- INFRA-01: PostgreSQL 16 isolado jobagent-sec05-db, 127.0.0.1:55434, volume nomeado jobagent-sec05-pgdata; INFRA-01D PERSISTENCE PASS após restart e limpeza de marcador.
- FC06A: 1 passed, 1 warning em 2,53 s; HMAC validado pelo SDK real, mas Stripe Subscription.retrieve/Customer.retrieve simulados. Detalhes em docs/SEC05-FC06A-REAL-SDK-SIGNED-PASS.md.

## Bloqueado até haver conta Stripe
- FC06B: checkout e assinatura reais apenas no Stripe Test Mode; criar conta, produto e preço de teste, configurar chaves/segredos localmente, URL HTTPS e webhook.
- FC06C e FC06D: homologação com eventos Stripe reais de invoices/pagamentos, falhas, reembolsos e reconciliação; não foi implementada/validada reconciliação completa.
- Cobrança pública, faturamento financeiro e produção com Stripe live continuam NÃO APROVADOS.

## Próximas tarefas sem Stripe (prioridade)
1. REGR-01: reexecutar toda suíte pytest backend em ambiente apropriado, registrar números e resultados sem marcar PASS antecipadamente.
2. FE-01: verificar build frontend produção, integridade de assets e contratos API; registrar evidências.
3. D2/UX: validar cadastro/login/sessões, persistência, importação de currículo, Master Profile/Fact Ledger, deduplicação, diagnóstico e currículo fundamentado, usando dados fictícios.
4. SEC/QA: revalidar rate-limit Redis, isolamento multiusuário, permissões Premium, upload e recuperação após falhas.
5. DB-01: corrigir arquitetura de migrações históricas dinâmicas (0001_initial) com teste de upgrades em banco descartável.
6. BILL-LOCAL: desenhar ledger/invoice interno e políticas de entitlement sob testes locais; integração e conciliação externa ficam pendentes.
7. READY-01: preparação de beta gratuito, observabilidade, backup/restore, política de dados e suporte. Cobrança só após FC06B–D.

## Limites e isolamento
Não tocar em main, PR #2, worktree original /workspaces/Job-Agent ou containers originais jobagent-postgres-v2 e jobagent-postgres-recovered. Não destruir volumes, nem expor secrets, nem executar migrations em DB sem verificar identidade. Um PASS prévio não equivale a nova execução.

## Próximo checkpoint
Recomendação: REGR-01 + FE-01; depois fluxo D2 completo. Stripe permanece explicitamente adiado por decisão do usuário.