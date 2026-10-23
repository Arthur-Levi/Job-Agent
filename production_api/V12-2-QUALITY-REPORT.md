# Job Agent v12.2 — Importação, duplicidade e recomendações

## Alterações
- DOCX: extração em ordem de parágrafos e tabelas; linhas de tabela mantêm colunas separadas por ` | `.
- PDF: tentativa de extração textual em modo layout; PDFs escaneados e layouts complexos ainda exigem revisão humana.
- Currículos: reconhecimento de seções numeradas, preservando separação conservadora de experiências e projetos.
- Duplicidades: comparador conservador por normalização, sobreposição de termos e similaridade de sequência. Registros idênticos/quase idênticos são ignorados; possíveis duplicatas geram HTTP 409, exigindo confirmação explícita antes da inclusão. Não é equivalência semântica por modelo de linguagem.
- Interface: mostra recomendações priorizadas, justificativas, origem e botão para a próxima ação na aba Diagnóstico. Após importação, abre o diagnóstico. Possíveis duplicatas exigem confirmação adicional.

## Validação realizada
- 56 testes em `production_api/tests/`: aprovados, 1 aviso de depreciação, SQLite de teste.
- `node --check` no JavaScript principal e `compileall` dos módulos Python alterados: aprovados.

## Limitações e riscos pendentes
- Não foi executado navegador real nem PostgreSQL real nesta etapa; a jornada E2E não está homologada.
- Currículos PDF multicoluna podem ter ordenação inadequada; documentos escaneados não recebem OCR.
- Heurísticas de duplicidade podem produzir falsos positivos e falsos negativos; duplicatas aproximadas não são eliminadas sem consentimento.
- A API de ações prioritárias continua determinística e dependente de vagas e evidências declaradas, não de inferência semântica profunda.
- O campo `allow_possible_duplicates` exige consentimento explícito do cliente, mas não substitui uma tela visual de comparação lado a lado.
- Antes de uso comercial: teste de navegador, PostgreSQL, testes de acessibilidade, análise de arquivos adversariais e validação com currículos reais anonimizados.

## Execução
Veja README e documentação existente. Testes direcionados: `cd production_api && PYTHONPATH=. ALLOW_TEST_SQLITE=1 DATABASE_URL=sqlite:////tmp/jobagent-test.db python -m pytest -q tests/`.
