# JOB AGENT — CHECKPOINT INTEGRAL D2-E2.D.1-C

**Data:** 2026-11-01 (Brasil; CI executado em UTC no início de 2026-11-02)  
**Repositório:** Arthur-Levi/Job-Agent  
**Branch ativa:** `audit/d2-e2d1-security-acceptance`  
**Commit técnico de referência (antes deste relatório):** `c0b1e619cdac963fe076407b109d6d522ae373f7`  
**PR de trabalho:** https://github.com/Arthur-Levi/Job-Agent/pull/9 (OPEN, DRAFT, não merged)  
**PR de base:** https://github.com/Arthur-Levi/Job-Agent/pull/8 (OPEN, DRAFT)  
**Origem de importação:** PR #7 D2-E2.C, ainda DRAFT.  
**Política:** preservar `main`, bancos PostgreSQL existentes, volumes, arquivos de usuários e configuração de pagamentos.

## 1. Decisão

**CHECKPOINT DO CÓDIGO: PASS CONDICIONAL. BETA / PRODUÇÃO: NO-GO.**

A implementação acumulada da branch está persistida no GitHub e passa na suíte CI do commit técnico de referência. NÃO significa que o sandbox esteja homologado como infraestrutura externa de produção, nem que o fluxo de usuários reais esteja aprovado.

## 2. Evidências realmente observadas

GitHub Actions: https://github.com/Arthur-Levi/Job-Agent/actions/runs/41370338832

- `backend`: **SUCCESS** — **296 passed, 3 xfailed, 1 warning**.
- `frontend`: **SUCCESS** (lint, build e testes do pipeline).
- `sandbox-smoke`: **SUCCESS** (imagem de parser isolada, currículo sintético, bloqueio de escrita em filesystem protegido e de saída de rede verificados no runner descartável).
- `audit`: **SUCCESS** como job informativo; `continue-on-error: true` no workflow — não interpretar como garantia de ausência de vulnerabilidades.
- Ruff, `ruff format --check`, MyPy e validação Alembic no CI: aprovados.
- Os testes usaram PostgreSQL efêmero provisionado pelo CI. **Não foi executado qualquer reset/migration no banco persistente do Codespaces por este trabalho.**

## 3. Entregas acumuladas na branch

### D2-E2.D.1-A — integridade do Fact Ledger
- `career_import.py`: bloqueio transacional em `users` por usuário ANTES das leituras de chave de idempotência e fatos ativos.
- `career_facts.py`: mesma ordem de bloqueio; histórico de correção mantido; correção de descrição importada preserva JSON estruturado (cargo, empresa e período).
- Teste de importação concorrente usando sessões PostgreSQL independentes; limpeza de registros sintéticos persistidos após o teste.
- Confirmar em próximos testes corridas de correção vs. importação, mesma chave simultânea e invariantes do histórico.

### D2-E2.D.1-B — parser containerizado (protótipo)
- `backend/Dockerfile.resume-parser` e `backend/.dockerignore`: imagem mínima e contexto whitelist.
- `resume_worker.py`: subprocesso legado apenas em dev/test; modo contêiner local com `--network=none`, `--read-only`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, sem mounts, usuário não root e cotas CPU/memória/processos.
- `scripts/d2e2d1_sandbox_smoke.py` + CI: teste sintético com Docker efêmero, negação de rede e escrita, sem dados reais.

### D2-E2.D.1-C — limites e broker privado
- Limite de **2 parsers por processo de API** com rejeição `CV_PARSER_BUSY`; NÃO é quota distribuída.
- Leitura incremental de stdout do parser com cap de 130 KB e deadline monotônico; interrupção de processo acima do limite.
- `RESUME_PARSER_MODE=broker`: cliente de socket Unix local, framing com tamanho máximo, sem comandos Docker transmitidos pela API.
- `backend/app/workers/resume_broker.py`: executor separado com comando Docker fixo, apenas socket Unix e sem listener TCP; diretório privado e socket 0600; no máximo 2 execuções por instância; resposta limitada.
- Testes unitários do protocolo, sobrecarga, negativa de conexão e respostas sintéticas.
- **Importante:** broker é protótipo de staging. Testes não comprovam isolamento de identidades e permissões de socket em ambiente real.
- O endpoint de upload continua **503 `CV_SANDBOX_REQUIRED` em `APP_ENV=production`**. Não remover este gate nesta branch.

