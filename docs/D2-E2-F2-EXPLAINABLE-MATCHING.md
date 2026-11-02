# D2-E2.F.2 — Matching explicável fundamentado no Fact Ledger

**Status:** PASS TÉCNICO CONDICIONAL. **Produção / beta: NO-GO.**

**Evidência CI:** commit `56225e118355eecc6b9508bd731bc9969d7e98c0`, https://github.com/Arthur-Levi/Job-Agent/actions/runs/41493227541. **312 passed, 3 xfailed, 1 warning** no backend; frontend, browser-smoke, real-browser-postgres-e2e, sandbox-smoke e audit concluíram com SUCCESS. O job audit continua advisory/não bloqueante. A regressão Chromium exercita a jornada anterior de importação e diagnóstico; **não** testa uma interface React de matching (ainda inexistente).

## Contrato de API

`POST /api/v1/career/vacancy-match` com autenticação obrigatória. Corpo JSON:
```json
{
  "vacancy_title": "Analista de Dados",
  "requirements": [
    {"category":"skill", "name":"Excel", "importance":"required"},
    {"category":"experience", "name":"Analista de Dados", "importance":"preferred"},
    {"category":"work_mode", "name":"onsite_only", "importance":"required"}
  ]
}
```

Os requisitos são **fornecidos pelo usuário e não verificados com o empregador**. São aceitas categorias `skill`, `experience`, `education`, `project`, `work_mode`; há no máximo 20 requisitos, sem duplicatas (após normalização de caixa/espaços) e com limites de comprimento. A API **não** salva vagas, não modifica fatos e não envia candidaturas.

Cada requisito recebe:
- `documented_match`: correspondência literal de categoria + título estruturado + título de fato ativo, ou modalidade explicitamente declarada compatível;
- `not_documented`: ausência de fato com título equivalente, formato inválido ou declaração conflitante/ambígua; **não** significa ausência de competência;
- `explicit_incompatibility`: **somente** modalidade `work_mode` estruturada `{"mode":"remote_only"}` versus exigência `onsite_only` (ou inverso), com **um único** tipo de declaração ativa; sem recusa ou elegibilidade automática.

As correspondências retornam `fact_id` e `verification` exatamente como no Fact Ledger. Um fato do usuário é uma declaração, **não** comprovação externa. Dados superseded/rejected ou de outros usuários nunca entram. Não há porcentagem, probabilidade de contratação, nota ATS ou inferência de sinônimos. Dúvidas de significado e diferenças de redação permanecem desconhecidas; a pessoa deve conferir.

## Aceitação

Os testes de integração usam apenas PostgreSQL efêmero em GitHub Actions. Validam:
- identificação literal e evidências exatas;
- exclusão de fatos substituídos, não estruturados e de outras contas;
- incompatibilidade explícita de modalidades, sem inventar incompatibilidades por ausência;
- duas modalidades ativas contraditórias => `not_documented`, não conclusão arbitrária;
- corpo inválido, categorias proibidas, duplicatas e acima do limite => 422;
- comportamento vazio e nenhuma escrita.

**Atenção:** o fixture de integração recria o schema `public`; jamais rodar em banco preservado, ainda que seu nome contenha `_test`.

## Pendências

- UI React para inserir/revisar requisitos da vaga e ler evidências, com revisão humana.
- Comparação segura de vagas persistidas pelo usuário via `Job`/`JobRequirement` (não faz parte desta primeira API).
- Normalização de sinônimos validada e explicada, critérios de senioridade/tempo sem excesso de confiança.
- D2-E2.F.3 exportação PDF/DOCX; D2-E2.F.4 revisão final no React; D2-E2.F.5 homologação completa.
- Segurança do parser operacional: `503 CV_SANDBOX_REQUIRED` permanece ativo para produção e bloqueia currículos reais. Não fazer merge em main, liberar beta ou executar migrations contra DB do Codespaces.

## Segurança de dados

Não aceitar evidência fornecida no corpo da requisição; o serviço busca fatos ativos do usuário autenticado. Os dados da vaga não são enviados a provedores externos. Retornos não reproduzem currículo bruto.
