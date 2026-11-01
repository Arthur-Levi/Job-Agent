# Job Agent — Roadmap unificado de pendências | Beta fechado de 10 candidatos

**Data de consolidação:** 2026-10-31 (BRT).  
**Natureza:** backlog de planejamento e aceitação; **não** afirma implementação.  
**Escopo:** backend moderno `backend/app` + React, integrando lógica revisada de `production_api`.  
**Base técnica:** D2-E2.A contrato + D2-E2.B modelos/migration `0005` com CI PASS (256 backend, 85 frontend, 9 xfail de endpoints ausentes); **sem deploy, sem migration no Codespaces, sem envio real Resend, sem Stripe real**.

## Definição de prioridade

- **P0-CORE:** necessário para primeira jornada útil do candidato no piloto.
- **P0-SAFETY:** bloqueia qualquer uso externo de dados pessoais e contas reais.
- **P1-BETA:** aumenta compreensão, ativação e retenção no piloto; pode ser reduzido para primeira onda de 2 usuários, se não afetar segurança e entendimento.
- **P2-LATER:** posterior à validação de 10 usuários; não deve atrasar o beta.
- **Estado:** `DONE-CI` = código testado sem prova operacional; `IN-PROGRESS` = parcialmente construído; `TODO` = pendente; `BLOCKED-EXTERNAL` = depende de fornecedor/configuração.

## Fatos do checkpoint (não inflar status)

- **D2-E1.5.1:** identidade com PostgreSQL e ações de verificação/reset homologadas em ambiente isolado; implantação pública ainda bloqueada.
- **D2-E1.5.2:** integração Resend com simulação/CI PASS; entrega real de email **PENDENTE** (domínio/chave).
- **D2-E2.A:** auditoria e contrato alvo OpenAPI 3.1, mas rotas novas **NÃO EXISTEM** no backend moderno.
- **D2-E2.B:** `ResumeImportRecord`, `CareerFact`, migration aditiva `0005`, testes CI e ownership por FKs **DONE-CI**; ainda sem serviços de confirmação e correções.
- **Codespaces:** worktree `/workspaces/Job-Agent-D2-E2` confirmada em `a3e3f33` pelo operador na última prova; **sincronização de 6743b64 ou posteriores não confirmada**. O banco `jobagent_react_test` na porta 55435 e migration `0004` permanece **protegido**; não executar migration/pytest com reset nele.
- **Preço:** R$299/mês é hipótese comercial atual para plano único; backlog antigo cita R$149/R$299 (proposta anterior), **não considerar preços implementados ou validados**.

## P0-CORE — jornada mínima end-to-end (ordem de execução)

| ID | Missão | Entrega pendente | Aceite PASS observável | Dependências |
| --- | --- | --- | --- | --- |
| B10-C01 | D2-E2.C.1 | Portar extração PDF/DOCX/TXT e implementar endpoint autenticado `resume-imports/preview` com limites, recusa de arquivos maliciosos e falhas controladas para PDFs imagem | PDF/DOCX/TXT sintéticos extraídos sem persistência de arquivo bruto; casos inválidos falham com resposta segura | D2-E2.B CI |
| B10-C02 | **ATS-01** em D2-E2.C | **ATS Parser Check**: relatório de texto extraível, reconhecimento de seções, contatos, cargos, empresas, datas e campos não recuperados | Métrica de fidelidade **por campo**, testada em corpus sintético; avisos quando extração incompleta; nada de “aprovado por ATS” | C01 |
| B10-C03 | D2-E2.C.2 | Separar múltiplos empregos/cargos, tratar datas, tabelas DOCX e seções PT/EN; preview editável em React, com excluir/corrigir/confirmar | Três experiências reais distintas permanecem distintas; sem inventar cargos ou proficiência | C01, C02 |
| B10-C04 | D2-E2.D | `resume-imports/confirm` com token de preview vinculado ao usuário/TTL, chave idempotente, hash de payload, transação atômica, upsert/revisão de near-duplicate, origem rastreável e ownership | Sem persistência antes da confirmação; duas contas isoladas; replay/concorrência sem duplicação; conflito exige decisão humana | C03, D2-E2.B |
| B10-C05 | D2-E2.D | Master Profile + Fact Ledger: projeção de experiências/projetos/formação e fatos, correções com histórico e proibição de falsa verificação externa | Referência de origem para cada claim; SUPERSEDED não reaparece; correções e isolamento testados; restrições + serviço transacional | C04 |
| B10-C06 | D2-E2.E | Diagnóstico de carreira por vaga, requisitos obrigatórios/desejáveis e recomendações específicas; sem chances fictícias de contratação | Requisito -> fonte/fato ativo -> interpretação/gap/ação é reprodutível; ausência não afirma incompetência | C05 |
| B10-C07 | **ATS-02** em D2-E2.E | **Job Keyword Alignment** baseado em fatos confirmados, com termos exatos e sinônimos documentados, requisitos por prioridade | Nenhuma palavra-chave inserida sem fato ativo; lacunas sinalizadas; pontuação, se houver, nomeada **cobertura documental**, nunca chance de aprovação | C05, C06 |
| B10-C08 | D2-E2.F | Gerador de currículo fundamentado, editável, ligado a `ResumeVersion` e a vaga opcional | 100% de claims com fatos ativos e pertencentes ao candidato; versão anterior preservada | C05, C06 |
| B10-C09 | **ATS-03** em D2-E2.F | **ATS Formatting Guard + Resume Builder**: template textual legível, exportação DOCX/PDF com seções simples e alternativa acessível | Layout sem tabela/coluna/caixa de texto complexa por padrão; arquivo abre e preserva todos os campos essenciais | C08 |
| B10-C10 | **ATS-04** em D2-E2.H | **Round-trip independente**: extrair novamente DOCX/PDF produzidos e comparar com dados confirmados, sinalizando perdas | Nome, cargos, empresas, datas e dados essenciais recuperados corretamente no corpus; divergências bloqueiam selo interno de fidelidade; **não simula ATS proprietário** | C09 |
| B10-C11 | D2-E2.G/H | Integrar React, dashboard de primeiro resultado, vagas/candidaturas e testes ponta a ponta API/PostgreSQL/navegador | Candidato sintético cadastra → importa → revisa → diagnostica → gera currículo → acompanha candidatura; nenhum envio afirmado sem ação real | C01–C10 |

