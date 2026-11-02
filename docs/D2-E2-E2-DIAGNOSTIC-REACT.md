# D2-E2.E.2 — Diagnóstico rastreável + React

**Escopo:** interface React autenticada, recomendações específicas de revisão dos registros, explicação por ID de Fact Ledger, e testes unitários + jornada real com dados sintéticos.

- A rota protegida `/career/diagnostic` consome `GET /api/v1/career/diagnostic`. Links para Fact Ledger e importação.
- Cada categoria apresenta apenas fatos ativos documentados, com `fact_id` e grau de verificação. A ausência de um registro não é interpretada como ausência de habilidade.
- Cada recomendação carrega tipo, prioridade, próximo passo e IDs de evidência. Recomendações relativas a organização e datas **não** prometem edição desses campos pela interface atual (correção textual de descrição apenas).
- Não calcula pontuação de empregabilidade ou chances de aprovação, não inventa experiências nem cria fatos ao consultar.
- A suíte React testa cobertura, ausência de registros, evidências, erros e nova tentativa. O Chromium com backend e PostgreSQL descartável verifica a navegação real ao diagnóstico depois da importação.
- **Sem liberação de produção:** `CV_SANDBOX_REQUIRED` ativo, broker de sandbox e quotas distribuídas ainda não homologados; nenhum dado real ou deploy.
- **D2-E2.F a seguir:** currículo e matching explicáveis com dados sustentados pelo Fact Ledger, após estes testes e revisão dos limites de provenance.

Este checkpoint não é autorização para beta; mantém PRs em Draft.
