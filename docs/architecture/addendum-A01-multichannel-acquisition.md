# Addendum A01 — Multi-Channel Acquisition & Resume Intelligence

- **Status:** **aprovado** pelo usuário em 2026-10-08 como planejamento. **Nenhuma implementação** nesta etapa.
- **Data:** 2026-10-08
- **Escopo preservado:** a D1.5 (seed, README final, fechamento e dívida técnica) segue como planejada.
  Nenhum código, migration ou teste existente é alterado por este adendo.
- **Objetivo final:** transformar o Job Agent numa plataforma pessoal de aquisição profissional
  multicanal, com currículos verificáveis, workflows específicos e decisões orientadas por resultados.

---

## 0. Decisões aprovadas pelo usuário (2026-10-08)

1. **Numeração D4–D8** aprovada como planejamento inicial, **sujeita aos gates técnicos de cada fase**.
2. **LinkedIn, Indeed, InfoJobs e páginas oficiais são fontes-alvo.** Nenhuma operação automatizada será habilitada sem
   **autorização verificada por fonte e por operação**.
3. **Headhunter CRM:** dados profissionais **mínimos**, proveniência, finalidade, controles de privacidade e
   **política de retenção documentada**.
4. **Setores iniciais** (Banking & Fintech, Startups, Software Houses, Consultorias de tecnologia) aprovados como
   **sementes editáveis**.
5. **20 candidaturas por setor** = **limiar exploratório inicial**. **Não** usar essa amostra para alegações
   estatísticas conclusivas.
6. **Entidade conceitual `Opportunity`** (separa oportunidade, publicação de vaga e candidatura) registrada na seção 3.K.
   **Sem migração na D1.5.**

---

## 1. Princípios inegociáveis

| # | Princípio | Consequência prática |
|---|---|---|
| P1 | **Autorização explícita, por fonte e por operação.** Nunca presumir que uma plataforma autoriza scraping, acesso automatizado ou submissão automática. | Toda fonte nasce `UNVERIFIED`: operações restritas desabilitadas até haver evidência registrada. A checagem fica no **service**, não só na UI. |
| P2 | **Sem automação contrária às regras dos portais.** Sem scraping, sem contornar CAPTCHA/limites, sem bot de candidatura. | Não existe código de coleta para uma fonte antes de sua autorização estar verificada. |
| P3 | **Nada simulado como se fosse real; nenhuma API inventada.** | Antes de cada conector: ler a documentação e os termos **oficiais** da fonte e registrar a evidência (URL, data de leitura, trecho relevante). Fixtures de teste são rotuladas `synthetic` e jamais apresentadas como resposta real. |
| P4 | **Proveniência em tudo.** | Todo dado importado guarda fonte, identificador externo, URL, data de captura, método e versão do normalizador. |
| P5 | **Fatos verificáveis.** | Toda afirmação profissional num currículo referencia ≥ 1 fato do Master Profile; afirmação sem lastro bloqueia a exportação. |
| P6 | **Histórico auditável e append-only** (mesmo padrão de `application_events`). | Mudanças relevantes viram eventos imutáveis, com ator e, quando houver, a confirmação humana. |
| P7 | **Humano no controle de qualquer ação externa irreversível** (enviar, submeter, compartilhar dados, finalizar currículo). | Ponto de confirmação registrado no evento: quem, quando, o quê. |
| P8 | **Determinismo primeiro; IA opcional e plugável.** | Regras, deduplicação, validações e métricas são determinísticas. Onde houver IA, fica atrás de interface, sem acoplar a um fornecedor. |
| P9 | **Privacidade e consentimento para dados de terceiros** (recrutadores). | Minimização, finalidade, consentimento/base registrados, exportação e remoção. Avaliar requisitos da LGPD antes da D6 (não é parecer jurídico). |
| P10 | **Comparação neutra.** | Nenhuma hipótese sobre qual setor/canal/modelo performa melhor; métricas sempre exibem o tamanho da amostra. |

---

## 2. Distribuição por fase

