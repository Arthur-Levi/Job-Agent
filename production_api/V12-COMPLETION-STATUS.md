# v12.1 — Incremento de importação e prioridades

Implementado: reconhecimento conservador de cabeçalhos PT/EN; separação heurística por bullets, linhas em branco e cabeçalhos com datas; bloqueio de duplicações idênticas já existentes para o mesmo usuário, preservando dados; endpoint autenticado GET /api/diagnostic/priority-actions com recomendações rastreadas até perfil, vagas e evidências.

Limitações: agrupamentos e títulos requerem revisão; duplicações semanticamente equivalentes com textos distintos não são detectadas; análise textual não comprova competência; nenhuma probabilidade de contratação é calculada. Não houve homologação PostgreSQL, navegador real ou clientes. Testes direcionados: 5 aprovados com SQLite de teste. Não afirmar fechamento completo da jornada.
