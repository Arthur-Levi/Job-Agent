# Evidence Strength — avaliação comparativa v1

## O que mede
Rubrica determinística de **qualidade da documentação declarada** (0–100), não qualidade técnica real. Critérios: escopo 15, contribuição pessoal 25, método 20, resultados 25 e limitações 15. Cada campo precisa de pelo menos 35 caracteres para pontuar. Isso é um indicador grosseiro de completude e **pode ser manipulado com texto falso**. Links não são abertos, autoria não é verificada, nenhuma probabilidade de contratação é produzida.

## Comparação reproduzível (casos sintéticos, não clientes reais)
- Caso A: menção breve a Python, sem contexto: 0/100.
- Caso B: projeto com escopo, contribuição e método descritos: 60/100.
- Caso C: mesmo projeto com resultados e limitações descritos: 100/100.
- Caso D: cinco campos preenchidos com texto inventado: também 100/100, mas **NOT_INDEPENDENTLY_VERIFIED**. Esse caso demonstra a limitação do método, não sua eficácia.

Os testes automatizados verificam esses casos, persistência, histórico, segregação entre contas, exportação e remoção por cascata. Eles **não demonstram validade preditiva**.

## Protocolo para comparação com casos reais
1. Recrutar profissionais voluntários, obter consentimento específico e anonimizar dados; não importar currículos pessoais sem permissão.
2. Selecionar pelo menos 20 evidências reais de projetos/experiências, cobrindo diferentes níveis de documentação e áreas.
3. Dois avaliadores independentes (recrutamento e especialista técnico) avaliam, às cegas, clareza, rastreabilidade, contribuição e verificabilidade. Registrar discordâncias.
4. Comparar ordenação do sistema com rubrica humana usando Spearman e concordância por faixa; medir falsos positivos e falsos negativos.
5. Criar casos adversariais com textos longos inventados, links inválidos e afirmações não comprovadas. Não usar dados pessoais no repositório.
6. Revisar rubrica antes de usar scores para priorização; documentar erro, vieses e limitações por ocupação.

**Estado:** apenas testes sintéticos executáveis; nenhuma avaliação com participantes reais foi realizada nesta entrega.