> **Aprovado como planejamento inicial** (decisão 1): a numeração D4–D8 deriva da ordem do diagrama da D1
> (Fit Engine → Resume Engine/Truth Validator → CRM → Analytics → Learning) e **cada fase só começa após seus
> gates técnicos** (fase anterior fechada, dívida revisada, ADRs pendentes resolvidas).

| Fase | Tema | Requisitos do A01 que entram |
|---|---|---|
| **D1.5** | Fechamento | Somente documentação: registrar este adendo, atualizar README, incluir os impactos da seção 4 na lista consolidada de dívida técnica. **Zero código novo.** |
| **D2** | Master Profile | **Pré-requisitos de F/G:** dados de contato (e-mail, telefone, links) no perfil; cada fato (experiência, projeto, formação, skill) com ID estável, datas, evidência/comprovação opcional e estado de verificação; é a base contra a qual afirmações são validadas. |
| **D3** | Job Intelligence & Sources | **A** (registro de fontes, autorização por operação, limites, autenticação por referência a segredo), **B** (contrato do Source Adapter + testes de conformidade), **C-5** (workflow de importação manual, a única fonte 100 % sob controle do usuário), **H** (deduplicação + múltiplos links de origem), entidade **Company** (aliases, setor), proveniência. Conectores reais só para fontes com autorização **verificada**. |
| **D4** | Fit & Opportunity Score | Normalização de requisitos e cobertura Perfil × Requisitos (insumo de **G: compatibilidade com requisitos**); estado QUALIFIED com justificativa auditável. Fonte/setor/canal **não** entram como prior do score (P10); só como dimensão de análise. |
| **D5** | Resume Engine + Truth Validator | **F** (registro de templates; separação fatos / plano de conteúdo / apresentação; ledger de afirmações) e **G** (Resume Quality Gate, relatório auditável por versão). |
| **D6** | Application CRM & Workflow Orchestrator | **C** (os cinco workflows com estados, ações, confirmações humanas e auditoria), **E** (Headhunter CRM, sem envio em massa), entidade de **campanha** (**D**), Kanban por workflow. |
| **D7** | Analytics | **I** (todas as métricas) e **D** (comparação entre setores, canais e modelos de currículo). |
| **D8+** | Learning Engine | Aprendizado a partir de resultados medidos, orientado a hipóteses; nada presumido de antemão. |

Regra de entrada em cada fase: ela só começa quando a anterior estiver fechada e a lista de dívida
técnica revisada (uma fase por vez).

---

## 3. Requisitos detalhados

### A. Multi-Source Discovery

**Fontes-alvo (aprovadas):** LinkedIn, Indeed, InfoJobs e páginas oficiais de carreira; também ATSs e feeds
autorizados, empresas-alvo, recrutadores especializados e importação manual. **Todas nascem `UNVERIFIED`.**

**Estado de autorização (por fonte) — proposta:**
`UNVERIFIED` (padrão) · `NOT_AUTHORIZED` · `MANUAL_ONLY` (apenas o que o usuário traz) ·
`AUTHORIZED_API` · `AUTHORIZED_FEED`. O estado só muda com **evidência** (URL da documentação/termos,
data, quem verificou) e pode expirar para reverificação.

**Configuração independente por fonte:** capacidades, matriz de permissão por operação, autenticação
(guarda **referência** a segredo — variável de ambiente/cofre —, nunca o segredo no banco), limites
(taxa, volume), política de erros e retentativas, workflow vinculado, saúde.

**Operações restritas** (exigem autorização explícita): coleta automatizada, leitura de detalhe em
massa, submissão de candidatura, envio de mensagem. Operação não suportada **ou** não autorizada é
recusada com erro de domínio próprio, mesmo que o adaptador a implemente.

**Critérios de aceite (D3):**
1. Fonte nova nasce `UNVERIFIED` com todas as operações restritas desabilitadas.
2. Teste prova que service recusa operação restrita para `UNVERIFIED`/`NOT_AUTHORIZED`/`MANUAL_ONLY`.
3. Nenhum segredo persistido em claro; nenhum segredo em log.
4. LinkedIn/Indeed/InfoJobs aparecem no registro como `UNVERIFIED` e **sem código de coleta** até a verificação.

### B. Source Adapter Contract