**P0-CORE não implica automação de inscrição em vagas.** A primeira versão exige que o candidato envie por conta própria e registre o status corretamente.

## P0-SAFETY — liberação de pessoas reais (pode evoluir em paralelo com P0-CORE)

| ID | Entrega | Gate que impede beta real |
| --- | --- | --- |
| B10-S01 | Nova base PostgreSQL de staging/beta, isolada de `jobagent_react_test`, backups com criptografia em repouso/transporte, recuperação externa e restore demonstrado | Backup + restore real em ambiente separado, testes de integridade e política RPO/RTO |
| B10-S02 | Hospedagem persistente com HTTPS/TLS, DNS/subdomínio ou URL própria validada, proxy/firewall, segredos e restrição de CORS | Testes live de acesso, reinício, indisponibilidade, headers e não exposição direta do banco/API |
| B10-S03 | Email transacional real de verificação/reset (Resend ou alternativa segura), domínio remetente controlado e conta de teste | Recebimento real, expiração, token one-use, revogação e recuperação de conta pós-restart comprovados; **não usar MemoryMailer em ambiente público** |
| B10-S04 | Revisão de segurança e privacidade (LGPD, política/termos, exclusão/exportação, retenção, logs redigidos, limites, isolamento, abuso, resposta a incidentes) | Testes negativos multiusuário/IDOR, revisão de fluxo de dados, termos claros, contato de suporte e processo de exclusão |
| B10-S05 | Testes de segurança de upload e parsers (limites decompression bomb, PDF/DOCX malicioso, timeout, sem execução nem rede, limpeza de temporários) | Testes negativos PASS; preferir parser isolado/worker com recursos limitados antes do beta |
| B10-S06 | Prova de lançamento em ambiente real (CI + E2E navegador + 5 testes live antes skipped + rollback e alerta) | Um operador reproduz o runbook sem banco original, sem dados pessoais em logs; nenhum P0 aberto |
| B10-S07 | Preparação comercial/legal e atendimento de candidatos reais (idade/capacidade contratual aplicável, responsáveis, documentação, termos, reembolso se cobrar) | Operação de beta gratuito/assistido documentada; verificar formalização com profissional adequado antes de cobrança |

**Sem acesso público com dados de candidatos enquanto P0-SAFETY estiver aberto.** Conversas exploratórias e entrevistas sem currículos podem começar antes.

## P1-BETA — melhoria de experiência e retenção

