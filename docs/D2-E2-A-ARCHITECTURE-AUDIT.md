# Job Agent — D2-E2.A | Auditoria arquitetural e contrato da jornada do candidato

**Estado:** AUDIT + TARGET CONTRACT, sem implementação das novas rotas.  
**Branch:** `feature/d2-e2a-candidate-contract` (derivada de `feature/d2-e1-react-auth-ui`).  
**Não altera:** main, PR #2, PR #3, banco Codespaces `jobagent_react_test`, Alembic `0004`, migrations existentes, Stripe ou Resend real.  
**Contrato:** [d2-e2-candidate-journey.openapi.yaml](contracts/d2-e2-candidate-journey.openapi.yaml) — **proposta**, NÃO a especificação OpenAPI atualmente servida.

## 1. Inventário efetivamente inspecionado

| Camada | Código inspecionado | Capacidades observáveis | Lacuna para jornada única |
|---|---|---|---|
| FastAPI moderno | `backend/app/api/v1/router.py`, `auth.py`, `profile.py`, `jobs.py`, `applications.py` | /api/v1/auth/*, /profile, /jobs, /applications; sessão por Bearer, UUID, PostgreSQL, autorização por usuário | **Não expõe** importação, Fact Ledger, diagnóstico ou geração de currículo |
| Domínio moderno | `backend/app/models/candidate.py`, `resume.py`, `job.py`, `application.py` | Perfil básico; experiências/skills/projetos/educação como entidades; ResumeVersion e JobMatch persistentes; histórico de candidatura | ResumeVersion/JobMatch não têm serviço de geração/matching; entidades estruturadas de perfil sem API completa |
| React atual | `frontend/src/app/App.tsx`, `ProfilePage.tsx`, `JobsPage.tsx`, `JobDetailPage.tsx`, `ApplicationsPage.tsx` | Login e páginas protegidas; edição de perfil resumido; manutenção de vagas e candidaturas | Não há rotas/telas para upload, revisão, Fact Ledger, diagnóstico ou currículo |
| API legada | `production_api/main.py` | `/api/import/resume/{file-preview,preview,confirm}`; `/api/master-profile`; `/api/fact-ledger`; `/api/diagnostic/fact-grounded`; `/api/resume/grounded-draft` | IDs inteiros, modelo/sessão próprios, contrato /api não compatível diretamente com /api/v1 |
| Extratores legados | `production_api/resume_ingestion.py`, `resume_journey.py`, `resume_similarity.py` | PDF/DOCX/TXT, extração delimitada, segmentação conservadora, classificação de duplicatas | Formatos não padronizados e mudanças de cargo não são garantidos; parser não é módulo integrado |
| Evidência legada | `production_api/models.py` | `Evidence`, `MasterProfileItem`, `CareerFact` e `Session` | Entidades de outra base; não compartilhar usuários/sessões via cópia direta de tabelas |

### Evidências pontuais importantes

- `backend/app/api/v1/router.py` inclui somente `auth`, `profile`, `jobs`, `applications`. **Nenhum dos endpoints do contrato D2-E2 está implementado no backend moderno.**
- `backend/app/models/resume.py` descreve `ResumeVersion` como persistência sem geração de currículo. `JobMatch` em `backend/app/models/job.py` é persistência sem motor de matching no D1.
- `production_api/main.py` usa `current_user` baseado em `Session` (hash de token com `user_id` inteiro), enquanto o moderno usa `AuthSession`/UUID. **Não montar o módulo antigo diretamente no processo novo, nem expor conexão com o banco antigo.**
- `production_api/resume_ingestion.py` limita arquivos a 2 MB, PDF a 12 páginas, texto a 25 mil caracteres; PDFs escaneados sem camada textual não funcionam sem OCR.
- `production_api/resume_journey.py` usa heurísticas de títulos, bullets, espaços e datas, sem garantia de separar experiências. As sugestões são declaradas não verificadas.
- `production_api/resume_similarity.py` compara título e descrição, não identidade normalizada da empresa/cargo/período. Possíveis falsos positivos ao trocar de cargo na mesma empresa ou trabalhar em tarefas semelhantes.
- `production_api/main.py` atualmente exige confirmação de itens antes de criar `Evidence`, `MasterProfileItem`, `CareerFact`; deduplicação entre importações é heurística e transacional nesse sistema, **não equivale à mesma garantia no moderno**.
- Diagnóstico legado verifica presença textual de requisitos em fatos marcados `ACTIVE`; não comprova experiência nem calcula probabilidade de contratação. Currículo fundamentado retorna rascunho textual com `fact_id`, sem arquivo DOCX/PDF final.
- Backend moderno já tem histórico de eventos de candidaturas, transações e lógica de estado. Devemos **estender**, não reconstruir esse módulo.

## 2. Decisões arquiteturais propostas

**D2-E2-ADR-01: o backend moderno é o sistema de registro.**

Adotar `backend/app` com UUID, autenticação Bearer existente, `get_current_user`, PostgreSQL e Alembic como única autoridade de usuários e permissões. Extrair **algoritmos puros** da API legada para módulos de domínio/serviço novos, com adaptações de tipagem, testes e revisão. Não replicar credenciais legadas, não compartilhar arquivos SQLite ou banco produção e não implementar proxy opaco para a API antiga.

**D2-E2-ADR-02: modelo de fatos preserva origem e histórico.**

Cada fato ativo deve referenciar usuário e origem (importação confirmada, evidência ou declaração explícita), com estado `ACTIVE`/`SUPERSEDED`/`REJECTED`, versão e data, sem afirmar `EXTERNALLY_VERIFIED` sem verificador independente. Correções geram nova versão e tornam a anterior inelegível em diagnósticos/currículos futuros. Usar FK UUID e restrição de propriedade; tabelas reais serão decididas no D2-E2.B. Não duplicar tabelas já atendidas por `CandidateExperience`, `CandidateEducation`, `CandidateProject` e `ResumeVersion` sem ADR específico.

**D2-E2-ADR-03: preview separado da confirmação.**

Preview não persiste fatos. A confirmação exige identidade do usuário, referência verificável do preview com expiração, seleção/edição explícita, Idempotency-Key estável e transação única. A origem do preview deve ser vinculada ao usuário mesmo após reinícios; opções de implementação incluem registro efêmero no PostgreSQL com TTL, e não token autoafirmado pelo cliente. Contrato ainda não determina armazenamento — depende de avaliação de retenção, privacidade e UX. Arquivo bruto não é persistido por padrão.

**D2-E2-ADR-04: sem alegações de capacidades não verificadas.**

`USER_DECLARED` significa declaração do usuário. Menção em PDF não prova competência. Se existir score, ele mede **cobertura documental explicável**, nunca chance de contratação. `hiring_probability: null` é obrigatório no contrato. Geração de currículo só pode usar fatos ativos e do próprio usuário.

**D2-E2-ADR-05: lançamento desacoplado de fornecedores externos.**

MVP sintético sem Stripe, domínio e email transacional real. Endpoints privados e testes podem usar autenticação isolada existente, mas nenhum usuário real ou cadastro público será exposto até conclusão dos gates externos já documentados. Não reduzir proteções da D2-E1.

## 3. Mapeamento legado → novo (não é migração de dados)

| Conceito legado | Fonte em production_api | Alvo proposto em backend/app | Trabalho |
|---|---|---|---|
| `User.id` inteiro e `Session` | `models.py`, `main.py` | `User.id` UUID e `AuthSession` existentes | **Reutilizar autenticação moderna**; NÃO importar usuários do legado |
| `Profile` (name, target_role, salary etc.) | `models.py` | `CandidateProfile` e eventual extensão dos campos de objetivo | Reconciliar campos, privacidade e migrations aditivas depois |
| `Evidence` | `models.py` | Evidência confirmada e referência de origem vinculadas a usuário UUID | Definir destino antes de persistir |
| `MasterProfileItem` | `models.py` | `CandidateExperience`, `Education`, `Project`, `Skill` + referências | Mapear separadamente, não achatar diferentes experiências |
| `CareerFact` | `models.py` | Fato rastreável com versões e dono UUID | **Novo serviço/modelo**, sujeito a revisão D2-E2.B |
| `Job` e requisitos | `models.py` | `Job` + `JobRequirement` existentes | Reutilizar e oferecer API controlada para requisitos |
| Diagnóstico textual | `main.py` | Serviço de diagnóstico baseado em fatos ativos | Implementar versionamento, propriedade e interpretação por requisito |
| Currículo fundamentado | `main.py` | `ResumeVersion` existente + serviço gerador | Texto rastreável primeiro; exportação DOCX/PDF após validação |
| `Application` e pipeline | `models.py` | `Application` e `ApplicationEvent` existentes | Reutilizar transições/eventos atuais, vínculo a ResumeVersion |

## 4. Contrato REST alvo e condições de proteção

Fonte: `docs/contracts/d2-e2-candidate-journey.openapi.yaml` (OpenAPI 3.1 **draft**, não publicada na API).

| Rota proposta | Papel | Gate antes do primeiro PASS |
|---|---|---|
| `POST /api/v1/resume-imports/preview` | Upload seguro + itens de prévia | Auth, limites, tipos, não persistência, parser isolado |
| `POST /api/v1/resume-imports/confirm` | Confirmação idempotente | Preview expirável e vinculado ao dono, transação única |
| `GET /api/v1/career/profile` | Master Profile unificado | Dados por UUID, nenhuma relação cruzada |
| `GET /api/v1/career/facts` | Fact Ledger | Histórico só do dono; defaults ativos |
| `POST /api/v1/career/facts/{fact_id}/corrections` | Corrigir com histórico | Supersession atômica, IDOR test |
| `GET /api/v1/career/facts/contradictions` | Divergências conservadoras | Evitar falsos positivos por mudanças temporais legítimas |
| `POST /api/v1/career/diagnostics` | Diagnóstico por vaga | Requisitos/FK dono; null para chance de contratação |
| `POST /api/v1/career/resumes/drafts` | Currículo rastreável | 100% dos claims com fonte ativa, versão do currículo |

**Ainda não contratados:** API para editar rascunhos de experiências em tempo real, exportações, lifecycle de preview, paginação e edição de itens Master Profile. Definir com UX durante D2-E2.B/C, sem fingir suporte atual.

## 5. Matriz de riscos e testes RED

| Risco | Consequência | Teste mínimo que deve falhar antes da implementação |
|---|---|---|
| IDs legados vs UUID | Acesso cruzado/corrupção | Rotas novas só aceitam UUID e usuário moderno |
| Preview sem vínculo ao dono | Usuário B confirma dados A | Confirmar preview criado por A como B retorna 404/403 sem gravação |
| Retry ou concorrência de importação | Fatos duplicados | Mesma Idempotency-Key produz resultado estável e uma projeção |
| Duas experiências semelhantes | Fusão silenciosa | Empresa igual, cargos/datas distintos resultam em dois itens |
| Contradição por alteração legítima | Diagnóstico falso | Mudanças de cargo com períodos distintos não são 'falsidade' |
| Fato substituído em currículo | Informação desatualizada | Seleção de `SUPERSEDED` retorna 404/422, nunca texto antigo |
| URL/arquivo malicioso | SSRF, exaustão, parser crash | Nenhuma rede no parse, limites e falha segura |
| Diagnóstico como previsão | Propaganda enganosa | `hiring_probability` estritamente null |
| Candidatura 'preparada' exibida como enviada | Falsa ação | Status real e event log confirmam se houve aplicação |
| Quebra de compatibilidade com D2-E1 | Login ou sessões expostos | Suite de autenticação/limites mantida em regressão |

`backend/tests/unit/test_d2e2a_candidate_contract_red.py` contém nove verificações **strict xfail** para as novas rotas e uma verificação positiva de baseline. As xfails **não contam como funcionalidade implementada**; um XPASS fará falhar o CI até remover a marcação e fornecer testes verdadeiros de contrato/isolamento.

## 6. Execução segura e critérios de aceitação D2-E2.A

- Salvar este ADR, o contrato e testes RED isolados em **branch própria**, sem modificar o checkpoint anterior.
- Executar CI para sintaxe, Ruff, MyPy, backend/frontend regression e PostgreSQL efêmero **somente do GitHub Actions**. O banco de testes CI pode fazer upgrade/downgrade; **NUNCA** executar esse workflow destrutivo na base do Codespaces.
- D2-E2.A PASS somente com documentação e CI aprovados. D2-E2.B, imports e todo o fluxo permanecem PENDENTES.
- **Próximo checkpoint D2-E2.B:** decidir entidades/relacionamentos/índices com base no schema atual; escrever testes de propriedade e persistência com `*_test` temporário independente; desenhar migration `0005` de modo aditivo e revisá-la antes da aplicação.
- Não mexer em `jobagent_react_test`, porta `55435`, `APP_ENV=production`, PR #2, PR #3 ou `main`.

## 7. Retomada do Codespaces

A worktree atual `/workspaces/Job-Agent-D2-E1-UI` continua em `feature/d2-e1-react-auth-ui`/HEAD detached e serve à identidade. **Não fazer checkout da nova branch nessa worktree** enquanto estiver preservando a homologação anterior.

Quando houver necessidade de trabalhar localmente em D2-E2, criar **nova worktree** após inspecionar `git worktree list` e `git status`, com caminho próprio, sem `reset --hard` ou remoção de worktrees. Evitar qualquer comando de DB/migration até preparar o gate de D2-E2.B.
