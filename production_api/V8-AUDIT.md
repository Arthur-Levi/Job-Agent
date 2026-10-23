# Job Agent v8 — revisão técnica e auditoria de lançamento

## Implementado nesta entrega
- `technical_quality.py`: parsing estático Python, sinalização de sintaxe inválida, `eval`/`exec`, imports sensíveis e docstrings ausentes. Não executa código; não fornece pontuação de proficiência.
- `contribution_review.py`: resumo de commits declarados, SHA e arquivos; **não autentica** identidades nem consulta GitHub.
- API autenticada `POST/GET /api/evidence/{id}/technical-reviews`: isolada por usuário, persistida no histórico de `ArtifactReview`; exportação/exclusão já incluem esse histórico.
- Interface web para submissão de arquivos e metadados de commits.
- `sandbox_runner.py`: executor opcional de `unittest` em Docker com rede desligada, usuário não privilegiado, recursos limitados, rootfs somente leitura, sem capabilities. **DESABILITADO por padrão**, sem endpoint público. NÃO executado/homologado neste ambiente. Para código hostil, exigir worker em VM descartável, daemon isolado, digest de imagem validado, limites no host e auditoria de isolamento. Docker sozinho não constitui sandbox garantida.

## Resultados de validação desta execução
- Sintaxe Python (`compileall`) e JavaScript (`node --check`): aprovadas.
- Testes direcionados v8: seis casos reportaram sucesso (`......`), porém o processo pytest não encerrou antes do timeout; portanto a execução não é considerada uma suíte aprovada integralmente.
- Suíte geral: execução iniciada, mas não concluída antes do timeout. NÃO afirmar E2E aprovado.
- Sem PostgreSQL real, Stripe real, Chromium, Docker nem análise de projetos de voluntários.

## Achados críticos para comercialização
1. Cobrança não homologada com Stripe em modo de testes, inclusive concorrência, cancelamento, falhas e chargebacks.
2. Sem testes end-to-end em navegador real, PostgreSQL real, migrações e restauração de backup.
3. Rate limiting de autenticação é local ao processo; exige mecanismo distribuído antes de produção.
4. Recuperação de senha e verificação de e-mail não implementadas na API de produção.
5. Análise de evidências continua limitada: heurística Python e commits declarados, sem prova de autoria, testes executados ou revisão humana.
6. Não existem dados de retenção, satisfação, utilidade ou disposição a pagar de clientes reais.
7. Necessário teste independente de segurança, proteção de dados, consentimento e política de retenção.
8. Testes com pytest apresentaram problema de encerramento/timeout; investigar isolamento dos fixtures e lifecycle antes de release.

## Visão do cliente e preço
- Valor perceptível: organização, diagnóstico rastreável, plano semanal, histórico e avaliação documental/técnica preliminar.
- Fricção: usuário precisa cadastrar dados, vagas e arquivos manualmente; sem aquisição autorizada de vagas nem verificação independente.
- Para R$ 299/mês, faltam conveniência, evidência de resultados e confiabilidade operacional. Não vender como 'certificação de competência' nem como 'IA que garante contratação'.
- Decisão: beta fechado supervisionado, sem cobrança automática pública. Testar com 10 usuários reais consentidos; medir conclusão do onboarding, utilidade do diagnóstico, retorno em 7 dias, execução de ações e disposição a pagar.

## Próximas gates de aprovação
- Stripe sandbox com webhooks e múltiplos cenários concorrentes.
- PostgreSQL + Alembic + backup/restore e isolamento entre tenants.
- Playwright/Chromium para todas as telas, fluxos e permissões.
- Sandbox em VM dedicada e revisão de segurança independente antes de aceitar código de terceiros para execução.
- Dupla avaliação humana cega de artefatos consentidos, com comparação e discordância documentadas.
