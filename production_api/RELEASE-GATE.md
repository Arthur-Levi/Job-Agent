# Job Agent — P0/P1/P2 release gate

## Implementado nesta versão
- Interface web integrada à API `/api` de produção; login, cadastro, perfil, evidências, vagas, candidaturas, tarefas, diagnóstico, assinatura e conta.
- UI não injeta HTML dinâmico: campos são renderizados com `textContent`.
- CSP, X-Frame-Options, no-store, Argon2, sessões aleatórias com hash SHA-256 em banco, isolamento por usuário, alteração de senha com revogação das sessões.
- Checkout Stripe hospedado com idempotência de janela curta e bloqueio de checkout para assinaturas existentes.
- Webhook Stripe assinado, deduplicado e reconciliado com o estado atual da assinatura na Stripe.
- Diagnóstico explicável com referências de evidências declaradas por requisito e lacunas, sem pontuação inventada.
- PostgreSQL com Alembic (schema inicial herdado e migration 0002), Docker Compose e readiness.
- Indicadores de execução e exportação de dados.

## Não homologado / bloqueios para venda pública
1. **Stripe real**: não foram executados pagamentos, reembolsos, falhas, cancelamentos nem webhooks com conta Stripe real. A reconciliação exige rede externa e configuração de chaves.
2. **PostgreSQL real**: os testes automatizados desta entrega usam SQLite. Executar testes de migrations, concorrência e transações com PostgreSQL.
3. **Login distribuído**: rate limit é em memória; implementar Redis ou WAF/ingress rate limit antes de escalar múltiplas instâncias.
4. **E-mail**: verificação de e-mail, recuperação de senha e notificações transacionais ainda não existem.
5. **LGPD**: revisar retenção de auditoria e eventos Stripe, política de privacidade, base legal, solicitações de titulares, exclusão e obrigações fiscais com profissional qualificado.
6. **Monitoramento**: health checks e logs não substituem métricas externas, alertas, rastreamento e testes de recuperação de backup.
7. **Diagnóstico**: matching é textual e depende de dados declarados. Não há verificação independente de credenciais, integração de vagas externas nem validação com usuários reais.
8. **UX**: teste real de navegador, acessibilidade, responsividade e fluxo de cobrança completo ainda necessários.
9. **Infraestrutura**: o Compose expõe somente localhost; exige proxy TLS, DNS, firewall, gestão de segredos e backup externo configurados pelo operador.
10. **Billing**: proteção contra assinaturas paralelas entre janelas de checkout ainda depende de reconciliação adicional com a Stripe; revisar cenários de múltiplas abas e concorrência.

## Operação segura
- Nunca usar o banco de produção para testes destrutivos.
- Configurar `DATABASE_URL`, `POSTGRES_PASSWORD`, `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET`, `PUBLIC_BASE_URL` em gerenciador de segredos.
- Aplicar `alembic upgrade head` antes de iniciar a API. Realizar backup antes de cada migração.
- Rodar `pytest -q tests/test_production.py tests/test_v3.py` e verificar `/health/ready`.
- Não executar `alembic downgrade base` em dados reais: migration inicial herdada contém `drop_all`.
- Nunca afirmar que a plataforma garante vaga, salário ou taxa de contratação.