Contrato (Protocol em Python, a definir na D3):

| Membro | Definição |
|---|---|
| `source_id` | Identificador estável da fonte no registro. |
| `capabilities` | Conjunto declarado do que o conector *sabe* fazer (ex.: listar, detalhar, importar arquivo). |
| `supported_operations` | Operações implementadas. Efetivas = `supported ∩ autorizadas` no registro. |
| `authorization_status` | **Lido do registro**; o adaptador não pode autodeclarar-se autorizado. |
| `normalization` | Função **pura e determinística** `raw → NormalizedJob`, versionada. |
| `provenance` | `source_id`, `external_id`, URL, `captured_at`, método, versão do adaptador, hash do payload bruto. |
| `health` | Estado (`OK`/`DEGRADED`/`DOWN`/`UNKNOWN`), último sucesso, último erro. Sem rede ⇒ `UNKNOWN`, nunca `OK` presumido. |
| `error_mapping` | Erros da fonte → taxonomia interna (autenticação, limite, indisponível, formato, permissão…). |

**Conformidade:** suíte de testes que todo adaptador precisa passar. O adaptador de **importação
manual** é a implementação de referência. Testes não fazem chamadas de rede.
Conectores sem autorização permanecem desabilitados para operações restritas (P1).

### C. Workflow Orchestrator

Mecanismo comum, cinco definições. Cada definição declara **estados, transições, ações disponíveis,
pontos de confirmação humana e eventos auditáveis**. O envelope de evento acrescenta: `workflow_type`,
`workflow_version`, ator (`user`/`system`), confirmação (sim/não, quando) e metadados.

> Os estados abaixo são **rascunhos para validar na D6**, não decisão final.

| Workflow | Estados (rascunho) | Confirmação humana obrigatória |
|---|---|---|
| **1. Portal de emprego** | DISCOVERED → QUALIFIED → PREPARED → READY → APPLIED → RESPONSE → INTERVIEW → TECHNICAL → OFFER; saídas REJECTED / WITHDRAWN / GHOSTED. (É o fluxo hoje implementado na D1.3.) | Marcar READY (currículo final); registrar APPLIED. |
| **2. Página oficial da empresa** | Mesmo pipeline do portal, mais verificação de autenticidade da vaga e do canal. | Idem. |
| **3. Contato com recrutador** | RECRUITER_IDENTIFIED → CONTACT_DRAFTED → CONTACT_APPROVED → CONTACTED (ou INBOUND_RECEIVED) → CONVERSATION → OPPORTUNITY_SHARED → QUALIFIED → … → INTERVIEW / OFFER; saídas CLOSED / DECLINED. | Enviar qualquer mensagem; compartilhar currículo ou dados pessoais; registrar consentimento. |
| **4. Candidatura espontânea** | TARGET_IDENTIFIED → CONTACT_PATH_FOUND → MESSAGE_DRAFTED → MESSAGE_APPROVED → SENT → FOLLOW_UP_DUE → RESPONSE → CONVERTED_TO_OPENING / CLOSED. Começa **sem vaga**. | Aprovar e enviar mensagem; cada follow-up. |
| **5. Importação manual** | IMPORTED → REVIEWED → CLASSIFIED (canal definido) → converge para o workflow 1 ou 2. | Classificar canal; confirmar dados importados. |

**Critérios de aceite (D6):** transições inválidas rejeitadas por definição; toda transição gera evento
imutável; ações externas só executam após confirmação registrada; reconstruir a trajetória de uma
oportunidade só pelos eventos.

### D. Target Sector Intelligence

- **Setores iniciais:** Banking & Fintech · Startups · Software Houses · Consultorias de tecnologia.
  Taxonomia **extensível** (dados, não enum); uma empresa pode ter mais de um setor.
- **Campanha de busca por setor:** setor(es), critérios, período, canais usados.
- **Comparação:** taxa de resposta, entrevistas e ofertas por setor, com **n absoluto** sempre visível e
  rótulo "amostra insuficiente" abaixo de um mínimo configurável. Sem ranking, sem favorito presumido.
