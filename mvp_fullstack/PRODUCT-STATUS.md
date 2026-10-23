# Job Agent — Product build 1.1

## Implementado e testado localmente
- Cadastro, login e logout com senhas PBKDF2 e tokens armazenados como hash.
- Perfil, evidências declaradas, vagas manuais, comparação de requisitos, rascunho de currículo e roteiro de entrevistas.
- Diagnóstico inicial baseado em regras, plano de 7 dias e checklist de completude sem fingir probabilidade de contratação.
- CRM manual de candidaturas, tarefas e dashboard.
- Histórico de atividades, exportação de dados, exclusão de conta e alteração de senha com revogação de sessões.
- Cabeçalhos HTTP de segurança e limitador local de tentativas de autenticação.
- Testes automatizados básicos.

## NÃO está pronto para venda/publicação pública
- A interface é uma aplicação HTML/JS integrada à API FastAPI/SQLite, não uma integração com a arquitetura D2.1 PostgreSQL.
- Não há checkout, assinatura, impostos, notas fiscais, webhooks ou cobrança real.
- Não há IA externa, verificação de evidências, integrações de vagas ou envio de candidaturas.
- Não há recuperação de senha por e-mail, confirmação de e-mail, MFA, controle de sessão em múltiplos dispositivos ou proteção distribuída contra abuso.
- Não há observabilidade, backups gerenciados, migrações versionadas, deploy de produção ou auditoria de segurança independente.
- Não há evidência de eficácia profissional nem validação com clientes.
- O checklist mede completude das informações, NÃO qualidade da carreira.

## Execução
```bash
cd mvp_fullstack
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```
Abra http://127.0.0.1:8000. Testes: `pytest -q`.

## Próxima etapa antes de cobrar clientes
1. Consolidar a versão mais recente do repositório D2.1/TD-34, sem substituir o trabalho já feito.
2. Migrar este protótipo para PostgreSQL com migrations e auth/isolamento multiusuário robustos.
3. Integrar cobrança real com webhooks verificados, estados de assinatura, cancelamento e entitlements.
4. Fazer o diagnóstico usar evidências analisadas e fontes reais com avaliação humana, testes de qualidade e limites claros.
5. Configurar HTTPS, domínio, backups, monitoramento, privacidade, suporte e testes end-to-end.
