# SEC05-FC06 — Stripe Test Mode: plano e portões de homologação
Data: 2026-10-31
Branch isolada: `test/sec05-stripe-prebeta`

## Estado
- FC01–FC05, mais INFRA-01D, têm evidências reportadas de PASS nos checkpoints anteriores.
- **FC06A implementado, pendente execução:** `production_api/tests/test_sec05_stripe_sdk_signed.py`. Usa `stripe.Webhook.construct_event` real para conferir HMAC sobre JSON e eventos simulados, TestClient FastAPI e PostgreSQL descartável persistente. `Subscription.retrieve` e `Customer.retrieve` são interceptados; **não há rede Stripe**.
- **FC06B/C/D ainda não implementados/aprovados**. Não cobrar usuários, não habilitar Stripe live.

## Execução FC06A
Sincronizar branch. As credenciais PostgreSQL locais estão em `/workspaces/.jobagent-sec05-postgres.env`. Ler esse arquivo sem exibir a senha e gerar `DATABASE_URL` para o processo pytest com destino explícito `postgresql+psycopg://ux_test@127.0.0.1:55434/jobagent_ux`, revisão `0006_subscription_price_guard`. Exigir `SEC05_PG_INTEGRATION=1`. O teste substitui a chave Stripe em memória por identificador `sk_test_` falso e assina localmente os eventos com segredo `whsec_` aleatório; nenhuma chave real é exigida. A saída de PASS só é válida após pytest exit 0.

## Escopo técnico e limites
1. **FC06A (SDK local, sem rede):** rejeitar corpo adulterado com assinatura válida para conteúdo original; aceitar assinatura HMAC íntegra; criar Premium somente com remote `active`, preço exato, identidade da assinatura/cliente e dono corretos; ignorar replay; revogar `canceled`; rejeitar efeito de evento antigo. Confirmar limpeza só de registros identificados.
2. **FC06B (Stripe Test Mode via API real):** usar conta Stripe de TESTE, produto/preço recorrente exclusivo e `STRIPE_SECRET_KEY=sk_test_...`, `STRIPE_PRICE_ID=price_...`, webhook secret `whsec_...`, `PUBLIC_BASE_URL` HTTPS de sandbox. Nunca commitar secrets. Criar sessão e realizar pagamento com cartão de teste em interface oficial Stripe; verificar assinaturas reais na base de teste e logs de API. Sem pagamento real.
3. **FC06C (eventos de faturamento):** definir política de elegibilidade para `invoice.paid`, `invoice.payment_failed`, `invoice.payment_action_required`, `customer.subscription.updated/deleted`, cobrança em atraso, cancelamento ao final do ciclo e reembolso. Atualmente `invoice.*` **não atualiza um ledger financeiro**. O webhook registra IDs de eventos desconhecidos e responde 200: isto NÃO equivale a conciliação. Implementar invoice ledger com IDs únicos e associação a cliente/assinatura, status do pagamento, moeda, total e reconciliação com API Stripe antes de declarar concluído.
4. **FC06D (reconciliação):** relatório interno que confira assinatura, invoice e pagamentos remotos; reprocessamento seguro, falha Redis/PG/Stripe, eventos fora de ordem, retry, alertas de inconsistência e observabilidade; não usar valores financeiros estimados como pagamentos confirmados.
5. **FC06E (pré-beta):** regressão pytest geral, build frontend, contrato API/PG reais, testes de autorização e recuperação, revisão migrations históricas, segredos, limites e política de suporte/cancelamento.

## Condições de segurança
Somente `test/sec05-stripe-prebeta`, `jobagent-sec05-db` (`55434`) e `jobagent-sec05-pgdata`. Preservar `main`, PR #2, worktrees originais e containers PostgreSQL originais. Não executar ações destrutivas nem usar Stripe live.
