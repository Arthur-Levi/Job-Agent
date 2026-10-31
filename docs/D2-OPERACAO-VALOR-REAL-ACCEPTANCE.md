# D2 — OPERAÇÃO VALOR REAL: contrato de aceitação do usuário
Data: 2026-10-31
Branch: test/sec05-stripe-prebeta
Decisão: Stripe Test Mode adiado; não tocar em main, PR #2, worktree original, bancos originais.

## Tese verificável
O Job Agent só entregará valor comercial quando uma pessoa conseguir sair de um currículo real para um perfil fiel, diagnóstico baseado em fatos e ações de carreira claras, sem afirmações inventadas ou necessidade de refazer todo o trabalho manualmente.

## Jornada de aceitação
1. Cadastro/login/sessão. Novo usuário isolado e autenticado.
2. Upload de PDF/DOCX/TXT com texto selecionável; erros legíveis para documento escaneado, inválido ou excedente; sem armazenar bruto no preview.
3. Preview da importação: experiências individuais, empregador/cargo/datas, formação, projetos, competências **mencionadas**; confiança e procedência explícitas; permitir correção/exclusão antes de gravar.
4. Confirmação transacional: Evidence -> MasterProfileItem -> CareerFact, com source_evidence_id/source_reference, USER_DECLARED, sem inventar qualificações ou resultados.
5. Repetição de importação idêntica: sem duplicata; near-duplicate ambígua exige revisão; conflitos preservados e auditáveis.
6. Perfil persistente: logout/login/reload; correção de dado gera histórico superseded sem apagar rastreabilidade; sem vazamento interusuários.
7. Diagnóstico: uma vaga real, requisitos extraídos ou fornecidos, gaps com referência a fato/evidência, sem probabilidade de contratação inventada; recomendações específicas e executáveis.
8. Currículo fundamentado: somente fatos selecionados da conta, coerência com cargo-alvo, texto profissional com seção apropriada, preserva ausências sem preencher falsamente; revisão pelo usuário.
9. Primeiro resultado: usuário entende 3 próximas ações ligadas a suas lacunas; linguagem simples e navegação intuitiva.

## Estado factual do código inspecionado
- `production_api/main.py` routes de cadastro/login, /api/import/resume/file-preview, /preview e /confirm; /api/master-profile; /api/fact-ledger e /contradictions; /api/diagnostic/fact-grounded; /api/resume/grounded-draft; /api/diagnostic/priority-actions e /api/journey/first-result.
- `resume_ingestion.py`: PDF, DOCX, TXT; 2 MB, 12 páginas PDF, 25 mil caracteres, extração de texto; não OCR. Arquivo escaneado pode falhar.
- `resume_journey.py`: segmentação heurística por cabeçalho, quebra em bullets/brancos/datas; pode agrupar experiências e ignorar seções não reconhecidas.
- `resume_similarity.py`: duplicate/possible_duplicate por título e descrição; ainda requer avaliação de falsos positivos/negativos.
- `resume_confirm`: exige confirmação explícita; grava Evidence e projeta apenas as novas em MasterProfileItem e CareerFact, transacionalmente.
- `diagnostic_fact_grounded`: correspondência textual; não prova capacidade nem estima contratação.
- `grounded_resume`: valores literais de fatos, rastreáveis; ainda é rascunho simples, não documento final sofisticado.
- Não inferir que existência de endpoint significa UX funcional ou comercialmente validada.

## Matriz inicial de cenários
A. Candidato junior administrativo/logística com Excel e Power BI, múltiplos empregadores e datas.
B. Candidato junior tecnologia com projetos reais e experiência não profissional.
C. Currículo com 3 experiências quase similares na mesma empresa, mudanças de cargo.
D. Currículo sem headings usuais ou com tabelas DOCX.
E. Currículo PDF textual e PDF digitalizado sem camada de texto (falha explicada).
F. Currículo com duplicata/contradição proposital e correção posterior.
G. Duas contas distintas, mesma vaga, evidências diferentes; isolamento forte.
H. Usuário sem experiência; não inventar experiências e oferecer alternativas concretas.
Todos os cenários devem usar dados sintéticos, sem currículos pessoais reais em commits.

## Critérios mínimos de PASS técnico
- Todos os cenários de importação completam com correção humana explícita ou falha controlada; nunca salvam dados sem confirmação.
- Experiências não são fundidas silenciosamente; diferenças entre empregador/cargo/período são revisáveis.
- Importação repetida não aumenta contagens em cenário idêntico.
- Cada afirmação gerada é atribuível a fato ativo e dono corretos; fatos superseded/excluídos não reaparecem.
- Diagnóstico não mistura vagas/usuários; lacunas são explicáveis e ligação aos requisitos é reproduzível.
- Logout/login conserva estado; outro usuário não enxerga os dados.
- Testes automatizados PASS no ambiente isolado; testes de navegador e UX precisam evidência separada.

## Critérios de valor (hipóteses, não medições)
- Primeira entrega útil em até 10 minutos para currículo comum com texto selecionável.
- >= 90% dos campos essenciais corretos após revisão simples de candidatos piloto; reportar métrica por campo, não porcentagem geral ilusória.
- >= 80% dos pilotos identificam pelo menos 1 recomendação específica que adotariam.
- 0 afirmações inventadas em currículos gerados; qualquer ocorrência é blocker.
- >= 70% concluem cadastro -> importar -> revisar -> diagnóstico -> primeira ação sem ajuda.
- Medir tempo e cliques, edições manuais, falhas de interpretação, confiança e disposição de pagar; metas provisórias, validar com 5-10 pilotos, não se trata de estatística inferencial.

## Plano de execução / checkpoints
D2-A: reexecutar backend/tests e build frontend e capturar evidências.
D2-B: escrever testes end-to-end de API isolados sobre a jornada, duplicação, contradição, perfis múltiplos e persistência.
D2-C: consertar pontos de parse/segmentação de experiência, sem mascarar falhas no teste.
D2-D: implementar revisão de importação por item, contextualizar procedência e melhorar rascunho fundamentado.
D2-E: teste real de interface com 5-10 pilotos consentidos, sem cobrança; validar utilidade e tempo até primeiro valor.
D2-F: somente então revisar posicionamento/preço, beta e retorno ao Stripe.

## Segurança
Sem executar migrations em bancos originais; usar apenas PostgreSQL SEC05 descartável na 55434 após verificação de identidade, ou SQLite efêmero para testes que o suportam; não commitar secrets nem dados pessoais; nenhum merge para main sem autorização.

## Próximo comando inicial (somente leitura)
cd /workspaces/Job-Agent-SEC05
git status --short --branch
find production_api/tests -maxdepth 1 -type f -name 'test_*.py' | sort
find . -maxdepth 3 -name package.json -not -path '*/node_modules/*'
