# Gate de encerramento Q2.2 e segurança pré-beta — 2026-10-28

## Contexto e limites
Auditoria **estática** do código em `feature/q22-feedback-safe`; não é pentest, revisão exaustiva nem validação de produção. Criada em branch separada `audit/q22-security-beta-gates`. Nenhum banco, conta, container, migration, branch `main` ou PR #2 foi alterado.

## Evidências positivas diretamente observadas
- `production_api/main.py`: senha com Argon2; token de sessão de alta entropia, persistido apenas como SHA-256; validade de sete dias; revogação de sessões após troca de senha.
- Middlewares: CSP, `nosniff`, `frame-ancestors 'none'`, HSTS no ambiente production, `Cache-Control: no-store`, política de referrer.
- Endpoints privados normalmente exigem `current_user`; há helper de propriedade `owned` para objetos identificados por ID.
- Stripe webhook verifica assinatura e registra ID do evento para deduplicação; consulta estado remoto para assinatura.
- Importação de arquivo lê até `MAX_BYTES+1` antes da extração; endpoint declara não persistir arquivo bruto.
- Frontend cria texto dinâmico majoritariamente via `textContent`, reduzindo exposição a HTML arbitrário. **Não equivale a auditoria XSS completa.**

## Bloqueios / verificações obrigatórias antes de ativar beta pagante

### G1 — homologação Q2.2 visual (pendente)
- Evidência automatizada relatada: 45/45 (38 testes auxiliares + 7 Playwright com API simulada).
- Arquivo **`q22-feedback-mobile-375.png`** ainda não foi revisado. Captura `b52-q1-mobile-375.png` corresponde à Q1, portanto não substitui Q2.2.
- Inspecionar erro, retry, confirmação e estados `aria-live` em desktop/mobile, inclusive ações que desmontam botão após `show()`.
- Não promover PR #2 de draft enquanto pendente.

### G2 — isolamento de autorização (pendente)
- Rodar testes de duas contas descartáveis A e B no PostgreSQL **descartável**, cobrindo GET/POST/PUT/DELETE sobre evidências, vagas, tarefas, candidaturas, perfil mestre, fact ledger, exportação e premium.
- Garantir 401 sem token, 403/404 sem recurso de A ao acessar como B, e nunca retorno de dados cruzados. Validação de código isolada não comprova esta matriz.

### G3 — segurança de sessão e dados privados (pendente)
- Frontend usa Bearer token em `sessionStorage`. Conferir proteção XSS de todos os caminhos de renderização; CSP ajuda mas token permanece legível por JS da mesma origem.
- Confirmar limpeza de tokens, drafts e estados privados em logout, expiração, troca de conta, encerramento de sessão, troca de senha e exclusão de conta. Evitar que dados de A persistam visíveis em B após navegação assíncrona.
- Testar invalidação real no servidor (logout e troca de senha) com duas sessões descartáveis.

### G4 — defesa de abuso e autenticação (pendente)
- Limitador de login/cadastro atual é **por IP em memória de processo** (`defaultdict(deque)`, janela 60 s, limite 10); não é distribuído. Em várias instâncias ou após restart, a defesa recomeça.
- Adotar e comprovar proteção de gateway distribuída, limites de corpo/uploads, logs sem dados sensíveis e auditoria de tentativas, conforme arquitetura real de deploy.
- Testar registro, falha de senha, tentativas repetidas, resposta 429 e configuração HTTPS + HSTS.

### G5 — cobrança e encerramento (pendente)
- Homologar Stripe em **test mode**, sem pagamento real: checkout, repetição, webhook assinado, entrega fora de ordem, evento duplicado, atualização de status, portal, cancelamento e revogação de premium.
- Verificar política de exclusão para usuário com assinatura ativa: código hoje retorna 409 e exige resolução de assinatura no Stripe, o que deve ser explicado claramente ao cliente.
- Testar exclusão permanente apenas de **conta descartável**, após validação de exportação e consentimento. Não usar contas/bancos de produção.

### G6 — privacidade e suporte (pendente)
- Documentar finalidade, retenção e exclusão de currículos/dados pessoais, privacidade conforme LGPD, transparência de IA e canal de suporte, sem promessas de emprego.
- Confirmar segurança e restauração de backups e monitoração de erros sem currículo/texto confidencial; não pressupor backup externo configurado.

## Aceite antes do beta pagante
- Q2.2: captura inspecionada + QA real e PR revisado.
- Segurança: G2–G5 aprovados em ambiente descartável com evidência (status, logs redigidos, testes), sem tocar produção.
- Comercial/legal: oferta, pagamento em test mode, termos/privacidade, suporte e cancelamento compreensíveis.
- Revisão de arquitetura e risco restante registrada; decisão explícita antes de merge ou deploy.

## Comandos seguros de retomada (worktree Q22)
```bash
cd /workspaces/Job-Agent-Q22
git status --short --branch
node --check production_api/web/app.js
node production_api/tests/verify_q22_action_feedback.cjs
node production_api/tests/verify_q22_feedback.cjs
node production_api/tests/verify_b52_q1_navigation.cjs
JOB_AGENT_PLAYWRIGHT_ROOT=/workspaces/Job-Agent node production_api/tests/verify_q22_browser_isolated.cjs
```
Essas verificações são *mock/static*, não substituem backend real. Captura gerada localmente: `q22-feedback-mobile-375.png`; preservar seu arquivo untracked.

## Decisão atual
**Q2.2: implementação e testes simulados satisfatórios; homologação completa PENDENTE.**
**Segurança beta pagante: NÃO APROVADA enquanto gates não forem testados.**
Não alterar `main` ou realizar merge do PR #2 sem aprovação expressa.
