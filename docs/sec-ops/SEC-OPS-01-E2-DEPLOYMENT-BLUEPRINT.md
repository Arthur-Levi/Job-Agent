# SEC-OPS-01.E2.2 — Blueprint de implantação isolada do worker

**Status: DESIGN ONLY / NOT DEPLOYED / NO-GO.**  
**Baseline:** `69c78fc`; contrato `f1d59c8`; arquitetura `4ddcb44`.  
**Tracking:** Issue #23; PR #24 (Draft).

## Decisão

**Não** adicionar `resume_broker` ao `production_api/docker-compose.production.yml`. Esse Compose inicia outra aplicação (`main:app`) e não integra o backend homologado (`app.main:create_app --factory`). **Não** montar `/var/run/docker.sock` na API nem usar o daemon root do Codespaces para ensaio adversarial.

Desenho-alvo de homologação:
1. **Plano de aplicação:** FastAPI D2-E2 em identidade sem acesso ao runtime, usando PostgreSQL *somente em teste descartável*.
2. **Plano de execução separado:** worker host/VM efêmera com runtime confinado e parser-only, sem credenciais do banco nem acesso às redes privadas da aplicação.
3. **Canal:** transporte autenticado entre os dois planos, na rede privada, com autenticação de workload e autorização explícita por job. Uma conexão UNIX domain socket existente **não atravessa hosts**; código atual `RESUME_PARSER_MODE=broker` é somente protótipo local. A integração remota ainda exige implementação e testes.
4. **Parser efêmero:** imagem somente com parser, usuário não root, rede negada, filesystem read-only, limites CPU/RAM/PIDs/tmpfs, sem mounts host e sem segredos.
5. **Gate de produção:** a rota `/preview` continua retornando `503 CV_SANDBOX_REQUIRED`, independentemente da escolha do modo do parser.

## Matrizes de rede e privilégio

| Origem | Destino | Regra pretendida |
|---|---|---|
| Internet | API via gateway | HTTPS somente quando homologado |
| API | Banco próprio | Conexão autenticada estritamente necessária |
| API | Worker admission endpoint | Canal privado autenticado; operações `submit/status/cancel` autorizadas |
| API | Docker API / host socket | **DENY** |
| Worker | Banco, API admin, serviços internos | **DENY** |
| Parser | Internet, banco, Docker daemon | **DENY** |
| Operador | Worker runtime | Acesso administrativo separado, auditado |

## Limites de segurança que exigem implementação

- **Protocolo:** autenticação de serviço, validação de origem e escopo, proteção contra replay e reuso de credenciais, IDs não previsíveis, correlação por request, versionamento e comprimento limitado.
- **Fila/admissão:** limites por usuário e globais entre réplicas, backpressure, TTL e rate limiting; fila de tamanho controlado e recusa segura.
- **Cancelamento:** política em timeout, desconexão, encerramento de API/worker, reinício do broker e limpeza de jobs/contêineres órfãos.
- **Runtime:** isolamento do daemon em worker/VM descartável, imagem fixada por digest, seccomp/AppArmor verificados no host, usuário sem root e sem capacidades excessivas.
- **Privacidade:** sem dados de CV em logs, métricas ou traces; retenção mínima, criptografia aplicável e exclusão previsível.
- **Operação:** supervisionamento, monitoramento/alertas, resposta a incidentes, recuperação e comprovação de segregação.

## Sequência de implementação (propostas, NÃO executadas)

1. E2.2-A: definir contrato autenticado `submit/status/cancel` e threat model; especificar limites e erros sem expor conteúdo de CV.
2. E2.2-B: implementar API adapter e worker admission **em branch**, mantendo a rota de produção bloqueada.
3. E2.2-C: compor laboratório **totalmente descartável** em runner/VM independente e com identidades verificáveis; jamais usar os PostgreSQL existentes do Codespaces.
4. E2.2-D: testes sintéticos: negação de Docker/DB, host FS/egress, overload multirréplica, timeouts, crash, restart, cleanup, vazamento de logs.
5. E2.2-E: revisar CI e política de aprovação; documentação de resultados com SHA/ambiente/config sanitizada. Somente após aprovação de SEC/OPS + demais P0 considerar remover o gate num PR separado.

## Provas indispensáveis para PASS

- Matriz observada UID/GID e acesso a socket/daemon (não apenas declarada).
- Nenhum caminho da API concede acesso ao Docker daemon; tentativa negativa demonstrada.
- Separação real de host/VM, sem credenciais de DB no worker.
- Quotas distribuídas e por usuário testadas com múltiplos processos.
- Limites de recursos e políticas do runtime comprovadas sob falha.
- Cancelamento e recuperação não deixam containers ou dados órfãos.
- End-to-end sintético, logs redigidos e revisão de segurança independente.

**Nenhum item acima está aprovado apenas por este documento. Não é um manifesto executável.**
