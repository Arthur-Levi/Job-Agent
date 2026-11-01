# Job Agent — D2-E2.B | Modelo persistente inicial e migration aditiva 0005

**Estado:** implementação de *modelo + schema + testes de banco*; não confundir com endpoints de produção.  
**Branch:** `feature/d2-e2b-data-model`, PR Draft #5 sobre `feature/d2-e2a-candidate-contract`.  
**Protegidos:** `main`, PR #2/#3, banco do Codespaces `jobagent_react_test` em `0004`, todos os bancos legados, volumes e segredos.

## Escopo do primeiro incremento

Reutilizamos `CandidateProfile`, `CandidateExperience`, `CandidateEducation`, `CandidateProject`, `CandidateSkill`, `JobRequirement`, `JobMatch`, `ResumeVersion` e `Application`. **Não duplicamos essas tabelas**.

Adicionamos somente duas estruturas:

1. **`resume_import_records`**: recibo de **importação já confirmada** (UUID, user_id, idempotency_key, content_sha256, source_format, created_at). Impõe UNIQUE(user_id, idempotency_key), permite a mesma chave em contas diferentes, e não armazena PDF/DOCX/TXT bruto, nome de arquivo ou texto extraído. O hash refere-se ao payload confirmado canônico; sua canonicalização será implementada no serviço de confirmação, não neste checkpoint. O banco, sozinho, não impede uma mesma chave ser reutilizada com conteúdo diferente: isso exigirá verificação da comparação de hash pelo serviço.
2. **`career_facts`**: fato individual (UUID, user_id, subject, predicate, value, source_type, source_reference, verification, status, import_id opcional, supersedes_id opcional, created_at). `USER_DECLARED` é valor padrão; uma fonte de importação exige um recibo existente. Os estados `ACTIVE/SUPERSEDED/REJECTED` são restringidos no banco.

### Isolamento entre usuários

- `CareerFact(user_id, import_id)` usa FK composta para `ResumeImportRecord(user_id, id)`. Não aceita vincular uma conta B ao recibo da conta A.
- `CareerFact(user_id, supersedes_id)` usa FK composta autorreferenciada para `CareerFact(user_id, id)`. Não permite que a conta B declare uma correção para fato da conta A.
- A consulta por dono deverá continuar implementada nos serviços e APIs; os constraints de banco são defesa adicional, **não RLS PostgreSQL**.
- Não há lógica de impedir ciclos de múltiplas correções, marcar versões antigas SUPERSEDED nem limitar `EXTERNALLY_VERIFIED` ao verificador neste incremento. Todos esses controles exigem um serviço transacional específico antes de expor as rotas.

## Migration `0005`

`backend/migrations/versions/0005_d2e2b_career_facts.py` adiciona duas tabelas e índices. `down_revision=0004`. Nenhuma tabela anterior é alterada ou apagada pelo **upgrade**.

O `downgrade` remove exclusivamente as duas tabelas novas, **somente para CI efêmero**, e é proibido no Codespaces com dados preservados.

**Não executar esta migration ainda no Codespaces.** Os testes globais `backend/tests/integration/conftest.py` dão `DROP SCHEMA public CASCADE`; executá-los contra o banco `jobagent_react_test` apagaria dados. GitHub Actions usa contêiner PostgreSQL exclusivo `job_agent_test` e está autorizado a recriar esse banco descartável do CI.

## Critérios de aceite no CI

- Ruff, MyPy, subida e regressão Alembic com revision `0005`, zero drift entre SQLAlchemy e migration.
- Uma conta consegue registrar recibo e fato próprio.
- Chave de idempotência pode repetir em usuários diferentes, mas não na mesma conta.
- Conta B não consegue associar seu fato ao recibo da conta A.
- Conta B não consegue superseder fato da conta A.
- Fato de importação não é permitido sem recibo.
- Versão nova pode referenciar a anterior da mesma conta e manter valor antigo preservado.
- Recibo não possui campos de armazenamento de arquivo bruto.
- Testes D2-E2.A xfail continuam documentando os endpoints ainda ausentes.

## Decisões ainda pendentes em D2-E2.C/D

- Como assinar ou proteger o token de preview de curta duração, com binding ao usuário, sem persistir texto bruto antes da confirmação.
- Como vincular cada experiência/educação/projeto estruturado aos fatos confirmados (tabela de provenance ou associação especializada) sem duplicar `CandidateExperience` etc.
- Como normalizar idempotência de payload, detectar near-duplicates de funções na mesma empresa, resolver conflitos e impedir ciclos na cadeia de correções.
- Como restringir verificação externa, guardar histórico imutável e implementar privacidade, exclusão e retenção.
- Como expor APIs de confirmação e Fact Ledger e integrar ao React.
- Como homologar no **novo** PostgreSQL D2-E2 descartável, em worktree própria e sem tocar na `55435`.

**Nota:** mesmo após CI PASS, D2-E2.B não é um fluxo operacional completo. As rotas do contrato OpenAPI continuam ausentes, e ninguém deve apontar o aplicativo público para esta migration sem concluir os demais gates.
