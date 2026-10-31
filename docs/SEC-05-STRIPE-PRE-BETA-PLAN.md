# SEC-05 — Plano de homologação Stripe (pré-beta)

Data: 2026-10-31. Status **EM ANDAMENTO / NÃO APROVADO**.

## Contexto / limites
Criado a partir de `feature/sec04-distributed-rate-limit` em branch **isolada**. Nada de merge na `main`, PR #2, bancos originais ou cobranças reais. **Credenciais exclusivamente Stripe test mode** (`sk_test_`, `price_...` de objeto criado em TEST, webhook secret `whsec_...` do endpoint de teste). Nunca publicar credenciais, links de checkout, payloads identificáveis ou dumps.

DB permitido após verificação de identidade: PostgreSQL descartável `127.0.0.1:55433/jobagent_ux`, usuário `ux_test` e Docker `jobagent-ux-a-db`. Redis de testes `redis://127.0.0.1:56379/15` (exigir disponibilidade para auth). Confirmar que servidor aponta para banco DESCARTÁVEL antes de qualquer mutação. Nunca usar Docker `jobagent-postgres-v2` ou `jobagent-postgres-recovered`.

## Auditoria estática inicial (production_api/main.py, commit da branch-base)
- `GET /api/billing/status`: `premium_enabled` verdadeiro para status `active` e `trialing`.
- `POST /api/billing/checkout`: usa `STRIPE_PRICE_ID`, `PUBLIC_BASE_URL` HTTPS, trava alguns status já existentes, chave de idempotência por usuário e janela de dez minutos.
- `POST /api/billing/portal`: requer `stripe_customer_id`, usa retorno HTTPS.
- `POST /api/billing/webhook`: verifica assinatura Stripe, limite de payload 1 MiB, registra `WebhookEvent.id` para deduplicar, consulta estado remoto atual da assinatura para eventos subscription.*.
- **Possível lacuna crítica**: concessão de premium baseada no status de uma subscription sem validação explícita de que o item de preço daquela assinatura é `STRIPE_PRICE_ID`. Reproduzir em teste antes de corrigir.
- **Potencial conflito**: `checkout.session.completed` vincula customer ao usuário mas não valida preço, moeda e subscription recebida; a inspeção de vínculo entre contas precisa teste.
- **Revisar** criação concorrente de checkout após status ainda não persistido; expiração, múltiplas sessões e reenvio.
- Não assumir bug explorável sem teste reproduzível.

## Matriz de homologação — nenhuma linha ainda executada
| ID | Cenário | Critério de aprovação |
|---|---|---|
| SEC05-01 | App sem configurar Stripe | 503 seguro, não habilitar premium |
| SEC05-02 | Checkout teste e price R$ 299/mês | Cria sessão somente com price autorizado; zero cobrança real |
| SEC05-03 | Callback com assinatura inválida | 400, sem alterar banco |
| SEC05-04 | Checkout pago teste + webhook assinado | Vincula ao usuário correto; premium somente após status legítimo |
| SEC05-05 | Webhook duplicado | Não cria registros ou assinaturas adicionais |
| SEC05-06 | Eventos fora de ordem | Estado atual remoto vence evento atrasado |
| SEC05-07 | customer/subscription de outro usuário | 409 ou rejeição segura sem transferência de premium |
| SEC05-08 | price não autorizado com assinatura ativa | Não concede premium ao cliente Job Agent |
| SEC05-09 | Inadimplência e cancelamento | Premium segue política documentada; sem acesso indevido |
| SEC05-10 | Falha temporária Stripe/DB | Resposta recuperável; webhook reprocessado; sem perda silenciosa |
| SEC05-11 | Concorrrência de dois checkouts | Sem assinaturas duplicadas involuntárias |
| SEC05-12 | Exclusão com assinatura ativa | Bloqueio controlado e instrução clara para cancelar |

## Sequência sugerida
1. Confirmar ambiente descartável e status das worktrees; nenhum commit local pendente deve ser sobrescrito.
2. Testes offline de assinatura, deduplicação, price/entitlement com Stripe SDK simulado e DB descartável.
3. Corrigir vulnerabilidades confirmadas, teste de regressão, registrar evidência de falha e solução.
4. Só então integrar Stripe test mode com CLI/webhook secret (quando houver credenciais TEST e autorização).
5. Registrar PASS/FAIL por caso com comandos, saídas sanitizadas e hash do commit testado.
6. SEC-05 somente PASS quando 12/12 gates obrigatórios estiverem validados e revisão da implementação concluída.

## Comandos iniciais somente leitura e segurança
```bash
cd /workspaces/Job-Agent-SEC04-Redis
git status --short --branch
git fetch origin test/sec05-stripe-prebeta
git worktree add /workspaces/Job-Agent-SEC05 origin/test/sec05-stripe-prebeta
cd /workspaces/Job-Agent-SEC05/production_api
git status --short --branch
```
Observação: esse `worktree add` cria um detached HEAD por usar `origin/...`; para trabalhar com commits, é preferível usar `git worktree add -b test/sec05-stripe-prebeta /workspaces/Job-Agent-SEC05 origin/test/sec05-stripe-prebeta` se a branch local ainda não existir; verificar antes com `git branch --list`. Nunca sobrescrever worktree pré-existente.

## Instruções para retomada
Branch `test/sec05-stripe-prebeta`. Testes SEC-02 a SEC-04 reportados PASS no escopo isolado; SEC-05 ainda NÃO foi testado. Qualquer cobrança real exige autorização separada.
