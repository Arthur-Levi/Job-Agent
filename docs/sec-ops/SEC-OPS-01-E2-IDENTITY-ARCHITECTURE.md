# SEC-OPS-01.E2.1 — Arquitetura de identidade e isolamento do broker

**Status:** PROPOSTO / NÃO IMPLEMENTADO / NO-GO  
**Base:** checkpoint D2-E2 `69c78fc`, contrato `SEC-OPS-01-BROKER-CONTRACT.md`  
**Rastreabilidade:** Issue #23; PR #24 (Draft)

## 1. Escopo

Este documento define a futura fronteira de autoridade entre API, broker e parser. Não habilita o uso de currículos reais. O código existente em `backend/app/workers/resume_broker.py` é um protótipo de staging; a API não deve receber acesso direto ao Docker daemon.

## 2. Identidades e autoridade esperadas

| Ator | Identidade | Autoridade permitida | Autoridade proibida |
|---|---|---|---|
| API | `jobagent-api` (UID de serviço próprio) | Conectar ao endpoint privado do broker; consultar seu banco via credencial própria | Docker socket/daemon, runtime host, comandos arbitrários |
| Broker | `jobagent-broker` (UID de serviço distinto) | Admitir jobs de parsing autorizados; acionar um runtime restrito e dedicado | Credenciais do banco/API, diretórios de dados de outros serviços, exposição TCP pública |
| Parser | UID sem privilégios no runtime efêmero | Ler entrada limitada e devolver saída estruturada limitada | Rede, filesystem host, segredos, privilégios, mounts arbitrários |
| Host/operador | Conta operacional separada | Instalação, configuração, atualização, observabilidade e recuperação | Compartilhar credenciais operacionais com a API |

**Atenção:** separar processo ou UID não basta se o broker mantiver controle sobre um Docker daemon privilegiado no mesmo host que abriga banco e API. A solução candidata deve usar um **worker host/VM dedicado** e runtime confinado (preferivelmente rootless) para reduzir o impacto de uma eventual falha. Validar o isolamento efetivo antes de aprovar. A implantação via Docker Compose na mesma VM com montagem de `/var/run/docker.sock` não satisfaz este contrato.

## 3. Canal de comunicação

O protótipo usa socket Unix local e enquadramento de mensagens com comprimento em 4 bytes. Para identidades diferentes, o atual diretório `0700` e socket `0600` não permitem compartilhamento por grupo; **não relaxar permissões automaticamente**.

Antes de implementar, escolher e documentar um dos contratos:

- **Mesmo host de aplicação, com broker sem Docker:** socket privado usando serviço intermediário de jobs e credenciais de serviço; ou
- **Worker host/VM dedicado:** API envia jobs autenticados por canal privado com TLS mútuo ou mecanismo equivalente, sem expor o controle do runtime. A interface deve continuar limitada a operações de parsing, nunca a comandos ou imagens arbitrárias.

Não usar um socket Unix local como se funcionasse diretamente entre máquinas. Se for necessário socket Unix local dentro do worker host, ele será interno ao worker e não será montado na API.

## 4. Contrato mínimo de jobs

- Associar job a identidade autenticada e usuário/tenant autorizado, verificando autorização na camada de admissão.
- ID não previsível, limites de corpo e tamanho de entrada; formatos permitidos; deduplicação/idempotência.
- Fila e capacidade globais por worker pool, mais limites por usuário e por origem.
- Prazo de início, execução e expiração; cancelamento e varredura de jobs órfãos.
- Sem persistência desnecessária de CV bruto; TTL e política de eliminação.
- Resposta com status de parsing, códigos de erro permitidos e saída estruturada limitada.
- Logs de eventos e métricas sem conteúdo do documento ou credenciais.

A passagem de `user_id` declarado pelo cliente **não constitui autenticação**: identidade, autorização e tenancy devem ser verificadas antes do encaminhamento.

## 5. Testes de aceitação (somente infraestrutura descartável)

1. API sem acesso ao daemon e sem capacidade de criar contêineres.
2. Broker sem credenciais da API/DB e incapaz de ler recursos de serviços alheios.
3. Parser não root, read-only, sem rede, sem secrets, com limites CPU/RAM/PIDs/tmpfs.
4. Recusa de jobs sem autorização, excessivos, duplicados ou sobre a quota; quotas entre réplicas.
5. Timeout, cancelamento, crash/restart e limpeza de recursos e arquivos temporários.
6. Fail-closed quando o canal do worker estiver indisponível; código `CV_SANDBOX_REQUIRED` ainda bloqueando produção.
7. Evidência reproduzível: commit, imagens fixadas, configurações sanitizadas, resultados do runner/VM descartável, revisão humana e decisão formal.

**Restrições:** não usar os bancos existentes do Codespaces; não executar amostras maliciosas no host compartilhado; não criar serviço com acesso ao Docker socket da API; não alterar `main` nem retirar o bloqueio de produção.

## 6. Decisão de implementação proposta

Escolher como alvo o modelo **worker host/VM dedicado com runtime restrito**, em vez de tentar tornar o daemon root do Codespaces uma fronteira de segurança. A próxima entrega E2.2 será um desenho de deployment e protocolo autenticado coerente com essa separação, submetido a revisão antes de qualquer teste operacional.

**Parecer atual:** documentação de arquitetura proposta, sem aprovação de produção.