- **Limiar exploratório:** 20 candidaturas por setor. Abaixo disso a UI mostra "amostra insuficiente"; a partir disso o
  rótulo é **"exploratório"** — sem testes de significância, sem "vencedor" e sem alegações estatísticas conclusivas.
- O setor do evento é **fotografado** no momento do evento (reclassificar uma empresa não reescreve a história).

### E. Headhunter CRM

Entidades futuras (nomes do adendo; campos a detalhar na D6):

| Entidade | Papel / campos candidatos |
|---|---|
| `Recruiter` | Nome, canais de contato, organização, **proveniência** (como e quando o contato foi obtido), estado de consentimento. |
| `RecruiterOrganization` | Agência/consultoria/empresa, tipo, site. |
| `RecruiterSpecialization` | Áreas/setores/senioridades em que atua (N:N). |
| `RecruiterInteraction` | Histórico **append-only**: data, canal, direção, resumo, ator. |
| `RecruiterOpportunity` | Liga recrutador ↔ vaga/oportunidade (e candidatura, se houver), com estado. |

**Política de retenção (obrigatória, documentada antes da D6):** prazo por tipo de dado, revisão periódica,
expurgo/anonimização ao fim da finalidade. **Dados profissionais mínimos**, com finalidade explícita por registro.

**Privacidade e consentimento:** coletar o mínimo; registrar finalidade e base de tratamento;
consentimento com data de concessão e revogação; exportar e apagar/anonimizar dados de um contato sem
quebrar o histórico agregado. **Não há envio em massa** — nem endpoint, nem job: cada mensagem é
individual, com confirmação humana e limite de taxa.

### F. Resume Template Registry

**Templates:** ATS Classic · Software Engineer · Internship / First Job · Corporate Technology ·
International English Resume.

**Três camadas separadas:**
1. **Fatos** — Master Profile (D2): entradas com ID estável e verificação.
2. **Plano de conteúdo** — quais fatos entram, em que ordem e com qual ênfase para uma vaga-alvo; cada
   frase gerada guarda os IDs de fatos que a sustentam (**ledger de afirmações**).
3. **Apresentação** — template versionado (layout, tipografia, seções) que apenas renderiza o plano.

Trocar de template **não** altera fatos nem plano. Cada `ResumeVersion` guarda plano, versão do
template e referências aos fatos usados, de modo reproduzível e auditável.

### G. Resume Quality Gate

| Verificação | Tipo | Severidade |
|---|---|---|
| Factualidade: toda afirmação mapeia para fato do Master Profile | determinística | **bloqueante** |
| Ausência de experiências/credenciais inventadas | determinística (conjunto de fatos × ledger) | **bloqueante** |
| Informações de contato presentes e válidas | determinística | **bloqueante** |
| Integridade do arquivo exportado (abre, hash, páginas, fontes embutidas) | determinística | **bloqueante** |
| Extração textual do PDF: texto extraído ≈ texto do plano | determinística | **bloqueante** acima do limiar |
| Organização (seções esperadas, ordem, datas coerentes) | determinística | aviso |
| Legibilidade (comprimento, tamanho mínimo de fonte, densidade) | heurística determinística | aviso |
| Compatibilidade com requisitos relevantes (cobertura de MUST_HAVE que o perfil sustenta) | determinística (D4) | informativa |

Resultado: **relatório persistido por versão**; exportação só liberada sem bloqueantes. Qualquer
verificação assistida por IA seria complementar, nunca substitui as bloqueantes.

### H. Duplicate Intelligence

- Uma oportunidade (`Job`) tem **N links de origem** (`JobSourceLink`: fonte, `external_id`, URL,
  captura, proveniência). **Nenhum link é descartado**, mesmo após fusão.
- **Sinais:** empresa (normalizada + aliases), cargo normalizado, localização, identificador externo,
  similaridade textual determinística (ex.: shingles/Jaccard ou SimHash), com limiares configuráveis.
- **Política:** identificador externo/URL idênticos na mesma fonte ⇒ fusão automática; demais casos ⇒
  **sugestão** com score e explicação, aguardando confirmação humana. Fusão é **reversível** e auditada
  (evento com os links antes/depois).
