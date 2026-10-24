# Job Agent — Backup e recuperação PostgreSQL 16

## Objetivo
Backups consistentes com pg_dump em formato custom, SHA-256 e teste de restauração em container temporário isolado, sem modificar o banco principal.

## Execução
```bash
cd /workspaces/Job-Agent
bash scripts/backup-postgres.sh
```
O backup somente é publicado como .dump após passar pelo teste de restauração. O teste exige Docker e espaço para um PostgreSQL temporário (tmpfs de 512 MB; aumente se necessário). Os arquivos são armazenados em db-recovery/automatic por padrão. Não coloque dumps no Git.

## Automação enquanto o Codespaces estiver ligado
Verifique que cron está instalado e ativo. Se estiver, instale a entrada no crontab do usuário, **sem substituir as entradas existentes**:
```bash
(crontab -l 2>/dev/null; echo '0 3 * * * cd /workspaces/Job-Agent && /usr/bin/bash scripts/backup-postgres.sh >> /workspaces/Job-Agent/db-recovery/backup.log 2>&1') | crontab -
```
Não execute esse comando duas vezes: ele duplicaria a entrada. Cron não executa com Codespaces suspenso ou excluído. Faça um backup manual ao iniciar sessões importantes.

## Cópia externa
Configure rclone com destino seguro e credenciais fora do repositório. Defina JOBAGENT_BACKUP_REMOTE, por exemplo `remote:jobagent-backups`, no ambiente de execução do backup. Teste leitura e restauração de um arquivo baixado da nuvem. O envio por rclone não criptografa automaticamente o dump; prefira destino criptografado (rclone crypt) e controle de acesso. Nunca versionar dumps, senhas ou tokens.

## Verificação independente
```bash
sha256sum -c /caminho/jobagent-AAAAMMDDTHHMMSSZ.dump.sha256
bash scripts/verify-postgres-backup.sh /caminho/jobagent-AAAAMMDDTHHMMSSZ.dump
```

## Limitações
O teste valida a estrutura restaurável e tabelas, mas não garante integralmente consistência semântica de cada registro ou disponibilidade futura do provedor remoto. pg_dump cobre apenas o banco jobagent_test, não usuários globais, roles, configurações de infraestrutura, segredos nem arquivos externos. Sem armazenamento remoto testado, a recuperação após exclusão do Codespaces não está garantida. Não remover o backup original postgres-volume-original.tar.

## Recuperação de desastre
Preserve os arquivos existentes; prepare um PostgreSQL 16 novo e vazio em volume separado; valide checksum do dump; restaure com pg_restore no novo banco; valide tabelas, usuários e login com credenciais adequadas; só depois redirecione a API. Nunca restaurar por cima do volume original sem backup independente e plano de reversão.
