# Job Agent — Auditoria competitiva UX/UI v14 (2026-10-25)

## Escopo e limitações
Análise heurística sobre `production_api/web/index.html`, `style.css`, `app.js` da branch `feature/d2681-railway-docker`, comparando fluxos publicados de Teal, Huntr, Simplify e Jobscan. Pontuações são julgamentos qualitativos, **não** analytics reais, testes de usabilidade ou benchmarks quantitativos de concorrentes. Sem screenshot renderizado, inspeção de contraste ou testes em dispositivos reais. Nenhum dado real de usuário foi usado.

## Rubrica ponderada e limiar
| Critério | Peso | Nota inicial | Contribuição |
|---|---:|---:|---:|
| Identidade visual | 15% | 82 | 12.30 |
| Valor na primeira impressão | 15% | 65 | 9.75 |
| Navegação e arquitetura da informação | 15% | 62 | 9.30 |
| Onboarding e importação | 15% | 72 | 10.80 |
| Usabilidade móvel | 10% | 52 | 5.20 |
| Feedback e estados | 10% | 58 | 5.80 |
| Valor Premium | 10% | 55 | 5.50 |
| Motivação e recorrência | 10% | 60 | 6.00 |
| TOTAL | 100% | **64.65** | **64.65** |

Regra: qualquer dimensão com nota <70 deve entrar em backlog de melhoria; nota total <70 impede declarar experiência pronta para expansão. O limiar é gerencial, não significa 70% de conversão.

## Referências comparativas verificadas
- Teal: visão do Job Tracker, agrupamento e mudança de status https://help.tealhq.com/en/articles/9524944-exploring-the-dashboard
- Simplify: dashboard orientado a recomendações, metas e atividade https://simplifyjobs.featurebase.app/en/help/articles/6390631-navigate-your-dashboard
- Simplify: tracker e filtros https://help.simplify.jobs/help/articles/2140179-using-the-job-tracker
- Huntr: navegação e currículo https://help.huntr.co/en/articles/10393367-your-huntr-dashboard
- Jobscan: análise de currículo e recomendações https://www.jobscan.co/resume-scanner

## Achados confirmados no código
1. Página anônima renderizava sidebar de workspace (sidebar fora da seção autenticada). Solução v14: classe `is-public`, barra lateral oculta antes do login.
2. Media query em 720px definia `.sidebar nav .nav-more{display:none}`, eliminando acesso móvel às ferramentas avançadas. Solução v14: reexposição por grid e `details` expansível.
3. `input` global `width:100%` afetava `checkbox`; solução v14 aplica largura automática a checkbox/radio.
4. Dashboard continha onboarding estático e orientação dinâmica ao mesmo tempo. Solução v14: ao detectar onboarding concluído, oculta `.quick-start`.
5. Mensagem da tela pública era institucional, mas pouco objetiva. Solução v14: texto anuncia currículo, preparação e ações concretas.

## Backlog ainda não implementado
- P0: validar interface responsiva em dispositivos reais a 320/375/768/1440 px; keyboard-only e leitor de tela; WCAG AA; testes de foco de `details`.
- P1: feedback inline e acessível de erros/sucessos, evitar status global fora da viewport, tratar respostas concorrentes de `show()`.
- P1: exibir amostra real das vantagens do Premium e preço antes do checkout; teste de clareza com cinco usuários.
- P1: reduzir formulário de confirmação de currículo com resumos e edição progressiva, sem abrir mão de confirmação humana.
- P1: distinguir páginas públicas e autenticadas com estados de carregamento; evitar flash de layout ao iniciar a sessão.
- P1: tornar navegação móvel compacta/colapsável após testes, preservando acesso a todos os módulos.
- P2: testes controlados de nova paleta e densidade visual, com métricas de conclusão e não só opinião.
- P2: reduzir digitação repetida de vagas por mecanismos autorizados; nunca aplicar em portais sem permissão.

## Gates de aprovação antes do beta
- Testes de regressão da API e smoke HTTP de HTML/CSS/JS.
- Fluxo real: cadastro → currículo PDF/DOCX → preview → confirmação → diagnóstico → próxima ação.
- Acesso a cada aba no desktop e mobile, sem scroll horizontal indevido nem recursos ocultos.
- Cinco participantes do ICP: pelo menos quatro concluem a jornada sem ajuda; medir tempo, tarefas, erros e desistências.
- Painel semanal de ativação, retenção, conversão, pagamentos, feedback e acessibilidade.
- Nenhuma deploy para produção antes de CI, staging e comparação visual.
