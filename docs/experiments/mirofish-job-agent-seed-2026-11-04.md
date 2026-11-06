# MiroFish × Job Agent — pacote de cenário sintético (2026-11-04)

> **Somente para simulação comportamental.** Os valores não são métricas reais, previsões estatísticas nem resultados do MiroFish. Não enviar currículos, usuários, tokens nem dados privados ao MiroFish/Zep/LLM.
> Motor externo: https://github.com/666ghj/MiroFish (AGPL-3.0). Este arquivo é um *seed* para upload manual na interface do MiroFish, não um componente integrado ao Job Agent.

## Produto em teste
Job Agent é um SaaS brasileiro de apoio à carreira com preço comercial planejado de R$ 299/mês. Seu objetivo é oferecer uma jornada fundamentada: importar currículo com segurança; revisar e confirmar fatos no Master Profile e Fact Ledger; diagnosticar competências/lacunas de acordo com objetivos profissionais; gerar currículo verificável/exportável e comparar evidências reais com requisitos de vagas; depois acompanhar candidaturas, entrevistas e evolução profissional.

**Estado técnico em 2026-11-04:** segurança de currículos reais NÃO liberada, Gate 1 NO-GO e rota 503 CV_SANDBOX_REQUIRED. As funções de jornada completa e retenção constam de backlog, não são todas oferecidas ao público. Simular uma possível oferta futura, nunca declarar lançamento realizado ou eficácia comprovada.

## Mercado e personas (inteiramente fictícias)
- Candidata administrativa júnior: renda limitada, procura vaga em logística/administração; compara preço com serviços gratuitos; teme cobrança recorrente sem retorno.
- Profissional de dados júnior: deseja R$ 4 mil–6 mil/mês, entende parte da proposta de matching, exige evidências e transparência.
- Pessoa em transição profissional: currículo fragmentado, insegurança com dados pessoais e confiança em IA.
- Candidato empregado que busca promoção: valor pode depender de desenvolvimento contínuo pós-contratação.
- Candidato contratado: tende a cancelar se o produto não ajudar no novo trabalho.
- Criador de conteúdo de currículo/empregabilidade: 5–50 mil seguidores como faixa exploratória, alcance e engajamento não garantidos; decide pela transparência, reputação, cachê e desempenho.
- Criador de tecnologia/carreira: público mais técnico; preocupação com promessas exageradas e confiabilidade.
- Recrutador/gestor de RH: questiona scores opacos, aderência às vagas, alucinações e alegações de aprovação ATS.
- Profissional de privacidade: exige LGPD, retenção, consentimento, segregação e revisão das promessas.

## Estratégia comercial hipotética
Preço R$ 299/mês, dois microcriadores no início. Expansão hipotética de criadores por mês: Jan 2, Fev 3, Mar 5, Abr 8, Mai 12, Jun 18, Jul 25, Ago 34.
Aquisições pagas hipotéticas: Jan 4, Fev 8, Mar 15, Abr 28, Mai 48, Jun 72, Jul 112, Ago 170.
Churn hipotético 5% ao mês sobre assinantes do começo do período. Não confundir essas entradas com resultados observados.
Contrato hipotético: R$ 250 fixos/criador/mês + R$ 60 por assinante pago atribuído. Não garantido por negociação.
Concorrência: plataformas de vagas, LinkedIn, InfoJobs, geradores de currículo e recursos gratuitos. Não inventar preços atuais, tendências ou dados de mercado.

## Hipóteses adversariais que a simulação deve explorar
1. A maioria dos usuários vê utilidade, mas considera R$ 299 alto em relação à renda e alternativas gratuitas.
2. A clareza de evidências, correção humana e exportação pode melhorar confiança; qualquer alucinação quebra confiança.
3. Depoimentos e criadores geram descoberta, mas nem todos os cliques são qualificados.
4. Aquisição pode subir enquanto retenção cai; não confundir MRR teórico com caixa.
5. Após conseguir emprego, o usuário pode cancelar; First 90 Days/Growth/Mobility são hipóteses de retenção, ainda não comprovadas.
6. O Gate de segurança pode atrasar o lançamento; nenhum usuário real deve importar CV até a aprovação.
7. Influenciadores podem abandonar campanhas por baixa remuneração ou por risco reputacional.
8. Recrutadores podem rejeitar conteúdo artificial ou afirmações de matching sem justificativa.

## Cenários de comparação
**A: Base cautelosa:** 2 criadores iniciais, expansão lenta, churn 10–12%; conversão por criador baixa; sem funções pós-contratação.
**B: Base experimental:** expansão condicionada a 10 renovações; churn hipotético 7%; criadores são cortados por CAC e retenção; currículo e diagnóstico fundamentados.
**C: Agressivo:** expansão 2→34 por agosto, churn 5%, aquisições programadas no plano acima; teste de fragilidade a preço, reputação, custo e capacidade.
**D: Choque:** falha no parser/sandbox, 3 semanas de indisponibilidade e recusa de divulgar CV; crescimento pausado, foco em transparência e correção, nunca bypass de segurança.

## Saídas solicitadas ao ReportAgent
- Narrativa separada para candidato, criador, RH e profissional de privacidade: objeções, confiança, abandono e recomendações.
- Matriz de eventos/objeções com frequência simulada, sem alegar que representa populações reais.
- Diferenças A/B/C/D; pontos de ruptura e sinais precoces; evitar "previsão garantida".
- Sugestões testáveis de pricing, onboarding, prova de valor, jornada Fact Ledger e retenção; sinalizar dependências não implementadas.
- Plano de experimentos reais futuro com N, CAC, primeira renovação, churn, qualidade de diagnóstico e reclamações; não substituir dados observacionais por simulação.

## Regras de segurança e integridade do experimento
Só participantes, eventos e documentos sintéticos. Não conectar MiroFish ao GitHub privado, PostgreSQL do Job Agent, sistemas de pagamento, dados de RH, currículos reais ou à rota de produção. Operar em instância separada. Não publicar token LLM/Zep nos logs, prompts ou Git.
