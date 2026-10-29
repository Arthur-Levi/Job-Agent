# Job Agent — Backlog de excelência pós-Due-Diligence
Data: 2026-10-29 | Estado inicial: PLANEJADO, não implementado.
Origem: avaliação simulada de comitê de investimento, inspeção do repositório e evidências Q1/Q2.2.
**Regras:** não alterar `main`, bancos e containers originais; não mesclar PR #2 automaticamente; toda implementação em branch/worktree isolada, testes comprovados antes de merge. O PR #2 permanece draft. Não chamar mock de integração real. Sem funcionalidade fictícia em marketing.

## Definições
P0 = bloqueia beta público/pagante; P1 = necessário para validação de 10 pagantes e primeiras renovações; P2 = depois de evidência de uso; P3 = hipótese de expansão. Cada item requer responsável, evidence URL, status (TODO/DOING/BLOCKED/PASS), data e confirmação por teste ou pesquisa. Qualquer "PASS" exige artefato verificável.

## Fase A — segurança, verdade operacional e homologação (P0)
| ID | Item | Entrega e critério de aceitação |
|---|---|---|
| SEC-01 | Q2.2 — revisão final | Inspecionar captura **q22-feedback-mobile-375.png** (Q1 não substitui); revisar estados erro/sucesso/retry, responsividade, acessibilidade teclado/aria-live, navegar com ações que desmontam botão; documentar PASS/FAIL e manter PR draft até aprovação |
| SEC-02 | Autorização e isolamento A/B | Banco **descartável**: duas contas fictícias; testar leitura/gravação/alteração/exclusão de entidades, exports, premium; respostas 401 e 403/404 corretas; sem vazamento cruzado; cobertura automatizada e registro sem PII |
| SEC-03 | Sessões e privacidade local | Testar logout, expiração, troca de senha/conta, requisições concorrentes e drafts em sessionStorage; avaliar risco XSS/token e mitigação; nenhuma informação privada da conta A visível na B |
| SEC-04 | Proteção contra abuso | Revisar rate-limit por IP em memória, configurar defesa distribuída no gateway para produção, limites de corpo/upload, TLS, headers, logs redigidos e métricas; testes 429 e cargas adversariais com contas fictícias |
| SEC-05 | Stripe end-to-end | Stripe *test mode*: checkout, retorno, webhook assinatura/duplicação/fora de ordem, trial/ativo/inadimplente/cancelado, portal e revogação; contabilização e reconciliação verificadas; nenhum pagamento real em homologação |
| SEC-06 | Direitos e exclusão de dados | Testar export, alteração de senha e exclusão com conta descartável; explicar bloqueio de exclusão com assinatura; definir política LGPD, retenção, dados de currículo, termos, suporte e cancelamento |
| SEC-07 | Backup e recuperação | Comprovar processo de backup, restauração em banco descartável, RPO/RTO operacionais e segredo fora do Git; documentação sem afirmar cópia externa existente sem evidência |
| OPS-01 | Documentação canônica | Atualizar README/runbook para esclarecer legado D1 sem auth versus `production_api` autenticado; procedimentos de deploy, migrations, variáveis de ambiente, rollback e endpoints de health; validação por operador que não conhece a base |
| OPS-02 | Confiabilidade em staging | Instrumentar erros, p95 de endpoints-chave, falhas de importação, disponibilidadade e limites de carga; rodar teste de carga não destrutivo em staging, sem prometer capacidade para 500 pagantes antes de medir |
| OPS-03 | Integridade dos testes | Reorganizar matriz static/mock/integration/E2E/production; CI com gates, resultados sem dupla contagem; bloqueio de merge se regressão falhar |

## Fase B — valor em minutos, UX e diferenciação (P1)
| ID | Item | Entrega e critério de aceitação |
|---|---|---|
| UX-01 | Onboarding 3 passos | Fluxo principal **Perfil → Vaga-alvo → Plano de ação**, módulos avançados progressivos; teste com usuários novos; conclusão sem explicação do operador |
| UX-02 | Primeiro resultado rápido | Importar CV e inserir vaga -> diagnóstico útil e fundamentado antes de exigir cadastro extensivo de evidências; medir tempo até primeira percepção de valor e abandono |
| UX-03 | Mobile premium | Reduzir menu e redundância de títulos, equilibrar abas, hierarquia visual e ação principal, foco/touch targets, 320/375/768px; screenshot review + teste de teclado |
| UX-04 | Feedback persistente | Notificações de sucesso/falha após `show()`/troca de tela; preservar input em falhas, impedir duplo clique, mensagens semanticamente corretas e aria-live; browser teste |
| UX-05 | Clareza e honestidade | Microcopy em português simples; diferenciar dados autodeclarados, verificações e hipóteses; nunca exibir probabilidade de emprego sem modelo validado |
| PROD-01 | Fact Ledger comprovável | Provar origem/correção/deduplicação/contradição de fatos com currículos heterogêneos; nenhuma informação inventada; cobertura com fixtures de CVs sintéticos |
| PROD-02 | Diagnóstico explicável | Cada lacuna e sugestão vinculada a requisito de vaga e fato/evidência; justificar limites; avaliação por usuários reais |
| PROD-03 | Persistência legítima | Importação -> revisão -> confirmação -> relogin -> dados consistentes; separar preview de persistência; testes com PostgreSQL descartável |
| ENG-01 | Modularizar app.js | Quebrar arquivo `production_api/web/app.js` de ~54k chars em módulos por domínio gradualmente; snapshots/contratos e parity de behavior antes/depois; sem reescrita arriscada |
| ENG-02 | QA de usabilidade e acessibilidade | Rotas críticas em teclado, leitores de tela, contraste, erros, navegação e estados vazios; roteiro E2E replicável |

