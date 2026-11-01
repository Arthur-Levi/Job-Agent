# D2-E2.C — Importação de CV + ATS Parser Check — checkpoint de implementação

**Branch:** `feature/d2-e2c-ats-preview` (PR #7 Draft contra `feature/d2-e2b-data-model`).  
**Escopo:** preview autenticado e revisão **somente local**.  
**Não implementado:** confirmação, persistência de revisão no banco, Fact Ledger via API, certificação de ATS externo, OCR e candidatura automatizada.

## Implementado

- `POST /api/v1/resume-imports/preview` em `backend/app/api/v1/resume_imports.py`, dependente de `CurrentUserDep`. Processa `multipart/form-data` e retorna sugestões estruturadas para revisão.
- `backend/app/services/resume_preview.py`: extração de texto de TXT UTF-8, PDF textual (pypdf), DOCX textual/tabelas em ordem de documento; limites: arquivo 2MB, texto 25 mil caracteres, PDF 12 páginas, DOCX 150 entradas ZIP/10MB descompactados. Rejeita arquivos vazios, arquivos sem texto, extensões não suportadas e ZIPs com paths/embeddings proibidos. Sem rede externa ou OCR.
- Detecção conservadora de cabeçalhos PT/EN para experiência, educação, projetos, competências, resumo, objetivo; contatos email/telefone; separação por cabeçalhos fortes/datas/bullets. Quando existe a forma explícita `Empresa | Cargo | AAAA-AAAA`, separa empresa/cargo/datas. Para formatos ambíguos, **não inventa** campos: exige revisão.
- Relatório ATS preliminar: texto extraível, seções encontradas, contatos reconhecidos e avisos de campos ausentes. **Não mede nota universal nem chance de passar pelo RH.**
- `frontend/src/pages/ResumeImportPage.tsx` em rota autenticada `/resume-import`: upload, relatório, edição de cargo/empresa/períodos/descrição, descarte de sugestões e reconhecimento explícito dos limites. Nenhum dado revisado é gravado; sai da memória ao sair da tela.
- `frontend/src/services/http.ts` agora aceita FormData mantendo bearer, timeout, request-id e tratamento de falhas; o navegador decide boundary do multipart.
- Limite de corpo da API agora é 2.15 MB; para rota de upload, middleware contabiliza bytes reais mesmo sem Content-Length, antes de entregar a requisição ao parser.

## Testes / gates

- `backend/tests/unit/test_d2e2c_ats_preview.py`: corpus sintético (3 experiências, mesma empresa com dois cargos, contatos, DOCX tabelado, PDF escaneado sem texto, conteúdo inválido/maior que limite, autenticação obrigatória e verificação de HTTP 413).
- `frontend/src/pages/ResumeImportPage.test.tsx`: fluxo visual de prévia e revisão local/descartar + bloqueio de upload grande.
- Os 9 `xfail` de D2-E2.A foram ajustados: `resume-imports/preview` deixa de ser xfail e tem teste positivo de OpenAPI; os demais endpoints continuam **PENDENTES**.
- PASS só após CI completo (Ruff/MyPy/backend PostgreSQL CI, frontend build/lint/test) e posterior sincronização somente Git no Codespaces.

## Limitações de segurança para beta real

- PDF/DOCX não confiáveis são parseados no processo da API; **ainda falta isolamento do parser em processo/worker com limites de CPU, memória e tempo**, monitoramento e revisão de dependências antes de usuários externos.
- A prévia não gera token verificável de confirmação nem preserva edições ao reiniciar; isso será feito em D2-E2.D com transação idempotente e binding por usuário.
- O identificador de prévia atualmente é apenas correlacional: **não habilita POST /confirm**.
- Sem OCR; currículos digitalizados precisam ser substituídos por arquivo com camada textual.
- Teste de leitura de retorno de DOCX/PDF exportados (ATS-04) pertence à D2-E2.H. Compatibilidade com fornecedores (Gupy, Greenhouse etc.) permanece P2.
- Worktree Codespaces `/workspaces/Job-Agent-D2-E2` permanece em checkpoint anterior até sincronização confirmada. Banco `jobagent_react_test` na revisão `0004` permanece intocado. **Nunca executar pytest com fixture destrutiva nem alembic upgrade head nessa base.**

## Próximo passo

D2-E2.D: confirmação explícita e persistência transacional do que foi revisado, idempotência de hash e isolamento de usuários no Fact Ledger. Não usar dados pessoais reais até gates P0-SAFETY.