| ID | Entrega | Quando |
| --- | --- | --- |
| B10-P01 | Onboarding guiado, estados de erro, responsividade e acessibilidade por teclado/assistivo | Antes de ampliar de 2 para 10 usuários |
| B10-P02 | Métricas com privacidade: tempo até primeiro valor, preview→confirm, exportação, desistências, retorno 7 dias | Antes de cada onda beta |
| B10-P03 | Entrevistas com 20–30 candidatos-alvo, seleção de 10 betas e suporte estruturado | Recrutamento pode começar sem upload de dados |
| B10-P04 | Beta em ondas de 2 → 5 → 10, sem cobrança inicial; critérios de parada por erro/privacidade/perda de dados | Depois dos gates P0 |
| B10-P05 | Testar disposição de pagar R$299/mês e qualidade do valor percebido; acompanhar retorno e renovações quando houver cobrança segura | Depois de resultados concretos |
| B10-P06 | Tratamento refinado de PDFs escaneados (OCR seguro) ou fluxo alternativo de colar texto sem perder conteúdo | Caso o corpus/usuários demonstrem demanda |
| B10-P07 | Mensagens claras sobre limitações ATS e orientação de revisão do formulário no site do recrutador | Com ATS-01/02/03 |
| B10-P08 | Página de apresentação, FAQ, guia de suporte, canal de incidentes e política de exclusão | Antes da abertura a convites reais |

## P2-LATER — não bloquear beta de 10

| ID | Entrega | Regra |
| --- | --- | --- |
| B10-L01 | **ATS-05 Profiles**: perfis específicos Greenhouse/Workday/Lever/Gupy etc. | Só com documentação atual das plataformas e testes reais autorizados; não alegar compatibilidade universal |
| B10-L02 | Integrações e preenchimento assistido de ATS externos via APIs autorizadas | Sem burlar CAPTCHA, limites, autenticação ou regras dos portais; confirmação humana |
| B10-L03 | Automação de candidatura multicanal | Exige autorização, auditoria, exclusão de dados e confirmação de envio real |
| B10-L04 | IA semântica mais avançada de vagas e currículos, sem alucinações ou promessas de empregabilidade | Apenas após medição de ganho real vs análise determinística |
| B10-L05 | Stripe real, assinaturas, cancelamento, cobrança, antifraude, reembolsos, documentação fiscal | **Antes de cobrar**, não é requisito do beta gratuito; não simular pagamentos reais |
| B10-L06 | A/B tests, segmentos B2B/administrativo/logística e funcionalidades enterprise | Depois de retenção da coorte inicial |

## Portões da liberação (go/no-go)

| Gate | Evidência | Critério |
| --- | --- | --- |
| G0 — Código e esquema | D2-E2.B + C/D/E/F/G/H | Testes CI PASS; migrations aditivas verificadas em banco próprio |
| G1 — ATS legível | ATS-01/02/03/04 | Texto e campos preservados; diferenças reportadas; nunca prometer ATS score universal |
| G2 — Segurança operacional | S01–S07 | HTTPS, email real, isolamento, backup-restore, exclusão, privacidade e incidentes PASS |
| G3 — Piloto assistido | 2 → 5 → 10 | Sem vulnerabilidades graves abertas; candidato conclui jornada principal |
| G4 — Comercial | Reuniões/feedback e eventual cobrança | Não converter “10 betas” automaticamente em “10 clientes pagantes”; validar oferta e meios legais |

## Ordem sugerida da próxima execução

1. **Sincronizar Codespaces de maneira não destrutiva:** worktree `/workspaces/Job-Agent-D2-E2`, confirmar HEAD, buscar branch. Não aplicar `0005` no DB antigo, nem executar suite local com fixture que derruba schema.
2. **D2-E2.C = C01 → ATS-01/C02 → C03**, parser + revisão.
3. **D2-E2.D = C04 → C05**, confirmação e fatos.
4. **D2-E2.E/F = C06–C09**, diagnóstico, keywords e exportação.
5. **D2-E2.H = C10/C11**, round-trip e browser.
6. **Infra/segurança S01–S07 em paralelo, mas sem expor usuários reais.**
7. **Beta em ondas**, medir efetividade, depois decisão de cobrança.

## Restrições comerciais e de comunicação

- “Compatível com ATS” deve ser qualificado como **testado com parser e regras próprias**; não garantir leitura igual por ATS de terceiros.
- Não inventar skills, certificações ou experiência para otimizar palavras-chave.
- Não confundir “cobertura documental” com probabilidade de entrevista, de emprego ou de aprovação automatizada.
- Não commitar currículos de pessoas reais, credenciais, tokens de recuperação nem dumps.
- Documento de planejamento: criar/atualizar tarefas **não** implementa código de ATS, deploy, email ou billing.
