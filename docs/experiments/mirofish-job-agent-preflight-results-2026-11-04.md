# MiroFish × Job Agent — preflight e resultado matemático preliminar

**Estado:** seed e requisito preparados, **MiroFish NÃO executado** neste checkpoint. Não existe ID de simulation, relatório ReportAgent, output OASIS, GraphRAG, nem observações de agentes simulados a apresentar. O conteúdo a seguir é só um cálculo determinístico das hipóteses fornecidas no seed, e **não** uma saída do MiroFish.

## Compatibilidade técnica verificada
- Repositório público original `666ghj/MiroFish`, licença AGPL-3.0, frontend Node.js 18+, backend Python 3.11–3.12 e gerenciador `uv`.
- README exige `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL_NAME` e `ZEP_API_KEY`. Sem configuração de serviços e chaves não é possível executar a simulação de múltiplos agentes.
- Interface do projeto permite upload de arquivos `MD/TXT/PDF` e uma descrição da simulação, depois construção de grafo, preparação dos agentes, execução e ReportAgent.
- O Job Agent tem bloqueio `503 CV_SANDBOX_REQUIRED`; nunca integrar o produto real, DB, currículos privados ou credenciais. Executar MiroFish em ambiente de laboratório separado.

## Sensibilidade simplificada a cancelamento
Aquisições planejadas (jan–ago): `[4,8,15,28,48,72,112,170]`.
Algoritmo: `ativos = round(ativos_anteriores * (1 - churn)) + novas_assinaturas`. Arredondamento Python por mês. Preço R$ 299, zero inadimplência, aquisição fixa idêntica em todas as variantes.

| Churn mensal assumido | Jan | Fev | Mar | Abr | Mai | Jun | Jul | Ago | MRR Ago |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5% | 4 | 12 | 26 | 53 | 98 | 165 | 269 | 426 | R$ 127.374 |
| 7% | 4 | 12 | 26 | 52 | 96 | 161 | 262 | 414 | R$ 123.786 |
| 10% | 4 | 12 | 26 | 51 | 94 | 157 | 253 | 398 | R$ 119.002 |
| 12% | 4 | 12 | 26 | 51 | 93 | 154 | 248 | 388 | R$ 116.012 |

**Interpretação:** são cenários condicionais com vendas exógenas fixas. A curva de influenciadores e as vendas não foram medidas. Um choque de segurança, preço, reputação ou concorrência pode derrubar as novas assinaturas — efeito ausente desta tabela.

## Próxima execução real do MiroFish (ainda não realizada)
1. Instância separada/efêmera MiroFish, Python 3.12; instalar conforme README oficial.
2. Configurar credenciais de LLM e Zep apenas em segredo/ambiente seguro, nunca GitHub, mensagens ou logs.
3. Carregar `mirofish-job-agent-seed-2026-11-04.md` e colar o texto do arquivo `mirofish-job-agent-requirement-2026-11-04.md` em Simulation Requirement.
4. Construir grafo, preparar agentes, rodar um piloto pequeno (<40 rodadas, conforme aviso de alto consumo do README), gerar relatório e exportar indicadores.
5. Repetir A, B, C, D em condições comparáveis; separar narrativas geradas pelos agentes de números efetivamente medidos.
6. Guardar relatório sanitizado com ID, commit do MiroFish, custos, parâmetros, evidências, falhas e limitações.

**Decisão atual:** protótipo de entrada de simulação PRONTO; simulação MiroFish **NÃO EXECUTADA**; resultado preliminar de sensibilidade matemática disponível; segurança da produção Job Agent **NO-GO**.
