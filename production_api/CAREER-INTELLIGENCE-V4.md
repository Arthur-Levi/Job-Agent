# Job Agent v4 — Career Intelligence Engine

## Implementado
- Endpoint autenticado `GET /api/intelligence`, escopo exclusivo do usuário autenticado.
- Análise determinística de requisitos por vaga, referências de evidências e justificativas.
- Priorização por recorrência de requisito nas vagas; máximo de três ações concretas.
- Distinção rigorosa entre indício textual e competência comprovada; nenhuma previsão de contratação.
- Medidas de qualidade dos dados: vagas com requisitos, evidências com URL e requisitos com indícios.
- Visão unificada no frontend com ações que podem ser convertidas em tarefas.
- Testes de correspondência, falso positivo, prioridade, estado vazio e isolamento entre contas.

## Limitações importantes
- O mecanismo não acessa URLs, não verifica autoria, documentos, competências ou veracidade das vagas.
- O matching lexical é conservador e pode produzir falsos positivos e negativos; a priorização não é baseada em impacto causal demonstrado.
- Não foi implementado um modelo de linguagem, embeddings, extração automática de vagas, simulações avaliadas ou validação de salário.
- Testes automatizados locais com SQLite não substituem PostgreSQL, Stripe, navegador real e auditoria externa.
- O sistema ainda não é homologado para cobrança pública.

## Próximos incrementos com maior valor
1. Revisão e classificação humana das evidências (autoria, escopo, qualidade, fonte).
2. Extração estruturada de requisitos de vagas autorizadas, com citação do trecho original.
3. Histórico longitudinal de diagnósticos e resultados de candidaturas com atribuição de mudanças.
4. Avaliação de recomendações em conjunto rotulado por especialistas e usuários.
5. Homologação de PostgreSQL, Stripe sandbox, E2E de navegador, restauração de backup e controles de segurança.

## Execução de testes
`cd production_api && python -m pytest -q tests/`

Os requisitos e a pontuação exibida são heurísticos; não devem ser divulgados como probabilidade ou competência verificada.