- Critério de aceite: o mesmo anúncio em dois portais vira 1 oportunidade com 2 links; um falso positivo
  pode ser desfeito sem perda de dados.

### I. Analytics

Dimensões: fonte, canal/workflow, setor, campanha, modelo (e versão) de currículo, período.

| Métrica | Definição (numerador / denominador) |
|---|---|
| Oportunidades descobertas por fonte | contagem de oportunidades por `source_id` (links) |
| Vagas qualificadas | oportunidades que atingiram QUALIFIED / descobertas |
| Candidaturas realizadas | candidaturas que atingiram APPLIED (ou equivalente do workflow) |
| Taxa de resposta | com RESPONSE / candidaturas realizadas |
| Entrevistas | com INTERVIEW / candidaturas realizadas |
| Ofertas | com OFFER / candidaturas realizadas |
| Tempo até candidatura pronta | READY − DISCOVERED (a partir dos eventos) |
| Por setor / por modelo de currículo / por canal | as métricas acima, fatiadas |

Regras: derivadas dos **eventos append-only**; dimensões fotografadas no instante do evento; sempre com
`n`; nenhuma conclusão de "melhor" sem amostra mínima.

### J. Regra de implementação (resumo executável)

1. Sem integrações simuladas como reais. 2. Sem APIs inventadas. 3. Sem scraping ou automação contra as
regras. 4. Sem antecipar funcionalidades avançadas durante o fechamento da D1. 5. Cada conector começa
por uma ADR que cita a documentação/termos oficiais lidos e a conclusão sobre o que é permitido.

### K. Entidade conceitual `Opportunity` (aprovada; **sem migração na D1.5**)

Separa três conceitos que hoje estão fundidos em `jobs` e `applications`:

| Conceito | O que é | Relação |
|---|---|---|
| **Opportunity** | A chance profissional que o usuário persegue: uma vaga, um contato de recrutador ou uma empresa-alvo para candidatura espontânea. Unidade de decisão, deduplicação e funil. | 1 |
| **JobPosting** (publicação de vaga) | Um anúncio concreto numa fonte: `external_id`, URL, texto, proveniência. | N por Opportunity (o mesmo anúncio em vários portais) |
| **Application** (candidatura) | O ato de se candidatar/abordar por um canal, com currículo e eventos. | N por Opportunity (canais/tentativas); regra de unicidade definida na ADR |

Mapeamento atual: `Job` ≈ Opportunity + JobPosting fundidos; `Application` ≈ candidatura 1:1 com `Job`.

Regras conceituais:
- A deduplicação (H) **funde postings na mesma Opportunity** e nunca apaga postings nem links de origem.
- Recrutador e candidatura espontânea nascem como Opportunity **sem posting**.
- Analytics (I): "descobertas/qualificadas" contam Opportunities; "realizadas/respostas/entrevistas/ofertas" contam Applications.
- Os workflows (C) rodam sobre Opportunity (funil) e/ou Application (execução do canal) — a ADR decide a divisão.

**Isto não é decisão de schema.** Nomes, tabelas, se `jobs` é renomeada ou dividida e a unicidade de Application ficam
para a **ADR de Opportunity, no início da D3** (a deduplicação depende dela), com continuação na D6 (workflows).
Até lá, nenhum código novo deve assumir "Job = Opportunity" fora de repositories/services já existentes.

---

## 4. Análise de impacto sobre o que já existe (D1.1–D1.4)

Nada precisa mudar agora. Esta tabela registra **o que vai exigir migração/refatoração** para o time
(você) decidir com antecedência.

