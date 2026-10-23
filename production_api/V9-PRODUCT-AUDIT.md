# Job Agent v9 — auditoria funcional e melhoria de experiência

## Entregas verificadas
- `GET /api/onboarding`: quatro passos concretos para o primeiro uso, calculados por conta; completude do cadastro, não empregabilidade.
- `GET /api/career/weekly-brief`: tarefas, horas declaradas, status de candidaturas e próximas ações com justificativa; nenhuma afirmação de resultados externos.
- `GET /api/career/opportunity-priorities`: oportunidades ordenadas por indícios documentais; sem probabilidade de contratação.
- `PUT /api/evidence/{id}`: edição de evidência pertencente ao usuário, sem elevar automaticamente o status de verificação.
- `DELETE /api/tasks/{id}`: remoção autorizada de tarefa.
- Frontend: onboarding, resumo semanal, ranking explicável, edição de evidência e exclusão de tarefas.
- Segurança: testes de autenticação e isolamento entre duas contas para os novos endpoints.

## Resultados realmente executados
- `python -m pytest -q`: **40 testes aprovados, 1 aviso de depreciação**, em 14,04 s.
- `python -m compileall -q production_api`: aprovado.
- `node --check production_api/web/app.js`: aprovado.
- Tentativa de smoke test Chromium: **BLOQUEADA** pelo ambiente; navegador retorna `127.0.0.1 is blocked / Your organization doesn't allow you to view this site`. Não afirmar E2E visual aprovado.
- Banco nos testes: SQLite descartável. Sem PostgreSQL real, Stripe sandbox ou implantação externa.

## Inventário funcional e lacunas, por perspectiva do cliente
| Jornada | Existe | Principal lacuna |
|---|---|---|
| Primeiro uso | Cadastro, login, checklist v9 | Importação autorizada de currículo/perfil, menor esforço inicial |
| Diagnóstico | Motor lexical, proveniência declarada, grafo | Semântica e calibração com especialistas; revisão independente |
| Evidências | Rubrica documental, inventário, análise Python estática | Verificação de autoria e execução isolada ainda não homologadas |
| Oportunidades | Cadastro manual, prioridades documentais v9 | Vagas atualizadas por fontes autorizadas, filtros reais de salário/localização |
| Execução | Tarefas, candidaturas, resultados e check-ins | Lembretes e orientação de qualidade, sem sobrecarregar o usuário |
| Currículo/entrevista | Fluxos Premium existentes | Avaliação de qualidade com humanos e testes de usabilidade |
| Pagamentos | Integração Stripe em código | Testes reais de ciclo, idempotência concorrente, chargebacks, conciliação |
| Privacidade | Exportação, exclusão, isolamento básico | Revisão jurídica LGPD, retenção, incidentes, recuperação de conta |
| Infraestrutura | Docker, migrations e health checks | PostgreSQL real, backup/restore, observabilidade externa e teste de carga |
| Navegador | UI JavaScript disponível | E2E visual bloqueado neste ambiente; testar em CI acessível |

## Segurança e riscos residuais
- Rate limit de autenticação apenas local ao processo; exige proteção distribuída antes do lançamento.
- Tokens no sessionStorage são acessíveis a scripts da origem; CSP reduz risco, mas não elimina XSS. Avaliar cookies HttpOnly/SameSite com proteção CSRF.
- Regras de avaliação técnica são heurísticas; nenhuma evidência declara competência comprovada automaticamente.
- Execução de código desconhecido deve permanecer desativada até worker isolado auditado.
- Falta verificação de e-mail e recuperação de senha segura.
- Importação de links/repositórios exige consentimento, allowlist e mitigação SSRF.

## Veredito de produto
**Melhoria de experiência implementada, não homologação comercial.** O usuário agora recebe orientação de entrada e uma razão para voltar semanalmente. Não existem medições reais de satisfação, retenção ou disposição a pagar. R$299/mês permanece hipótese de preço; não abrir cobrança pública antes dos gates de infraestrutura, segurança, Stripe e testes de clientes.

## Gates para 9/10
1. E2E em Chromium/Firefox com jornadas completas e acessibilidade.
2. PostgreSQL + Alembic com concorrência, backup e restauração demonstrados.
3. Stripe test mode com duplicatas, eventos fora de ordem, falha, cancelamento e reembolso.
4. Segurança independente, rate limit distribuído, recuperação de conta e política LGPD.
5. Estudo com 10–20 usuários consentidos; medir ativação, tempo até valor, retorno D7 e avaliação de utilidade.
6. Revisão cega de recomendações e evidências por profissionais; quantificar erros, discordâncias e danos potenciais.
