# JOB AGENT — OPERAÇÃO PRIMEIRO VALOR (inspirada em princípios de foco e execução)

Status: **plano de implementação**, sem código de produto alterado e sem merge. Data: 2026-10-30.

## Tese de produto
Público inicial: profissional júnior de dados/tecnologia procurando recolocação. Proposta testável: transformar currículo confirmado pelo candidato em diagnóstico rastreável e 3 próximas ações úteis, sem promessa de emprego. Preço candidato: R$ 299/mês, **não validado**.

### Escopo único (vertical slice)
1. Entrada: upload/colagem de currículo -> `/api/import/resume/file-preview` ou `/api/import/resume/preview`.
2. Conferência: confirmar fatos/corrigir duplicidades -> `/api/import/resume/confirm`, `/api/master-profile`, `/api/fact-ledger`.
3. Primeiro valor: `/api/diagnostic/fact-grounded`, `/api/diagnostic/priority-actions`, `/api/journey/first-result`.
4. Plano e retorno: `/api/tasks`, `/api/career/checkins`, `/api/career/weekly-brief`.
5. Pagamento só depois da homologação SEC-05; não bloquear diagnóstico gratuito sem experimento de valor.

## Inventário existente verificado no código
- Backend `production_api/main.py` já possui importação preview/confirm, perfil mestre, Fact Ledger, contradições, diagnóstico fundamentado, priority actions, first result, tarefas, checkins, Stripe endpoints, export e exclusão.
- Frontend `production_api/web/app.js` já possui módulos `importResume`, `masterView`, `ledgerView`, `diagnostic`, `tasks`, `dashboard`; código grande e acoplado.
- **Não criar novo backend, novo banco, novo motor de IA nem novos serviços antes de provar falta real**.

## Backlog priorizado
| ID | Implementação | Critério de aceite |
|---|---|---|
| FOCUS-00 | Consolidar branches SEC-02/03/04 + Q2.2 em branch de integração isolada | Testes existentes verdes no backend real descartável, sem merge main; diff revisado |
| FOCUS-01 | UI de onboarding em 3 passos (enviar, conferir, receber análise) reaproveitando endpoints | Usuário conclui sem navegar por módulos auxiliares; upload e colagem; erros/retry; acessibilidade mobile |
| FOCUS-02 | Resultado inicial em uma tela | Exibe diagnóstico com 3 principais lacunas, evidência associada ou sinal explícito 'não verificado', 3 ações e CTA para tarefa |
| FOCUS-03 | Corrigir extração sem alucinação | Teste 10 currículos sintéticos diversos, sem inventar cargo/empresa/datas; erros e duplicidades visíveis e corrigíveis |
| FOCUS-04 | Medição mínima e consentida | Registrar eventos sem texto de currículo, nome, email, token ou identificador direto em logs analíticos; definição de início/conclusão e tempo até primeiro valor; revisar LGPD |
| FOCUS-05 | Feedback contextual | Após diagnóstico: útil? qual recomendação incorreta? (opcional); tratar feedback privado e retenção definida |
| FOCUS-06 | Ciclo semanal | 3 ações priorizadas, tarefa concluída, check-in e progresso sem promessas ou ranking enganoso |
| FOCUS-07 | Teste com 5 pessoas voluntárias | Observar conclusão, compreensão, benefício, confiança e motivo de não pagamento; sem manipular depoimentos |
| FOCUS-08 | Piloto comercial | 10 entrevistas, 3 testes de disposição a pagar, meta posterior de 10 pagantes que renovam |

## Indicadores e critérios
- `activation_rate` = usuários com primeiro diagnóstico factual concluído / usuários que iniciaram upload (usar janela de 7 dias por coorte, distinguir falhas).
- `time_to_first_value` = tempo entre início do upload e primeira análise mostrada, com mediana e p90.
- `evidence_integrity` = 0 fatos inventados nos currículos sintéticos de regressão, registrar correções sem atribuir fatos não declarados.
- `diagnostic_helpfulness` = votos úteis/total de respostas, exibir tamanho da amostra.
- `weekly_return` = proporção que retorna para executar uma ação em 7 dias (não supor meta alcançada).
- `paid_renewal` = clientes renovados / clientes elegíveis a renovar; precisa cobrança homologada.

## Gates antes do primeiro beta pago
SEC-05 Stripe test mode; SEC-06 privacidade (consentimento, retenção, eliminação, exportação); SEC-07 backups + restauração; integração frontend/backend, acessibilidade e segurança. SEC-02/03/04 têm PASS apenas no escopo dos cenários testados.

## Ordem recomendada
- Sprint A: checkpoint/integração e SEC-05/06/07 mínimos; não ativar pagamentos antes dos gates.
- Sprint B: FOCUS-01 a FOCUS-03, UX e teste real do primeiro valor.
- Sprint C: FOCUS-04 a FOCUS-07, entrevista e experimento assistido com usuários.
- Após evidência: decidir se proposta R$299/mês se sustenta; expandir recursos somente a partir do aprendizado.

## Disciplina de entrega
- Cada mudança: hipótese + diff pequeno + teste automatizado + gravação de evidência + rollback.
- Branch isolada; não modificar `/workspaces/Job-Agent` original, `main`, PR #2 ou bancos originais.
- Não versionar `sec04-env.sh`, `.env`, senhas, tokens, banco/dumps.
- Reutilizar endpoints e modelos atuais; não refatorar `app.js` inteiro antes de validar onboarding.
