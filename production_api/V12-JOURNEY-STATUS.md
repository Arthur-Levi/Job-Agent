# V12 — Jornada principal, entrega incremental

## Entregue
- Extração de currículo PDF/DOCX/TXT herdada da v11, com limites de tamanho.
- Sugestões editáveis de experiências, projetos, formação e cargo-alvo baseadas em cabeçalhos explícitos; sem inferir empregador, datas ou proficiência.
- Tela de revisão antes de persistir, com escolha de itens e confirmação explícita.
- Endpoint autenticado GET /api/journey/first-result com próximas ações e limitações mesmo sem vagas cadastradas.
- Dashboard direciona ao próximo passo; depois da confirmação, volta ao dashboard.
- Mantém diagnóstico por vagas e evidências existente, sem estimar probabilidade de contratação.

## Verificações realizadas
- 7 testes focados passaram com SQLite de teste; não equivalem a homologação PostgreSQL.
- Sintaxe Python e JavaScript verificada.

## Bloqueadores para considerar a jornada *completa*
- Currículos sem cabeçalhos padronizados exigem edição manual.
- PDF escaneado não tem OCR.
- A extração agrupa cada seção em um rascunho, ainda não separa múltiplos empregos com datas/cargos.
- Teste integrado real no navegador e banco PostgreSQL pendentes.
- Diagnóstico baseado em vagas reais requer que usuário informe requisitos.
- Falta teste de usabilidade com pessoas reais e medição de tempo até primeiro valor.
- Importações repetidas podem criar itens redundantes em execuções separadas.

## Segurança e limitações
- Não executa arquivos enviados, não armazena o currículo bruto pelo endpoint de prévia.
- Conteúdo extraído é devolvido ao cliente para revisão; só itens confirmados são persistidos.
- Recomendado processar PDF/DOCX em worker isolado antes de expor uploads ao público.
