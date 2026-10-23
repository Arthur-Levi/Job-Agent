# Job Agent — MVP Fullstack Beta

Aplicação **separada** da API D1/D2, para preservar o código original e evitar expor rotas legadas sem autenticação. Não integra automaticamente as migrations ou entidades existentes: a migração para a arquitetura principal ainda precisa ser feita.

## Iniciar

```bash
cd mvp_fullstack
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

Abra http://127.0.0.1:8000 — documentação da API: http://127.0.0.1:8000/api/docs

## Funcionalidades

- Registro/login/logout; senhas PBKDF2 com sal; tokens aleatórios de 7 dias com hash persistido.
- Perfil profissional, evidências declaradas, cadastro manual de vagas.
- Diagnóstico inicial explicável com plano de 7 dias.
- Matching textual transparente (não é probabilidade de contratação).
- Currículo textual fundamentado em informações declaradas.
- Perguntas de entrevista vinculadas a requisitos da vaga.
- CRM manual de candidaturas, tarefas e painel de métricas.
- Isolamento por usuário em consultas e alterações.

## Limites e segurança

**Beta local — não publicar na internet sem hardening.** Não há cobrança, pagamentos, recuperação de senha, verificação de e-mail, rate limiting, 2FA, observabilidade, testes de invasão, backup automatizado, LGPD operacional ou deploy de produção. Os dados são armazenados em SQLite local, sem criptografia em repouso. Sessões são armazenadas no `sessionStorage` e não devem ser usadas para dados sensíveis em produção sem revisão de segurança. Requer HTTPS, CSP e controles anti-abuso antes de qualquer beta pública.

O diagnóstico é determinístico e inicial; não existe integração com LLM, verificação automática de evidências, scraping, envio de currículos, integração de portais ou cálculo de probabilidade de contratação. As evidências estão sempre marcadas como não verificadas.

## Testes

```bash
pytest -q test_app.py
```

Para usar banco temporário nos testes, o arquivo define `JOB_AGENT_MVP_DB` antes de importar a aplicação.