### D2-E2.C/D — já existente na base (não reinterpretar como funcionalidades novas)
- Preview autenticado de PDF/DOCX/TXT com parser ATS conservador e revisão humana.
- `POST /resume-imports/confirm` com ticket assinado, chave de idempotência, registro transacional e Fact Ledger.
- Master Profile derivado de fatos ativos e revisão de fatos, sem afirmar verificação externa dos dados declarados.
- Testes de API, integração e PostgreSQL de base.

## 4. Riscos e pendências bloqueadoras

1. **Isolamento operacional real:** implantar broker em identidade separada, com acesso controlado ao runtime de contêineres, restringindo socket cliente e impedindo Docker socket na API pública. Verificar rootless / seccomp / AppArmor / limites por host. Arquitetura ainda não foi implantada ou homologada em infraestrutura real.
2. **Admission control distribuído:** impor cotas globais e por usuário entre instâncias; processo local e broker local não são controles suficientes.
3. **Resiliência do broker:** supervisão, cancelamento completo, timeout e limpeza de contêineres órfãos, recuperação após crash, logging sem PII e comportamento com muitos clientes.
4. **Parser adversarial:** testes com arquivos sintéticos malformados, PDFs difíceis, ZIP expansion, timeout, memória, tentativas de rede e limites; sem enviar arquivos reais.
5. **Confiabilidade transacional:** corridas de mesma chave, correção simultânea, conflito entre fontes, comprovação multiusuário e histórico de correções de todos os campos estruturados.
6. **LGPD / privacidade:** exportação e exclusão de dados, retenção, backups, restauração, direitos de titulares, proteção do ticket assinado (que não é criptografado), termos e observabilidade.
7. **Produto ponta a ponta:** registro/login, upload/review/confirm, Master Profile, Career Diagnostic com Fact Ledger, ATS Check explicável, geração de currículo fundamentado e exportação PDF/DOCX, matching de vagas, UI mobile e recuperação de erro.
8. **Operação comercial:** deploy, domínio/TLS, rate limit distribuído, métricas, suporte, onboarding, cobrança Stripe robusta antes de beta pago, cancelamento e retenção.

## 5. Roadmap de retomada (ordem preservada)

- **D2-E2.D.1-C (pendente operacional):** service separation e deploy do broker, cotas compartilhadas e testes de falha.
- **D2-E2.D.1-D:** aceitação E2E completa com dados sintéticos e PostgreSQL **exclusivamente descartável**; revisar constraints, correções e restauração.
- **D2-E2.E:** Career Diagnostic e ATS intelligence fundamentados em fatos, fontes e limites claros.
- **D2-E2.F:** currículo fundamentado, exportação e matching explicável sem inventar experiências.
- **Beta Acceptance:** segurança, privacidade, operação, atendimento e 10 usuários convidados; cobrar somente após liberação expressa dos controles de pagamento e consentimentos adequados.

Regra comercial de aprendizado: validar **10 clientes que encontram valor e renovariam** antes de escalar; referência de precificação planejada R$ 299/mês, **não** receita já realizada.

## 6. Retomada segura do Codespaces

```bash
cd /workspaces/Job-Agent-D2-E2D-AUDIT
git status --short
git branch --show-current
git fetch origin
git merge --ff-only origin/audit/d2-e2d1-security-acceptance
git log -1 --oneline
git status --short
```

**Não executar** `pytest backend/tests/integration`, `alembic upgrade head`, resets de schema, `docker compose down -v` ou mudanças em `DATABASE_URL` apontando para bases preservadas. O `conftest.py` dos testes de integração pode executar `DROP SCHEMA public CASCADE` em banco `*_test`. Para homologar, provisionar um PostgreSQL novo, único e descartável e provar a URL e a conexão antes de qualquer comando destrutivo.

## 7. Critério para alteração futura deste checkpoint

Checkpoint é uma fotografia rastreável. Evoluir em branch de trabalho separada; só declarar PASS final após evidências reproduzíveis e revisão dos riscos. Não fazer merge direto na main, não liberar produção, não conectar currículos reais ou pagamentos a esta fotografia.