## Fase C — aquisição, monetização e renovação (P1)
| ID | Item | Entrega e critério de aceitação |
|---|---|---|
| MKT-01 | Nicho e promessa | Público júnior tech/dados, pesquisa de dor real; uma promessa mensurável sem garantir emprego: lacunas de vaga justificadas por evidência |
| MKT-02 | Diferenciação defensável | Comparar experiências e recursos de concorrentes atuais sem alegar unicidade; demonstrar 3 benefícios percebidos do Fact Ledger + diagnóstico |
| MKT-03 | Landing e demo | Página de oferta com benefício imediato, demonstração de 5 minutos e CTA, transparência de preço e privacidade, provas reais (sem depoimentos fictícios); 5 testes observados |
| MKT-04 | Preço e disposição a pagar | Testar a hipótese R$299 com entrevistas e ofertas controladas; comparar objeções/alternativas; não alterar preço sem evidência |
| SALES-01 | Primeiros 10 | Registrar fonte, contato, conversa, demo, objeções, pagamento verificado, ativação e CAC; 10 clientes reais pagando, sem auto-compra ou promessas enganosas |
| SALES-02 | Primeiras 10 renovações | Coorte de 10 com primeiro ciclo de renovação comprovado; motivos de continuar/cancelar; suporte e reembolsos registrados |
| SALES-03 | Funil e canal | Taxas por canal (contato→resposta→demo→pago→renovou), custos/tempo; escalar somente canal com evidência de eficiência |
| FIN-01 | Unit economics | Receita recebida vs MRR, margem de contribuição, taxas, infra/IA, impostos, CAC, prazo de retorno, churn/coortes; hipótese de lucro separada de realizado |
| FIN-02 | Confiança comercial | Termos claros, cobrança, cancelamento acessível, suporte, transparência de limites, privacidade e exportação |
| RET-01 | Churn funcional | Entrevistar quem saiu **inclusive por ter conseguido emprego**; separar churn saudável e insatisfação; medir recompra/referência |
| RET-02 | Valor contínuo | Só após entrevistas: prototipar desenvolvimento de carreira, evolução, promoção e novas candidaturas; 5+ clientes aceitando usar após conseguir emprego antes de construir |
| SCALE-01 | Preparação 100–500 | Depois de coortes e aquisição validadas: testes de carga, suporte, automação segura, capacidade operacional, metas mensais por ganho líquido e orçamento |

## Sequência de execução (não fazer tudo simultaneamente)
**Sprint 0 — bloqueios (imediato):** SEC-01/02/03, PROD-03, OPS-01. Sem beta pagante antes dos P0 de cobrança, privacidade, limites e recuperação.
**Sprint 1 — primeiro valor:** UX-01/02/03/04/05 + PROD-01/02, com avaliação de usuários.
**Sprint 2 — primeiros compradores:** MKT-01/02/03/04, SALES-01, FIN-01 (entrevistas e demos podem começar antes do beta pagante, sem cobrar).
**Sprint 3 — renovação:** SALES-02/03, RET-01, FIN-02.
**Sprint 4 — escala controlada:** OPS-02/03, ENG-01/02, RET-02 e SCALE-01; segurança/ops P0 devem estar concluídas antes da venda pública.

## Métricas mínimas, sem números inventados
Ativação = usuários que atingiram primeiro diagnóstico útil / novos usuários; tempo até primeiro valor; conversão demo→pago; cohort de renovação 30/60/90 dias; churn por motivo; CAC por canal; margem de contribuição; P95/erro; taxa de incidentes e tempo de resposta de suporte.

## Critérios de investimento da comitiva
NO-GO hoje. Reconsiderar somente com beta seguro, 10 clientes realmente pagantes e 10 renovações verificadas, evidência de produto simples, política de dados confiável, e caminho econômico de aquisição. Para investimento relevante: 50+ clientes, coortes multiciclo e CAC sustentável. 400–500 clientes até agosto 2027 permanece meta aspiracional, não previsão.

## Segurança de execução
Não fazer merge do PR #2, não modificar `main`, bancos `jobagent-postgres-v2`/`recovered` nem volumes originais. Este arquivo é backlog, NÃO implementação. Cada melhoria deve gerar PR próprio, CI, evidência, checklist de aceite e revisão antes da integração.
