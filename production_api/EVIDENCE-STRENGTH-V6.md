# Job Agent v6 — Evidence Documentation Strength

## Implementado
- Rubrica explicável, determinística e versionada para completude de documentação (0–100).
- Campos: contexto, contribuição pessoal, método, resultados e limitações.
- Histórico persistente por evidência; API de consulta e avaliação, visão agregada por conta.
- Isolamento por usuário; exportação de dados e exclusão por cascata.
- Interface web para preencher rubrica e ver última avaliação.
- Migration Alembic 0003, que reúne as duas branches 0002 existentes.
- Testes sintéticos comparativos, casos adversariais e regressão completa.

## Limitações obrigatórias
O número 0–100 não mede proficiência nem autenticidade, e **não deve ser apresentado como 'força técnica da evidência'**. A implementação não acessa links externos, não audita repositórios e não verifica identidades. Um texto falso detalhado pode receber 100/100 de documentação. Nenhum teste com candidatos reais foi realizado. Não há certificação de produção, nem homologação Stripe/PostgreSQL/Chromium nesta execução.

## Executar
`cd production_api && PYTHONPATH=. pytest -q`

Para produção, aplicar `alembic upgrade head` no PostgreSQL de homologação após backup e revisar migrations; nunca executar alterações destrutivas em banco real sem janela e procedimento de rollback.
