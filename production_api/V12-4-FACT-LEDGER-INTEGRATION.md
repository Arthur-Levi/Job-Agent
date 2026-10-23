# Job Agent v12.4 — integração da jornada

## Implementado
- `/api/import/resume/confirm`: após confirmação, projeta somente novas evidências para `MasterProfileItem` e `CareerFact`, atomicamente, com `source_reference=evidence:<id>` e `verification=USER_DECLARED`. Importação repetida não duplica projeções exatas.
- `/api/fact-ledger/contradictions`: divergências conservadoras entre fatos ativos do mesmo sujeito/predicado. Não determina qual é verdadeiro.
- `/api/diagnostic/fact-grounded`: requisitos de vagas com referências a fatos ativos, sem probabilidades de contratação.
- `/api/resume/grounded-draft`: texto somente de fatos ativos pertencentes ao usuário; recusa IDs de outros usuários ou fatos substituídos. Não gera conquistas novas.
- Interface: painel de divergências no Fact Ledger e geração de rascunho rastreável no diagnóstico.

## Limitações relevantes
- Extração original do currículo continua heurística; informações devem ser confirmadas.
- Fatos não são verificados externamente, e a correspondência de requisitos é textual.
- Currículo é um rascunho rastreável, não um template ATS final nem arquivo DOCX/PDF.
- Detecção de contradições pode sinalizar alterações legítimas de cargo ao longo do tempo.
- Não há execução de testes de navegador nem auditoria independente de segurança.

## Testes executados
- Suíte completa com SQLite de teste: **62 passed, 1 warning**.
- Sintaxe JavaScript: `node --check` aprovado.
- PostgreSQL real: **NÃO HOMOLOGADO**. Ambiente de execução atual não disponibiliza `docker`, `psql`, `pg_ctl` nem driver `psycopg`. O script `run-postgres-v124.sh` prepara migração, inspeção de tabelas e testes para execução em ambiente com PostgreSQL real. Sua existência não representa execução bem-sucedida.

## Como homologar PostgreSQL
1. Instalar dependências de `requirements.txt` e iniciar banco PostgreSQL 16 isolado.
2. Definir `DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/banco_de_testes`.
3. Executar `cd production_api && ./run-postgres-v124.sh`.
4. Registrar evidências da execução, testar restauração de backup, concorrência, rollback e E2E navegador antes de comercializar.
