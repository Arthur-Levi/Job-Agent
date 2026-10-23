# V7 — Revisão técnica de artefatos

## O que funciona
- O usuário fornece uma lista JSON de até 30 arquivos de texto (máximo 120 KB).
- A API faz um inventário determinístico: código-fonte, arquivos de teste, documentação, dependências e CI.
- Um SHA-256 do conteúdo e o relatório são persistidos em `artifact_reviews`, vinculados ao usuário e à evidência.
- O conteúdo original dos arquivos **não é persistido**; o usuário deve evitar colar dados sensíveis.
- Histórico de avaliações, exportação e exclusão da conta incluem os novos registros.
- O código fornecido **não é executado**, URLs não são acessadas e nenhuma pontuação de competência é atribuída.

## O que NÃO funciona / limitações
- A detecção de segredos é heurística, não garante prevenção total de vazamento.
- Arquivos de testes podem ser falsos ou inúteis; a presença não comprova execução ou cobertura.
- Sem análise semântica, sandbox, verificação de commits, atribuição de autoria ou revisão humana.
- Sem integração automática GitHub; nenhum repositório externo foi avaliado.
- Homologação externa PostgreSQL/Stripe/navegador permanece pendente.

## Próximos passos para avaliação realmente confiável
1. Integração GitHub OAuth com escopo mínimo, autorização explícita e expiração.
2. Fetch server-side apenas via API GitHub autenticada, sem SSRF; limites de arquivos e proteção de segredos.
3. Análise estática por linguagem e testes executados em ambiente efêmero sem rede e sem privilégios.
4. Revisão de autoria, contribuições e qualidade por avaliadores independentes.
5. Dataset consentido de projetos reais, revisão dupla cega e métricas de discordância.