| Artefato atual | Limitação frente ao A01 | Fase | Ação prevista |
|---|---|---|---|
| `jobs.source` (texto livre) e `jobs.source_url` + índice único `uq_jobs_user_id_source_url` | Uma vaga tem um único link; não há registro de fontes nem proveniência. | D3 | **Depende da ADR de Opportunity (3.K).** Migration cria `job_sources` e links/postings, migra os valores atuais e move a unicidade para (fonte, `external_id`)/URL **nos links**. |
| `jobs.company` (string) | Sem entidade empresa, aliases ou setor. | D3 | Criar `Company` (+ aliases, setores); manter o texto como snapshot de exibição. |
| `applications.job_id NOT NULL` + `UNIQUE(user_id, job_id)` | Recrutador e candidatura espontânea podem não ter vaga. | D3 (ADR) / D6 | O agregado `Opportunity` (3.K) foi aprovado conceitualmente; a ADR define o schema antes de qualquer migration. |
| `ApplicationStatus` (enum + CHECK) e `TRANSITIONS` | Hoje é **um** workflow. | D6 | O módulo `app/domain/application_status.py` já é puro e isolado: vira a definição do workflow 1. CHECK por enum único deve ceder lugar a validação por definição de workflow. |
| `application_events` (append-only, trigger) | Falta `workflow_type`, versão, ator e confirmação. | D6 | Adicionar colunas preservando o trigger de imutabilidade. Base excelente para analytics. |
| `candidate_profiles` | **Sem dados de contato** (exigidos pelo Quality Gate). | D2 | Acrescentar e-mail, telefone, links públicos. |
| `candidate_skills/projects/experiences/educations` | Têm UUID, mas sem verificação/evidência. | D2 | Campos de proveniência e estado de verificação do fato. |
| `resume_versions` (`content` texto) | Sem template, plano, ledger, relatório do gate, hash do arquivo. | D5 | Migration com versão do template, plano, ledger, relatório e hash. |
| Inexistentes hoje | `Source*`, `Company`, `Sector`, `Campaign`, `Recruiter*`, templates, workflow definitions. | D3–D6 | Criar nas fases indicadas (seção 2). |
| Analytics: dimensões | Setor/fonte/canal/currículo não estão nos eventos. | D6–D7 | Fotografar dimensões no evento a partir do momento em que forem capturadas. |
| Segredos de fontes | Não há armazenamento seguro previsto. | D3 | Só referências (env/cofre) no banco. |
| Enums como CHECK | Cada novo valor exige migration. | contínuo | Já documentado em `database-schema.md`; para taxonomias abertas (setor, fonte) usar tabelas. |
| Privacidade | Dados de terceiros (recrutadores) elevam as obrigações. | D6 | Revisão LGPD antes da D6; escopo por `user_id` já existe. |

**Riscos arquiteturais registrados**
1. **Modelo "uma vaga = um link" é o maior débito** frente a H; a D3 começa por ele.
2. **Application acoplada a Job** pode forçar refatoração em cascata na D6 se a decisão de agregado chegar tarde.
3. **Taxonomia de status única** não sobrevive a cinco workflows; a refatoração é localizada, mas toca API, frontend e testes (`allowed_next_statuses` já ajuda, pois o frontend não duplica a política).
4. **Risco regulatório/contratual** (termos das plataformas, LGPD) é de natureza externa: mitigado por P1–P3, mas exige leitura dos termos reais e decisão sua; este documento não os interpreta.
5. **Escopo:** A01 é muito maior que a D3 sozinha; distribuir como na seção 2 e evitar adiantar D5/D6 durante a D3.

---

## 5. Perguntas

**Resolvidas (seção 0):** numeração D4–D8 · setores iniciais · limiar de amostra (exploratório) · política para dados de
recrutadores (mínimos + retenção documentada) · entidade `Opportunity` (conceito).

**Ainda em aberto:**
1. **Quais acessos legítimos você tem** em cada fonte-alvo (contas, APIs, feeds, programas de parceiros)? Sem isso, a D3 só
   entrega a importação manual; cada conector exige antes a leitura dos termos/documentação **oficiais** e a ADR.
2. **Prazos concretos de retenção** dos dados de recrutadores (a política é obrigatória; os números ainda não existem).
3. **ADR de Opportunity**: nomes, divisão de tabelas e unicidade de Application (início da D3).

---

## 6. Definição de pronto do registro do A01 (esta etapa)

- [x] Requisitos A–J registrados e distribuídos por fase.
- [x] Impactos sobre o código existente identificados (seção 4), sem alterá-lo.
- [x] Escopo e testes da D1.5 preservados.
- [x] Perguntas resolvidas e pendentes listadas; decisões do usuário registradas (seção 0).
