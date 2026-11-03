# SEC-OPS-01.E2.2-A — Contrato de comunicação API → worker

**Status: DRAFT / DESIGN / NOT IMPLEMENTED / NO-GO.**
Baseline: `77ae315`. Tracking: #23, PR #24.

## 1. Fronteiras e decisão de transporte

O `resume_broker.py` existente implementa transporte **Unix socket local sem autenticação de workload própria**; o `resume_worker.py` usa mensagens JSON em framing de 4 bytes. Ambos continuam protótipos locais. Um socket Unix **não atravessa hosts**. Não converter esse protocolo local em TCP público nem presumir que o framing autentique um pedido.

Na topologia proposta, a API chama um endpoint de admissão em rede privada do **worker host/VM dedicado**, com TLS mútuo ou equivalente verificável para autenticação de serviço, autorização de operação e rejeição de conexões não autorizadas. Credenciais específicas do worker, renovação e revogação são requisitos de operação. Não passar qualquer autoridade Docker pela interface. A identidade humana/tenant **não** é derivada de campos livres enviados pelo cliente: deve vir da sessão autenticada da API e ser vinculada à requisição assinada/autorizada.

## 2. Operações permitidas

| Operação | Método lógico | Finalidade |
|---|---|---|
| `submit` | criação | Admitir parser job sintético/legítimo já autorizado e limitado |
| `status` | consulta | Consultar estado do job pertencente à conta |
| `cancel` | cancelamento | Solicitar interrupção do job da conta |

Nunca aceitar `command`, `image`, `mounts`, `docker_args`, `env`, `network` ou nomes arbitrários de módulos. IDs opacos e não sequenciais. `status` e `cancel` exigem autenticação e autorização renovadas.

## 3. Envelope lógico proposto

```json
{
  "version": 1,
  "operation": "submit",
  "request_id": "uuid",
  "idempotency_key": "opaque-bounded-key",
  "subject": {"user_id": "server-authenticated-uuid", "tenant_id": "authorized-tenant"},
  "payload": {"filename": "synthetic.txt", "content_b64": "base64-bytes"}
}
```

Este é o **envelope funcional**, não o formato final de fio, nem uma indicação para o cliente poder declarar subject. A admissão deve impor tipo estrito, campos permitidos, limite do corpo antes de `json.loads`, decodificação de base64 com limite, comprimento do nome, formatos aceitos e limites do parser. Nunca registrar `payload.content_b64`, nomes, descrições ou dados pessoais em logs.

## 4. Segurança obrigatória

- Workload identity autenticada no worker; autorização por escopo `submit/status/cancel`.
- Autorização do candidato/tenant validada na API e novamente vinculada à identidade do job no admission service; client-supplied subject não é confiável.
- TLS validado, certificados/credenciais de curto ciclo com revogação; nenhuma credencial estática no repositório.
- Replay: nonce/request timestamp com janela curta e deduplicação atômica compartilhada; idempotência por tenant/usuário.
- Admission control: limite global **entre réplicas**, limite por usuário, tamanho e TTL de fila, recusa 429/503 sem iniciar workload.
- Estados: `queued`, `running`, `succeeded`, `failed`, `cancelled`, `expired`; transições auditáveis, cancelamento idempotente.
- Limites independentes: request/response, tempo de fila, tempo total, CPU/RAM/PIDs/tmpfs, retenção de CV, logs seguros.
- Fail closed em falhas de autenticação, backend de quota, runtime ou canal; sem fallback para subprocess desprotegido em produção.

## 5. Matriz mínima de testes

1. Mensagem com versão/operação desconhecida, campos extras, objeto malformado, comprimento excessivo → rejeição **antes** do parser.
2. Serviço sem credencial, credencial inválida/expirada/revogada → rejeição; sem logar segredos.
3. `user_id` ou `tenant_id` forjado, consulta/cancelamento cross-user → negado.
4. Replay idêntico e idempotência concorrente entre réplicas → no máximo uma execução física por chave.
5. Sobrecarga por usuário e global → recusa bounded, sem vazamento de recursos.
6. Worker indisponível, timeout, crash ou cancelamento → resultado controlado e remoção de dados efêmeros.
7. API não alcança Docker API; worker não alcança o PostgreSQL da aplicação; parser sem egress.
8. Nenhum teste com currículo real nem banco existente do Codespaces.

## 6. Critérios para iniciar implementação

- Revisar protocolo e modelos de ameaça, inclusive armazenamento da fila e identidade entre hosts.
- Implementar primeiro parser/validator **puro e sem efeitos colaterais**, com testes de rejeição.
- Só depois construir adapter, serviço de admissão e harness descartável.
- Manter `503 CV_SANDBOX_REQUIRED` na rota de produção até SEC/OPS e outros P0 serem aprovados.

**Este documento não implementa autenticação, conexão remota ou sandbox.**
