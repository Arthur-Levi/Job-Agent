# JOB AGENT FINANCIAL CORE — ADR FC-001
Status: PROPOSTA ARQUITETURAL, NÃO IMPLEMENTADO
Data: 2026-10-31
Branch isolada: test/sec05-stripe-prebeta
Objetivo: segurança de assinaturas, conciliação e unit economics sem assumir custódia de dinheiro.

## Base verificada em código
- production_api/models.py: Subscription(user_id, stripe_customer_id, stripe_subscription_id, status, updated_at), WebhookEvent(id, processed_at), Audit(user_id, action, created_at).
- production_api/main.py: /api/billing/status considera status active/trialing; checkout usa STRIPE_PRICE_ID; webhook valida assinatura, deduplica event.id e busca subscription remota ao processar subscription.*; checkout.session.completed associa customer.
- production_api/tests/test_homologation.py: teste de assinatura ativa com Stripe.Subscription.retrieve retornando apenas status='active'; testes de inserção direta de Subscription(status='active') exercitam autorização por usuário, não elegibilidade financeira do preço.
- Lacuna de aceitação: não há prova de validação do conjunto de itens/price autorizados da assinatura antes de conceder premium.

## Princípios inegociáveis
1. Stripe é processador de pagamentos e fonte externa de eventos; PostgreSQL é projeção operacional e trilha interna auditável. Nunca armazenar dados brutos de cartão nem movimentar fundos em nome do usuário.
2. Dinheiro em centavos inteiros com moeda ISO, nunca floats; eventos e lançamentos idempotentes; correções por novos lançamentos, não por apagar lançamentos históricos.
3. Premium exige customer vinculado ao usuário, subscription válida, price allowlisted, estado e janela de vigência conforme política. Nenhum evento isolado concede acesso sem validação.
4. Separar: receita contratada (MRR), faturas, pagamentos recebidos, reembolsos, impostos, taxas e custos de IA. Não confundir saldos de Stripe, caixa, MRR e lucro.
5. Event-driven, tratamento de duplicatas e ordem arbitrária; assinaturas verificadas com raw-body, assinatura/timestamp, transações e reconciliação periódica.
6. Respeitar dados sensíveis/segredos; exportação/eliminação com exceções de retenção contábil aplicáveis e revisão jurídica antes de produção.

## Arquitetura modular dentro do FastAPI (sem microsserviços prematuros)
- billing_gateway.py: encapsula cliente Stripe e objetos test/live com guardrail de ambiente.
- billing_webhooks.py: verificação de assinatura, tabela de inbox, deduplicação, transação e estados de processamento.
- billing_policy.py: função pura evaluate_entitlement(subscription, allowed_prices, now) -> decisão/razões; bloquear quando faltam provas.
- billing_reconcile.py: job periódico compara objetos do Stripe com projeções locais e registra divergências, sem sobrescrever decisões sem auditoria.
- financial_ledger.py: lançamentos monetários internos para reconciliação e relatórios, em centavos; não é carteira/custódia e não lança dinheiro real.
- usage_meter.py: mede consumo de IA por usuário, tokens e custo estimado; sem dados do currículo nos logs.
- finance_reporting.py: coortes, MRR, churn, arrecadação efetiva, estornos, receita líquida de taxas e custo por usuário.

## Dados propostos (migração futura, NÃO executar antes de testes)
- billing_webhook_inbox: event_id PK, event_type, provider, object_id, received_at, processed_at, processing_status, error_code, attempt_count; sem payloads sensíveis completos.
- billing_subscriptions: user_id, provider_customer_id UNIQUE, provider_subscription_id UNIQUE, status, period_start/end, cancel_at_period_end, currency, price_id autorizado, last_synced_at, source_event_id.
- billing_invoices: invoice_id UNIQUE, subscription_id FK, amount_due_cents, amount_paid_cents, currency, status, period_start/end.
- billing_payments: payment_intent_id UNIQUE, invoice_id, amount_cents, currency, status, occurred_at, refunded_cents.
- financial_journal + financial_postings: journal/event_id UNIQUE, posted_at, currency, entry_id; balanced postings signed integer cents with CHECK sum per journal/currency = 0 enforced transactionally. Reservar desenho contabilístico final para especialista.
- ai_usage_events: user_id, model, input/output tokens, estimated_cost_microunits, request category, occurred_at; ids sem dados pessoais diretos em logs.
- billing_entitlement_decisions: user_id, subscription_id, decision, reason_code, policy_version, effective_at; retenção controlada.

## Testes em ordem de precedência
A. Reproduzir negativo: assinatura remota active com price ERRADO não deve habilitar premium. Atualmente hipótese de falha; comprovar.
B. Reproduzir positivo: assinatura remota active com price allowlisted, customer/user válido, período válido => premium.
C. Status active sem itens/price => fail closed.
D. Webhook assinatura inválida => 400; nenhuma mutação.
E. Duplicate event => efeito único; repetição responde sem reprocessar.
F. Eventos de status fora de ordem => buscar estado atual do Stripe, nunca confiar em status antigo.
G. Checkout sessões concorrentes => não gerar assinatura duplicada.
H. cancel_at_period_end, unpaid, past_due, canceled, disputed/refund => política documentada e testada.
I. Eventos de invoice.paid, payment_failed, refunds e asynchronous methods => reconciliação e entitlement apropriados (não ativar baseando-se somente em checkout.session.completed).
J. Testes com DB PostgreSQL DESCARTÁVEL real e Stripe MOCK; posteriormente Stripe TEST real com secrets exclusivamente test.
K. Simulação do ledger: dez centavos/faturas/estornos/correções, no floats, invariant lançamentos compensados, idempotência, concorrência.
L. Falhas de rede e conflito de banco => reprocessamento seguro e trilha de falha.

## Estados e políticas precisam de decisão comercial explícita
- Trial: habilitar apenas se preço autorizado e trial legítimo.
- past_due: sem premium, ou carência claramente definida; nunca presumir.
- cancel_at_period_end: respeitar período já pago até expiração.
- paused/incomplete/unpaid/canceled: sem premium salvo política deliberada e comprovada.
- chargeback/refund: conciliar e decidir revogação conforme política.

## Plano em três fases
**Fase 1 (SEC-05, lançamento):** price binding, webhooks assinados/duplicados, ciclo invoice/subscription, acesso seguro, reconciliação mínima, Stripe TEST e testes PostgreSQL descartável.
**Fase 2 (primeiros 10-100 clientes):** métricas por coorte, custo de IA por usuário, alertas sobre cobranças, margem por cliente, dashboards sem expor PII.
**Fase 3 (>100 clientes e evidência de necessidade):** journal de partidas dobradas interno, reconciliação bancária/Stripe detalhada, automação de anomalias e múltiplos produtos/provedores. Não lançar uma carteira digital, custódia, transferências ou crédito neste projeto sem escopo regulatório separado.

## Guardrails
- Não tocar main, PR #2, /workspaces/Job-Agent original ou bancos originais jobagent-postgres-v2 e jobagent-postgres-recovered.
- Usar exclusivamente banco descartável ux_test@127.0.0.1:55433/jobagent_ux; sem migrar sem verificar identidade real de conexão e autorização.
- Não enviar .env, secrets, sec04-env.sh, dados pessoais ou dumps.
- SEC-05 ainda sem PASS financeiro. Este documento não representa implementação testada.
