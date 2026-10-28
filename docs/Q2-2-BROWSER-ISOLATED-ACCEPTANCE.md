# Q2.2 — Homologação no navegador completamente isolada

## Isolamento
A suíte `production_api/tests/verify_q22_browser_isolated.cjs` abre um servidor HTTP temporário em `127.0.0.1` com porta aleatória para os assets da **worktree Q22**, intercepta todas as requisições `/api/*` com Playwright e responde **somente com objetos fictícios em memória**. Não acessa FastAPI, PostgreSQL, Docker, ambientes originais, contas reais ou tokens reais. A suíte termina fechando o navegador e o servidor.

## Cenários
1. Erro na prévia de vaga, com mensagem específica e preservação da descrição.
2. Repetição da operação e recuperação após 503 fictício.
3. Desabilitação do botão durante a execução; rejeição de cliques simultâneos.
4. Erro de carregamento de tarefas, botão de retry único e recuperação.
5. Inclusão de tarefa simulada e atualização visível na interface.
6. Layout a 375px, captura `q22-feedback-mobile-375.png` e checagem de overflow horizontal.
7. Nenhuma exceção JS não tratada.

## Execução
No Codespaces, na pasta isolada `/workspaces/Job-Agent-Q22`:

```bash
cd /workspaces/Job-Agent-Q22
git fetch origin feature/q22-feedback-safe
git switch -c q22-browser-validation origin/feature/q22-feedback-safe
node --check production_api/tests/verify_q22_browser_isolated.cjs
JOB_AGENT_PLAYWRIGHT_ROOT=/workspaces/Job-Agent node production_api/tests/verify_q22_browser_isolated.cjs
```

O teste procura Playwright na própria worktree ou em `/workspaces/Job-Agent/node_modules`, onde a versão anterior da suíte foi instalada. Não executar `npm install` na pasta original se o módulo já estiver presente.

Se preferir manter a worktree em detached HEAD, substitua `git switch -c` por `git checkout --detach origin/feature/q22-feedback-safe` **apenas se `git status --short` estiver vazio**; não descarte alterações não commitadas.

**Aceite:** `RESULTADO: 7/7 | STATUS: PASS` e inspeção manual da captura. O teste é um browser E2E da UI com API mock, não prova persistência/autorização no backend.
