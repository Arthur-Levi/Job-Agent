# Job Agent — Backlog mestre de lançamento e valor comercial
Atualizado: 2026-10-26. Branch: feature/d2681-railway-docker.

## Objetivo
Consolidar pendências técnicas, UX/UI, segurança, comercialização e novas melhorias de utilidade e valor percebido dos planos R$149/R$299, sem duplicar tarefas. **Planejamento, não implementação.** Não anunciar funções futuras como prontas.

## Critérios comerciais e métricas
- Público inicial: profissionais juniores de tecnologia/dados.
- R$149 Professional: hipótese de preço, validar por entrevistas e clientes pagantes. R$299 Executive: NÃO liberar antes da entrega de diferenças reais e validação de disposição a pagar.
- Rubrica UX anterior: 64,65% no v13; estimativa subjetiva para v14 ~71,5%, não métrica de conversão. Objetivo interno 85% com testes reais; não alegar nível alcançado.
- Metas propostas para primeiros testes: >=4/5 usuários completam onboarding sem ajuda; medir tempo para primeiro resultado, ativação, churn, conversão, CAC, solicitações de suporte e uso repetido.
- Não prometer colocação no mercado, verificação automática de competências nem autonomia irrestrita em portais.

## P0 — Portões obrigatórios antes de beta com dados reais
| ID | Atividade pendente | Critério de aceite | Dependências |
|---|---|---|---|
| JA-P0-01 | Encerrar D2.6.9-A com evidências auditáveis (log completo da regressão HTTP, prova da conexão ao banco descartável, smoke e teste visual de desktop/mobile) | Evidências reproduzíveis, sem segredos; dashboard/diagnóstico sem sobrescrita, navegação e formulários utilizáveis | v14 atual |
| JA-P0-02 | Estabilidade de containers e PostgreSQL: diagnosticar RWLayer e definir estratégia de recuperação sem tocar no volume recuperado | Plano documentado, ambiente de teste reproduzível e prova de não impactar jobagent-postgres-recovered | backup prévio |
| JA-P0-03 | Backup criptografado externo + restauração em banco descartável e procedimento de recuperação | Backup verificável, restore exercitado, integridade de dados e RPO/RTO documentados | escolha de armazenamento seguro |
| JA-P0-04 | Deploy Railway com banco independente, migrations, HTTPS e observabilidade | Health live/ready 200, assets 200, logs, restart e rollback testados; segredos fora do repositório | P0-02/03 |
| JA-P0-05 | Privacidade/LGPD e controles de segurança (termos, exclusão/exportação, controle de acesso, logs sem dados pessoais, limites de taxa, sessões, incidentes) | Revisão de fluxos de dados, consentimentos/avisos, políticas publicadas e testes de isolamento | deploy seguro |
| JA-P0-06 | Jornada essencial de beta (registro/login, import PDF/DOCX, preview, confirm, diagnóstico, tarefas/vagas, billing) testada ponta a ponta | Fluxos concluídos por 4 de 5 participantes do ICP sem ajuda; sem bloqueadores P0 | P0-01 a P0-05 |

