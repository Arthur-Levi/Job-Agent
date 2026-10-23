# Job Agent v5 — Career Evidence Graph + Adaptive Career Loop

## Implementado
- Nós: evidências profissionais e requisitos das vagas pertencentes ao usuário.
- Arestas persistentes: vínculo explícito entre evidência e requisito, com justificativa, autoria implícita e restrição de unicidade.
- Histórico: snapshots imutáveis de métricas, recomendações e explicação, com deduplicação de estado idêntico.
- Resultados: entrevistas, rejeições, ofertas, feedback e marcos relatados pelo usuário.
- Loop: delta em relação ao último check-in e priorização de revisão de rejeições.
- Isolamento por usuário em todos os endpoints; exportação e exclusão incluem as novas tabelas.
- UI: abas Mapa de evidências e Evolução.

## APIs
GET /api/career/graph; POST /api/career/graph/links; DELETE /api/career/graph/links/{id};
POST /api/career/outcomes; GET /api/career/outcomes;
POST /api/career/checkins; GET /api/career/checkins; GET /api/career/loop.

## Banco
Aplicar `alembic upgrade head` para criar as tabelas via migration 0002_career_graph.

## Limitações
- Não verifica autoria/proficiência; links e resultados são declarados pelo usuário.
- Não estima probabilidade de contratação ou causalidade entre ações e ofertas.
- Recomendação determinística; não há motor semântico ou avaliação independente.
- Check-ins deduplicados com métricas e recomendações idênticas; mudanças narrativas sem alterar esses elementos não criam novo snapshot.
- Testes automatizados SQLite não substituem homologação PostgreSQL, Stripe, navegador e segurança externa.
- Não habilitar vendas públicas sem concluir gates de produção existentes.
