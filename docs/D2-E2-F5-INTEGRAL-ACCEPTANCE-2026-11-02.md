# D2-E2.F.5 — Homologação integral sintética e gate para Beta Acceptance

Data: 2026-11-02. Branch: `audit/d2-e2f5-full-acceptance`. PR #17 (Draft, base F.4). 
**Disposição:** PASS TÉCNICO CONDICIONAL; **NO-GO para uso de documentos reais, cobrança ou deploy público**.

## Matriz de evidências

| Subetapa | Evidência | Resultado |
| --- | --- | --- |
| Importação e revisão | React + FastAPI real + PostgreSQL descartável, candidato sintético, confirmação explícita | PASS |
| Master Profile / Fact Ledger | Listagem, correção transacional, histórico e nova sessão | PASS |
| Diagnóstico | Fatos ativos e limitações, ausência não vira inelegibilidade | PASS |
| Matching | Requisito não documentado e razão explicável; casos de correspondência exata e conflito testados no backend | PASS |
| Aprovação de exportação | Checkbox + digest SHA-256, download binário real PDF/DOCX | PASS |
| Integridade PDF e DOCX | Arquivos extraídos de Chromium, reabertos com pypdf/python-docx, conteúdo sintético comparado | PASS |
| PDF 1 página | Contagem pypdf + renderização PNG | PASS |
| DOCX 1 página (LibreOffice no CI) | Conversão independente do documento real com LibreOffice, extração e PNG | PASS no ambiente Ubuntu 24.04 de CI |
| Isolamento multiusuário | Segunda conta com login real não vê fatos, diagnóstico ou matching do primeiro; digest de outra conta é recusado | PASS |
| Sessão revogada | Login real da segunda conta, logout e requisição posterior recusada | PASS |
| Concorrência | Duas sessões PostgreSQL e exports paralelos de duas contas; sem dados cruzados | PASS |
| Correção e expiração de versão | Digest antigo recusado depois de correção persistida em outra sessão | PASS |
| Falha de renderização | Erro sintético não modifica ledger; retorno controlado | PASS |
| Expiração de tickets de importação | Teste preexistente de ticket expirado e horário futuro | PASS na regressão backend |
| Usabilidade por teclado | Links acionáveis com Enter, checkbox por Space, nomes de campos | Teste automatizado básico; não certifica WCAG |
| Revisão visual | PNGs reais de PDF e DOCX extraídos do GitHub Actions e inspecionados visualmente | Uma página, sem cortes ou sobreposição no fixture sintético |
| Layout profissional | Conteúdo documentado, mas pode haver repetição de títulos/descrições já existentes na origem | **Melhoria de usabilidade pendente** |
| Teste hostil de sandbox de produção | CI sandbox smoke usa runner descartável, não comprova isolamento operacional completo | **NO-GO** |
| Privacidade e conformidade | Retenção, exclusão, acesso a arquivos, consentimentos, base legal, revisão jurídica e políticas | **NO-GO** |
| Recuperação operacional | Backups externos/restauração cronometrada, interrupção de worker, limites distribuídos e observabilidade | **NO-GO** |
| Auditoria técnica | Job audit é advisory e `continue-on-error` | **Não constitui aprovação de segurança** |

## Como reproduzir com segurança

- Use exclusivamente os jobs `backend` e `real-browser-postgres-e2e` na branch do PR. Nunca aponte testes de integração a um PostgreSQL persistente. Os fixtures do backend podem executar `DROP SCHEMA public CASCADE`.
- O job real-browser-postgres-e2e instala LibreOffice Writer, Poppler e Chromium no runner temporário, migra somente `job_agent_e2e_test` e usa dados sintéticos.
- O navegador salva dois documentos de teste em `/tmp/jobagent-d2e2f5-synthetic` e o verificador `scripts/d2e2f5_document_acceptance.py` compara texto, quantidade de páginas, limites de tamanho e estrutura. Gera imagens `pdf-preview.png` e `docx-preview.png` preservadas por 3 dias no artifact `d2-e2f5-synthetic-document-previews` para revisão humana.
- A API de produção continua deliberadamente bloqueando preview de currículos reais com `503 CV_SANDBOX_REQUIRED`. Testes em `APP_ENV=test` não removem esse bloqueio.

## Pendências que impedem aprovação beta

1. **Sandbox operacional:** processo/contêiner com identidade separada e acesso mínimo, permissão correta do socket do broker, limites globais distribuídos por usuário, filas, supervisão, cancelamento, arquivos maliciosos e testes de falha com métricas operacionais. Deploy real e TLS/firewall/proxy validados com documentação.
2. **Privacidade e segurança:** política de retenção/exclusão de currículos e excerpts, isolamento de dados, backups e restauração, acessos administrativos, consentimentos/avisos adequados, auditoria de vulnerabilidades bloqueante e revisão de LGPD.
3. **Qualidade e usabilidade:** remover redundâncias de descrições importadas **sem inventar informações**, refinar apresentação ATS; validar fontes/acentuação e DOCX também no Word; acessibilidade com testes abrangentes (teclado, leitores de tela, contraste e WCAG); testar fluxo com 2+ candidatos sintéticos e novos cenários de browser.
4. **Resiliência e carga:** quedas da API/worker/banco durante importação e exportação, limites e quotas por usuário, concorrência entre replicas, retomada/rollback e testes de p95 sob carga sintética.
5. **Beta Acceptance:** termos, onboarding, operação de suporte, billing testado com isolamentos seguros, monitoramento, plano de rollback e critérios de cancelamento. Só então selecionar até 10 betas, mediante nova autorização.

## Escopo da aprovação

A homologação demonstra que os módulos funcionam juntos com dados sintéticos, PostgreSQL descartável e uma configuração de teste. Ela não demonstra adequação de produção, nem implica que a aplicação tenha conseguido emprego para alguém. Não habilitar o processamento de dados reais, não mesclar PRs para main e não alterar bancos persistentes automaticamente.
