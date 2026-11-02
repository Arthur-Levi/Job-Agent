# D2-E2.F.4 — React: revisão do currículo, aprovação e matching fundamentado

**Status:** **PASS TÉCNICO CONDICIONAL**. Produção e beta: **NO-GO**.

**CI comprovado:** commit `fca898a4b5c8dd293cb92cae022dc20458bcd186`; https://github.com/Arthur-Levi/Job-Agent/actions/runs/41501343273. Todos os seis jobs concluíram SUCCESS. Backend **317 passed, 3 xfailed, 1 warning**; frontend Vitest **17 arquivos aprovados, 1 skipped**, lint e build PASS. Chromium + API real + PostgreSQL efêmero comprovou download de PDF e DOCX após revisão e resposta `not_documented` no matching de uma competência ausente. Esses testes não autorizam uso de currículos reais em produção.

## Jornadas

1. `/career/resume-review` (rota protegida): lista todos os fatos estruturados incluídos, omitidos com motivo, IDs de fatos, origem declarativa, descrição, empresa e datas. A caixa de aprovação começa desmarcada e downloads são desativados em carregamento, erro, ausência de fatos, mudança de versão e durante requisição pendente.
2. `GET /career/resume-export/preview` fornece o SHA-256 que vincula a aprovação a nome, fatos incluídos, omitidos e versão do modelo. `POST /career/resume-export/pdf|docx` recebe `approved=true` com hash exato. Resposta binária com autenticação; navegador baixa via URL temporária e libera a URL na sequência.
3. Se o servidor detectar `RESUME_APPROVAL_STALE`, cancela aprovação anterior e recarrega a prévia. A aprovação não é persistida no navegador. O documento precisa ser conferido antes de envio.
4. `/career/vacancy-match` (rota protegida): recebe título e até 20 requisitos digitados pelo candidato, categoria, obrigatoriedade, confirmação humana. Exibe `documented_match`, `not_documented` ou `explicit_incompatibility` com evidências e próximos passos. Alterações nos requisitos apagam o resultado anterior.

## Limites e integridade

- Sem persistência de requisitos da vaga, atualização automática de fatos ou candidatura automática.
- Ausência de fatos não significa ausência de habilidade; correspondências exatas não provam contratação.
- O PDF passa por verificação de uma página no backend. **O DOCX ainda depende de verificação visual de paginação em Word/LibreOffice.**
- A tela não oferece edição estruturada: correções de fato pertencem ao Fact Ledger e futuras melhorias.
- O bloqueio de parser `503 CV_SANDBOX_REQUIRED` em produção permanece intocado.
- O job Chromium da CI usa somente usuários e currículos sintéticos contra API real e PostgreSQL efêmero. Ele não avalia segurança de um deployment público.
- Não mesclar em main, usar dados reais, tocar banco preservado ou cobrar cliente nesta etapa.

## Aceitação

Testes de componentes React para aprovação explícita, invalidação, retorno stale, dados vazios, comparação, citações e incerteza. Teste Chromium sintético para baixar PDF e DOCX realmente pelo browser e comparar vaga com fato ativo. Manter aprovação somente após CI completo.
