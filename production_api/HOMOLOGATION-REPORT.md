# Job Agent — Homologação técnica incremental (20/10/2026)

## Escopo e evidências
- Artefato de origem: `job-agent-unified-product-v3.zip`.
- API e interface da pasta `production_api` revisadas.
- Testes: `pytest -q` — **15 passed** em banco SQLite efêmero (7 testes originais e 8 adicionais). Os testes cobrem cadastro, login, troca de senha e revogação, acesso não autenticado, isolamento entre duas contas, CRUD de perfil/evidências/vagas/candidaturas/tarefas, painel, diagnóstico, recursos Premium, exportação, exclusão, cabeçalhos HTTP, disponibilidade de recursos web, simulação de checkout, assinatura de webhook e reconciliação de status de assinatura por consulta à fonte autoritativa simulada.
- Verificações de Stripe usam **mocks**; não são transações reais.
- Não foi possível testar Chromium real (navegador Playwright não instalado), PostgreSQL real (servidor indisponível), Docker (não instalado), Stripe real (credenciais não fornecidas), HTTPS em domínio público, backups/restauração, carga e alertas externos. **Esses gates permanecem pendentes.**

## Correções incorporadas
1. Validação de sessão consulta existência do usuário, e compara validade de timestamp com/sem timezone.
2. Webhook recusa vincular uma assinatura a um customer diferente de outro já associado à conta.
3. Evento `checkout.session.completed` exige modo subscription e status complete e vínculo de usuário válido; eventos sem vínculo falham para permitir reprocessamento.
4. Conflito de persistência no webhook só é tratado como duplicidade quando o ID do evento realmente está registrado; outros conflitos falham e podem ser reprocessados.
5. Exclusão de conta impede apagar vínculo com qualquer subscription Stripe ainda referenciada, reduzindo risco de assinaturas órfãs.
6. Suite adicional de testes com usuários independentes, controle de autorização, validação de entradas e mocks de cobrança.

## Gates de lançamento — bloqueadores
- [ ] PostgreSQL 16: migração Alembic upgrade e downgrade em banco descartável; integridade, concorrência e backups com restauração comprovada.
- [ ] Stripe **test mode**: checkout, customer, assinatura, pagamento recusado, cancelamento, atraso, retries, duplicidades e webhooks fora de ordem; reconciliar eventos em concorrência e não só sequencialmente.
- [ ] Navegador real (Chromium, Firefox, WebKit) e dispositivos móveis: fluxos completos, acessibilidade, erros de rede, autenticação e pagamento.
- [ ] HTTPS real e reverse proxy; firewall, CSP, secrets manager, Redis/gateway rate limiting, proteção contra CSRF conforme estratégia de token.
- [ ] Segurança externa: SAST, dependências com CVEs, DAST, testes de carga, verificação de logs sem dados sensíveis, revisão de LGPD e exclusão com retenção de auditoria legal.
- [ ] Observabilidade externa: métricas privadas, logs estruturados, alertas de erro, tracing, disponibilidade, backup e plano de incidente.
- [ ] E-mail verificado e recuperação de senha com tokens expirados e uso único.
- [ ] Teste com 10 usuários reais: conclusão do onboarding, diagnóstico útil, primeira ação e percepção de valor; coletar feedback e corrigir gargalos.

## Lacunas conhecidas ainda existentes
- Limite de login local à memória do processo; não é defesa distribuída.
- Idempotência de checkout por janelas de dez minutos reduz retries, mas **não impede** sessões distintas/assinaturas paralelas em janelas diferentes; precisa de lock de conta e reconciliação Stripe.
- Token bearer em `sessionStorage` é vulnerável a comprometimento em caso de XSS; revisar arquitetura de sessão e CSP.
- O diagnóstico é correspondência textual, não verificação independente de competência nem aconselhamento humano.
- `metrics` retorna apenas status estático; monitoramento externo não existe.
- O esquema Alembic inicial e procedimentos de rollback ainda exigem validação PostgreSQL.
- Sem teste de navegação real, não há garantia de UX nem de ausência de erros JavaScript de runtime.

## Decisão
**NÃO HOMOLOGADO PARA COBRANÇA EM PRODUÇÃO.** O código tem um conjunto mais amplo de testes automatizados e correções de segurança, mas as integrações externas e os requisitos operacionais continuam bloqueados até execução em ambiente controlado.
