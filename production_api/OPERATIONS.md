# Operação e implantação

1. Configure as variáveis do `.env.example` em cofre de segredos e `POSTGRES_PASSWORD` para o Compose.
2. Suba o banco: `docker compose -f docker-compose.production.yml up -d db`.
3. Migre: `docker compose -f docker-compose.production.yml run --rm api alembic upgrade head` (substitua entrypoint se necessário).
4. Suba API: `docker compose -f docker-compose.production.yml up -d api`.
5. Coloque reverse proxy HTTPS confiável na frente de `127.0.0.1:8000`; configure `PUBLIC_BASE_URL` exatamente com o domínio HTTPS.
6. Configure endpoint de webhook Stripe `/api/billing/webhook` e eventos `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`.
7. Antes de qualquer atualização, crie backup: `docker compose -f docker-compose.production.yml exec -T db pg_dump -U jobagent -Fc jobagent > backup-$(date +%Y%m%d).dump`.
8. **Teste restauração em banco separado** antes de depender dos backups; criptografe e armazene fora do servidor.
9. Monitore externamente `/health/ready`, taxa de erros HTTP, latência, espaço de disco e falhas de webhooks.
10. Nunca exponha porta do PostgreSQL, arquivo `.env` ou endpoint de métricas publicamente.

Os testes unitários não substituem teste de homologação em ambiente real.