## P1 — Produto v15: facilidade, automação e retenção
| ID | Atividade | Critério de aceite | Impacto |
|---|---|---|---|
| JA-P1-01 | Onboarding guiado com um próximo passo claro, orientação progressiva e retomar de onde parou | Menor tempo até primeiro resultado; usuário identifica ação principal sem ajuda | Facilidade |
| JA-P1-02 | Importação/revisão de currículo em cartões com resumos, edição progressiva, feedback inline e confirmação humana obrigatória | PDF/DOCX/TXT; zero publicação automática de fatos; teste de tempo/conclusão vs v14 | Facilidade, confiança |
| JA-P1-03 | Reduzir preenchimento repetitivo de vagas: extração assistida de URL/texto fornecidos pelo usuário, somente fontes e acessos autorizados | Prévia editável, confirmação antes de salvar, avisos sobre origem; sem scraping de portais proibido | Economia de tempo |
| JA-P1-04 | Navegação responsiva/teclado/leitor de tela (320, 375, 768, 1440px), menu compacto e WCAG AA | Todos os destinos acessíveis, foco visível, sem scroll lateral crítico | Usabilidade |
| JA-P1-05 | Robustez da UI: carregamento, estados de erro/sucesso contextuais, tratamento de requisições obsoletas e erro de billing não bloqueante | Fluxos toleram falha de API com mensagens específicas, sem botão inerte | Confiabilidade |
| JA-P1-06 | Dashboard orientado a resultados e próximas ações; progresso real, histórico e resumo semanal útil | Resultado e próximo passo visíveis na primeira tela; sem métricas ou chances fictícias | Retenção |
| JA-P1-07 | Plano semanal personalizado baseado em evidências, requisitos e disponibilidade; registro de execução | Ações específicas com origem explicada; retorno semanal utilizável | Utilidade recorrente |
| JA-P1-08 | Medição de funil e comportamento com privacidade (ativação, preview→confirm, diagnóstico→ação, uso semanal, churn) | Painel simples com coortes e telemetria sem currículos/tokens/segredos | Priorização |
| JA-P1-09 | Posicionamento e oferta Professional R$149: comparação Free x Professional, exemplos reais, limites, preço e cancelamento antes do checkout | Usuário consegue explicar benefícios; teste de entendimento e disposição a pagar | Valor percebido |
| JA-P1-10 | Conectar currículo fundamentado e análise de requisitos ao valor de cada candidatura; templates claros por vaga | Saída editável e rastreável, sem inventar experiência, comparação testada com usuários | Diferenciação |
| JA-P1-11 | Marketing landing page, demonstração transparente, casos autorizados, FAQ e canal de suporte | Visitante compreende produto em até 30 segundos (meta de teste), sem promessa de emprego | Aquisição |
| JA-P1-12 | Checkout Stripe/test mode, upgrade/downgrade, webhook idempotente, cancelamento/portal e falhas de cobrança | Fluxos e eventos simulados testados ponta a ponta sem cobrança real | Monetização |
| JA-P1-13 | Recrutamento de 5 beta, entrevistas e suporte estruturado; medir abandono/valor percebido | Feedback consentido, evidências de utilidade, taxa de ativação e teste de preço | Validação |

## P2 — Executivo R$299 e expansão condicionada a provas
| ID | Atividade | Critério de aceite / condição |
|---|---|---|
| JA-P2-01 | Definir diferenciação Executive R$299 (triagem assistida, entrevistas contextualizadas, analytics de busca, suporte prioritário) | Funcionalidades implementadas e testadas, SLA/custo conhecidos e usuários dispostos a pagar R$299; não vender antes |
| JA-P2-02 | Automações multicanal autorizadas por fonte/operação com confirmação humana, respeito a termos e opção de desligar | Segurança, privacidade, audit trail, nenhuma candidatura não autorizada |
| JA-P2-03 | Reduzir custo por usuário (IA, infra, aquisição e suporte); preços R$79/99/149 testados se necessário | Margem, retenção e conversão reais sustentam escolha do preço |
| JA-P2-04 | Experimentos A/B de identidade visual, microinterações e densidade de informação | Efeito medido em conclusão/retorno, não só preferência visual |
| JA-P2-05 | Pilotos B2B e novos segmentos (administrativo/logística) após validação de ICP inicial | Demanda e qualidade de recomendações comprovadas antes da expansão |

## Sequência recomendada
1. **D2.6.9-A fechamento documental** → P0-01.
2. **Infraestrutura, backup e segurança** → P0-02 a P0-05 (paralelo ao refinamento de UX v15).
3. **v15 de alto impacto** → P1-01/02/04/05/06/09.
4. **Economia de tempo e diferenciação** → P1-03/07/10.
5. **Testes com 5 usuários e pagamento em modo de teste** → P0-06, P1-08/12/13.
6. **Beta controlado** → landing e primeiros clientes, após portões P0.
7. **Executive R$299** somente após JA-P2-01 validado.

## Status e cuidados
- Código v14, correção de diagnóstico e regressão HTTP informada como bem-sucedida pelo operador já documentados no checkpoint D2.6.9-A; não declarar testes de navegador/CI concluídos sem registros.
- Banco de produção/recuperado: volume `jobagent-postgres-recovered` intocável para testes destrutivos.
- Não alterar preço, módulos, dados, tokens ou deploy por registrar este backlog.
