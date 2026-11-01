# Job Agent — D2-E1.5.2 | Email transacional (Resend)

**Situação:** implementação da API Resend + testes de transporte simulado. **Entrega real não homologada**: sem chave do provedor, domínio verificado, ambiente staging e testes de recebimento, a D2-E1.5.2 não pode ser marcada como operacional PASS.

**Não repetir** migrations já homologadas, scripts de reset de schema ou provas operacionais anteriores. O código não exige migration nova. O banco descartável Codespaces continua em `0004`, conforme a última evidência do operador.

## Decisões de arquitetura

- Primeiro provedor: **Resend**, endpoint fixo HTTPS `POST https://api.resend.com/emails`, com `Authorization: Bearer`, `Idempotency-Key` e JSON `from`, `to`, `subject`, `text`. A resposta válida tem HTTP 200 e `id`.
- Nenhum SDK externo ou nova dependência de runtime: transporte HTTPS via biblioteca padrão Python `urllib.request`.
- Credencial `RESEND_API_KEY` em variável de ambiente/secret manager; `SecretStr` impede exibição em validação. `ResendMailer.api_key` omite o campo no `repr`. Não salvar a chave no Git, log, issue, PR ou chat.
- URL do provedor imutável e redirecionamentos HTTP proibidos para impedir encaminhamento do bearer a outro destino.
- Idempotência SHA-256 derivada do corpo exato do email. Repetições do mesmo envio usam **a mesma** chave, sem gravar o token bruto em logs ou no banco. Esse header não oferece controle eterno: o provedor tem janela de idempotência.
- Até 3 tentativas totais, apenas em erros HTTP **429, 500, 502, 503, 504** ou falha transitória de rede, com intervalo curto e timeout de 5 s por tentativa; erros 400/401/403/409/422 e redirecionamentos não são repetidos.
- Sem cópia de detalhes de erros da Resend para a API. Falha de entrega produz `EmailDeliveryUnavailable` genérico; o token emitido é marcado como consumido na base, mantendo o cadastro não verificado e permitindo solicitar novo link depois. Requisições públicas continuam genéricas; logs exibem somente o tipo da falha.
- `MemoryMailer` permanece apenas para teste, e `EMAIL_DELIVERY_MODE=memory` é proibido quando `APP_ENV=production`.
- `disabled` continua sendo o padrão e a configuração de ciclo de identidade exige um transporte habilitado. Produção ainda requer revisão humana de HTTPS, proxy, rate limiting, monitoramento e política de contas legadas.
- **Limitação importante:** envio síncrono, sem fila/outbox persistente, tracking de entrega, webhooks validados ou observabilidade de bounce. A Resend aceitar HTTP 200 **não prova** recebimento na caixa postal. Essas lacunas são gates de publicação.

## Variáveis de configuração

```dotenv
APP_ENV=test
IDENTITY_LIFECYCLE_ENABLED=true
REGISTRATION_PRIVACY_ENABLED=true
EMAIL_DELIVERY_MODE=resend
PUBLIC_FRONTEND_URL=https://staging.example.com
EMAIL_FROM_ADDRESS=Job Agent <conta@seu-dominio-verificado.example>
# RESEND_API_KEY é um segredo: definir exclusivamente no Secret Manager
```

Os endereços são placeholders, nunca destinatários reais. `DATABASE_URL` é obrigatório em ambiente já configurado: não copiar este exemplo como arquivo .env completo. Para staging público real, usar HTTPS, domínio verificado e `AUTH_RATE_LIMIT_ENABLED=true` com segredo persistente. Não usar APP_ENV=production para o teste local.

## Homologação com chave real — somente staging autorizado

1. Criar/verificar domínio remetente no painel Resend. Configurar DNS SPF/DKIM/DMARC conforme os registros efetivamente fornecidos pelo provedor; comprovar status de verificação.
2. Criar uma chave específica de staging com permissões mínimas de envio, guardada como segredo no gerenciador de credenciais; nunca mostrar seu valor no terminal.
3. Hospedar staging com `PUBLIC_FRONTEND_URL` HTTPS real. Impedir acesso direto ao FastAPI, reescrever cabeçalhos de proxy, configurar CORS explícito e proteger rate limits.
4. Usar contas de email de **teste sob seu controle**: confirmar recebimento real do email e redirecionamento correto ao frontend, sem divulgar token, header de autenticação ou URL completa.
5. Confirmar entrega para verificação e reset; validar clique/consumo de token, repetição negada, expiração e revogação de sessões. Se possível, coletar evento de entrega validado da Resend (não confundir aceite de API com entrega).
6. Validar indisponibilidade do provedor, erros 429 e condições de concorrência multiworker. Não reenviar a mesma mensagem com novo identificador de idempotência em resposta a timeout.
7. Somente após aceite documental, considerar `D2-E1.5.2 OPERATIONAL PASS`. Não tirar PR #3 do Draft antes dos outros gates de segurança.

## Testes sem provedores externos (reexecutáveis via CI seguro)

- `backend/tests/unit/test_d2e152_email_delivery.py`: mocks de API HTTP, cabeçalhos, payload sem HTML, chaves de idempotência, retries delimitados, erros não-repetíveis, falhas de rede, validação de configuração e ausência de requests reais.
- `backend/tests/acceptance/test_d2e151_identity_lifecycle.py`: extensão que força falha do transporte e confirma que os tokens emitidos ficam consumidos; respostas públicas continuam idênticas.
- CI existente mantém `ruff check .`, `ruff format --check .`, `mypy`, `pytest`, frontend lint/build/Vitest, auditoria informativa; banco CI `job_agent_test` é temporário e DESCARTÁVEL. Nada de `pytest` diretamente no `jobagent_react_test` do Codespaces.

## Referências do provedor

- API OpenAPI oficial: https://github.com/resend/resend-openapi/blob/main/resend.yaml
- Chaves de idempotência: https://resend.com/changelog/idempotency-keys
- Segurança: segredos não versionados, domínio verificado, eventos webhook de entrega com assinatura antes de serem aceitos.

## Critérios PASS / pendências

- [x] Adapter Resend com endpoint fixo HTTPS, autenticação bearer e remetente configurável
- [x] Idempotency-Key estável e retry limitado
- [x] Redirecionamentos proibidos
- [x] Segredo fora dos logs e da representação do objeto
- [x] Transporte de memória mantido apenas para testes
- [x] Falha de envio invalida o token e resposta pública permanece genérica
- [ ] CI para esta mudança concluído e verificado (registrar run e contagens após execução)
- [ ] Credencial staging real sob controle do operador
- [ ] Domínio remetente verificado, com DNS confirmado
- [ ] Staging TLS e proxy seguros com email real recebido
- [ ] Política para falhas de rede/filas, bounce/webhooks e contas legadas revisada
- [ ] Aprovação de exposição pública

**Continuar apenas na feature branch** `feature/d2-e1-react-auth-ui`; manter branch de checkpoint `checkpoint/d2-e151-identity-2026-10-31` e PR #3 sem merge.
