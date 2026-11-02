# D2-E2.D.1-D — Homologação integral de importação, revisão humana e Fact Ledger

**Status:** PASS CONDICIONAL na primeira rodada de integração; Beta/produção: NO-GO. Esta branch é baseada no checkpoint imutável `c50e16dc`. Não fazer merge até obter evidências e resolver os bloqueadores.

## Escopo da rodada

- Validar HTTP `POST /resume-imports/preview` e `/confirm` com dados sintéticos, incluindo múltiplas experiências, revisão humana com alterações e rejeição de itens.
- Confirmar idempotência de mesma chave, o isolamento entre usuários e nenhuma gravação para fonte adulterada.
- Verificar `GET /career/profile`, `GET /career/facts?include_history=true` e correções transacionais com histórico `SUPERSEDED` e nova declaração `USER_DECLARED`.
- Proibir que importação crie experiência inventada ou marque fatos declarados como `EXTERNALLY_VERIFIED`.
- Validar DB real **somente** no PostgreSQL descartável do GitHub Actions `job_agent_test`. O fixture de integração executa `DROP SCHEMA public CASCADE`; não executar em DB preservado mesmo que termine em `_test`.

## Evidência CI — primeira rodada aprovada

- Commit técnico `a3f176792f2b18ec582cc6d98342ee860b73cc24`
- GitHub Actions: https://github.com/Arthur-Levi/Job-Agent/actions/runs/41444233792
- Backend: **298 passed, 3 xfailed, 1 warning**.
- Frontend, sandbox-smoke e audit jobs: **SUCCESS**.
- `ruff check`, `ruff format --check`, `mypy` e Alembic executados no runner descartável: SUCCESS.
- Casos novos comprovados: múltiplos vínculos em uma prévia TXT sintética, edição/rejeição pela confirmação HTTP, idempotência com identidade dos fatos, correção e histórico, separação de usuários, rejeição de origem adulterada antes de persistir.
- Corrigida a ordem indeterminada da leitura de fatos em retry: consulta ordenada para estabilidade entre leituras. A identidade do conjunto é a propriedade de idempotência exigida, não a ordem original do insert.

## Critérios ainda não completos

1. Concorrência com mesma Idempotency-Key em sessões independentes, concorrência correção/importação, rollback induzido e dedupe de documentos diferentes.
2. Revisão humana do React em navegador real: upload → prévia → edição/rejeição → confirmação → revisão pós-reload → histórico com autenticação.
3. Correções estruturadas de título, organização, datas e categoria com validação explícita. A API atual de correções altera a descrição e preserva demais campos.
4. Expiração, segurança de dados e ausência de PII em tickets e logs. Ticket é assinado, mas **não criptografado**.
5. Escalabilidade de acesso à conta e tratamento consistente de indisponibilidade.

## Gate de segurança separado

O processamento externo de CV em produção **continua bloqueado** por `503 CV_SANDBOX_REQUIRED`, independentemente dos resultados de teste deste checkpoint. O broker de sandbox é um protótipo e não está operacionalmente homologado. Sem acesso ao Docker daemon pela API pública; sem currículos reais, deploy de produção ou pagamentos.

## Roadmap

D2-E2.D.1-D (integração) → D2-E2.E (diagnóstico e ATS fundamentados) → D2-E2.F (currículo e matching) → Beta Acceptance. O gate do sandbox permanece obrigatório em paralelo.
