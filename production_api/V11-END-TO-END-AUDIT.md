# Job Agent v11 — auditoria de fluxo e prontidão comercial

## Entregue nesta versão
- Upload autenticado de PDF, DOCX e TXT com limite de 2 MB.
- Limites de expansão DOCX, até 12 páginas PDF, máximo de 25 mil caracteres.
- Detecção explícita de seções do currículo; menções a tecnologias não são proficiência.
- Pré-visualização no navegador, confirmação humana para persistir evidências.
- Não salva arquivo ou texto integral no endpoint de importação.
- 6 testes direcionados passaram (test_resume_ingestion_v11.py e test_import_v10.py).
- Verificação de sintaxe Python e JS passou.

## Limitações de implementação
- PDFs digitalizados não possuem OCR.
- Somente skills são confirmadas automaticamente pela UI; experiência, educação e projetos aparecem como trechos e ainda exigem cadastro manual.
- Extração de seções é heurística, não compreensão semântica.
- O frontend depende de JavaScript e ainda carece de testes de navegação completos.
- O servidor usa proteção parcial de upload; ainda é necessária defesa em profundidade com proxy, varredura e quotas.
- A suíte geral não concluiu dentro do tempo da auditoria, portanto nenhum resultado geral é declarado.
- PostgreSQL real, migrations em banco novo, Stripe real, testes de browser e pentest não foram homologados nesta rodada.

## Auditoria funcional (estática + testes parciais)
1. Autenticação: existe, necessita homologação de recuperação de conta, expiração e múltiplas sessões.
2. Perfil e evidências: CRUD parcial/funcional, fontes continuam autodeclaradas.
3. Importação: fluxo de arquivo→prévia→seleção→salvar implementado, com lacunas na estruturação de experiências.
4. Diagnóstico: lógica determinística e rastreável, não é IA semântica avançada; risco de correspondências textuais superficiais.
5. Vagas: entrada manual; não há aquisição multicanal autorizada homologada.
6. Ações e acompanhamento: presentes, ainda não validados quanto a eficácia e retenção.
7. Revisão técnica: análise estática, não comprova autoria nem proficiência; sandbox não homologado.
8. Pagamentos: código existente, não ativar publicamente antes de testes reais.
9. Operação: necessita logs seguros, métricas, backup/restauração, migrações e observabilidade verificadas.

## Avaliação subjetiva (não baseada em testes com clientes)
- Funcionalidade implementada: 7/10.
- Facilidade de primeira utilização: 5/10.
- Profundidade e precisão do diagnóstico: 5/10.
- Prontidão operacional e comercial: 3/10.
- Nota global provisória: 5/10.

## R$ 299/mês
Não recomendado como assinatura pública hoje. Beta gratuito ou piloto assistido com usuários reais é defensável, após checagens básicas de segurança e infraestrutura. Testar disposição real a pagar, onboarding, uso semanal e resultados profissionais. A promessa de análise profunda com IA e verificação de competência não é suportada integralmente.

## Próximos gates
1. Fluxo de confirmação de experiência/projetos com edição e deduplicação, e persistência transacional.
2. Testes E2E de navegador com fluxo de cadastro→upload→confirmação→diagnóstico→ação.
3. PostgreSQL real: migração, backup/restore, isolamento entre usuários e concorrência.
4. Segurança: revisão de upload, PII, autorização, billing, limites e infraestrutura.
5. Avaliação do diagnóstico com 10–20 casos reais consentidos e avaliadores independentes.
6. Piloto com métricas de ativação, retenção, conclusão de ações e valor percebido.
