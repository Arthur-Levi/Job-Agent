# Frontend (D1.4)

React 19 + TypeScript (strict) + Vite + Tailwind 4 + React Router 7. Sem biblioteca de estado ou
de data fetching: um hook (`useApiQuery`) cobre o que o D1 precisa. Tema escuro fixo (sem toggle).

## Estrutura (`src/`)
| Pasta | Conteúdo |
|---|---|
| `app/` | `App` (rotas), `AppShell` (cabeçalho + navegação + `ErrorBoundary`) |
| `pages/` | uma página por rota: Dashboard, Profile, Jobs, JobDetail, Applications, NotFound |
| `features/` | componentes e lógica por domínio (`jobs/`, `applications/`, `profile/`, `dashboard/`); a lógica pura dos formulários fica em `*FormModel.ts` |
| `components/` | UI genérica: `AsyncView`, `States` (Loading/Error/Empty), `Field`, `Button`, `Pagination`… |
| `services/` | `http.ts` (cliente) + um módulo por recurso (`jobsApi`, `applicationsApi`, `profileApi`) |
| `hooks/` | `useApiQuery`, `useSubmit`, `useUrlFilter` |
| `types/` | contrato da API (espelha os schemas Pydantic) |
| `utils/` | formatação, erros, estilos de status |

## Cliente HTTP (`services/http.ts`)
- URL base de `VITE_API_URL`; **nenhum `fetch` fora deste arquivo**.
- Envia `X-Request-ID` (UUID; com fallback fora de contexto seguro) e devolve o ID nos erros.
- Todo erro vira `ApiError { status, code, message, details, requestId }`:
  envelope do backend → campos do envelope; corpo não-JSON → `HTTP_<status>`;
  falha de rede → `NETWORK_ERROR` (status 0); excesso de tempo (15 s) → `TIMEOUT`.
  Cancelamento pelo chamador (`AbortSignal`) é relançado como `AbortError` e ignorado pelas telas.
- Dinheiro é `string` de ponta a ponta; só `formatSalary` converte, e apenas para exibição.

## Estados de tela
`AsyncView` + `useApiQuery` entregam **loading / error / empty / success** em toda tela que lê a API:
- erro mostra mensagem, `Request ID` e "Try again"; falha de rede tem texto próprio;
- `reload` mantém os dados anteriores visíveis (opacidade reduzida) até chegar a resposta nova;
- respostas de buscas antigas ou canceladas são descartadas;
- `ErrorBoundary` impede tela em branco por erro de renderização;
- formulários: validação local por campo + erros 422 do backend mapeados para o campo certo;
  demais erros viram um banner.

## Decisões
- **Política de status só no backend.** O seletor oferece `allowed_next_statuses` (vindo da API);
  os demais status aparecem como "Correct (forced)", com confirmação, e enviam `force: true`.
- **Dashboard** usa `total` de listas com `limit=1` (5 requisições em paralelo). "Interviews" = `INTERVIEW` + `TECHNICAL`.
- **Filtros de status na URL** (`?status=READY`): links do dashboard e recarga funcionam.
- Campos opcionais em branco viram `null`; no PATCH isso limpa o valor no banco.

## Testes
`npm test` roda ~65 testes (Vitest + Testing Library): cliente HTTP, hook, modelos de formulário,
utils e as páginas nos 4 estados. O **teste de contrato** (`services/contract.live.test.ts`) fica
desligado por padrão; contra um backend real (use banco descartável, ele grava dados):

```bash
VITE_LIVE_CONTRACT=1 VITE_API_URL=http://127.0.0.1:8000 npm test -- contract
```

Ele confere os enums do frontend contra o `/openapi.json`, o formato das respostas e o mapeamento dos erros.
