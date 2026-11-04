# Job Agent — backlog de produto, beta e continuidade profissional
**Registrado em:** 2026-11-04 · **Estado:** propostas e lacunas a validar, NÃO presumir implementação concluída.

## Critério de priorização
**P0 = bloqueador da experiência beta com currículos reais; P1 = essencial à proposta paga inicial, pode ser liberado em lote gradual; P2 = continuidade e expansão pós-contratação.** A segurança de processamento (SEC/OPS Gate 1, Issue #23) continua bloqueante para qualquer coleta/importação de CV real; `503 CV_SANDBOX_REQUIRED` permanece até aceite independente. Nenhum item deste backlog altera o gate.

### P0 — Jornada completa e segura (importação → revisão → fatos confirmados → entrega)
- [ ] Upload consentido, limites de tamanho/extensão e validações; execução unicamente em sandbox aprovada (SEC/OPS); isolamento entre usuários/tenants; retenção/exclusão e logs sem PII.
- [ ] Extração determinística auditável de seções: cada experiência distinta com empresa, cargo, período e atribuições; educação, competências, cursos e links.
- [ ] Interface React para revisar, corrigir, remover e confirmar fatos antes de salvar no Master Profile/Fact Ledger. Não inferir fatos ausentes.
- [ ] Deduplicar, identificar contradições e conservar proveniência (trecho/origem/confiança), edição e histórico de confirmação; transações idempotentes.
- [ ] Entregar resultado utilizável e legível ao candidato: perfil confirmado e pelo menos um documento/diagnóstico inicial gerado **somente** com fatos confirmados.
**Aceite:** jornada E2E com PDF/DOCX/TXT sintéticos e casos adversariais em ambiente descartável; usuário consegue corrigir duas experiências misturadas, confirmar/recusar fatos e obter resultado fundamentado; segurança, privacidade e exportação testadas.

### P1-A — Diagnóstico realmente personalizado
- [ ] Capturar objetivo profissional, senioridade, localização/modalidade desejada e restrições voluntárias sem pressupor disponibilidade ou elegibilidade.
- [ ] Separar competências comprovadas, não comprovadas e lacunas relevantes ao cargo-alvo; referenciar fonte do Fact Ledger.
- [ ] Possibilidades realistas de cargos/transição; não prometer emprego, salários ou probabilidade individual de contratação sem evidência.
- [ ] Recomendações específicas, priorizadas por impacto/esforço, com próximas ações e explicações auditáveis; permitir revisão/correção pelo usuário.
**Aceite:** perfis sintéticos distintos produzem recomendações distintas; lacunas não viram fatos; cada recomendação aponta objetivo/requisito e evidência ou ausência; testes contra alucinação.

### P1-B — Currículo e matching fundamentados
- [ ] Gerar currículo em formato amigável a ATS sem inventar qualificações, datas, cargos, conquistas ou métricas; edição e aprovação humana antes de exportar.
- [ ] Exportação funcional (inicialmente PDF e/ou DOCX validado) com testes de integridade e acessibilidade básica.
- [ ] Matching explicável: requisitos de vaga vinculados a experiências/competências comprovadas; indicar correspondências, ausências e incertezas; evitar score opaco como promessa de contratação.
- [ ] Registros de versões de currículo e decisões do usuário; remover dados sensíveis desnecessários; validação de titularidade.
**Aceite:** testes com vagas sintéticas evidenciam por que há ou não correspondência; currículo exportado é fiel ao Fact Ledger e preserva separação de experiências; não atribuir fatos de outro usuário.

### P1-C / P2 — Continuidade sem reconstruir histórico
- [ ] P1: painel de candidaturas com vaga, empresa, etapa, datas e próxima ação; importação/edição voluntária, histórico de mudanças e lembretes opcionais com consentimento.
- [ ] P1: preparação de entrevistas vinculada à vaga e às evidências profissionais, sem roteiros falsos.
- [ ] P1: Master Profile reutilizado em candidatura, diagnóstico, currículo e entrevista; revalidação de fatos alterados.
- [ ] P2: First 90 Days / Job Onboarding: acompanhamento voluntário 30/60/90 dias após contratação.
- [ ] P2: Career Growth: evolução de competências, resultados documentados e preparação de avaliações.
- [ ] P2: Career Mobility: promoção, troca de empresa/área e comparação estruturada de propostas.
**Aceite:** atualizar um fato uma vez reflete-se nas telas pertinentes com trilha de revisão; candidatura e entrevista preservam contexto, respeitam exclusão/consentimento; módulos pós-contratação somente após validação da base.

## Sequência de entrega recomendada
1. **Segurança primeiro:** SEC/OPS Gate 1 aprovado antes de qualquer CV real.
2. **Beta fechado (10 clientes que renovam):** P0 end-to-end + fatia mínima de diagnóstico P1-A + currículo fundamentado exportável P1-B; onboarding e suporte, sem funções automáticas não auditadas.
3. **Beta ampliado:** matching explicável por vaga + candidaturas/entrevistas com histórico P1-C.
4. **Retenção e crescimento:** First 90 Days → Career Growth → Career Mobility conforme demanda comprovada e privacidade.

## Métricas de produto e comerciais
- Conclusão da importação/revisão/confirmação; tempo até primeiro resultado útil; taxa de correção de extração; falhas por formato.
- % de diagnósticos com recomendações ligadas a evidências; satisfação, exportações bem-sucedidas, utilização do matching.
- Ativação D1/D7; candidaturas e entrevistas acompanhadas de forma opt-in; renovações, cancelamentos e feedback.
- CAC, clientes pagantes e **renovação de ao menos 10 assinantes** antes de escalar a malha de microinfluenciadores.
- Não armazenar material sensível em telemetria; consentimento, segregação tenant e expurgo conforme política.

## Limites e riscos
Não tratar itens de roadmap como funções já prontas. Não prometer entrega automática de candidaturas, aprovação ATS ou contratação. Dados profissionais são pessoais: cumprir LGPD, minimização e controles de acesso. Toda feature que recebe CV real depende do gate de segurança atual e de critérios de aceite próprios.
