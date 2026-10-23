# Job Agent v12.3 — Master Profile + Fact Ledger

## Entregue
- `master_profile_items`: experiências, projetos, formação, certificados, idiomas e habilidades em campos estruturados, com referência opcional a uma evidência existente da mesma conta.
- `career_facts`: declarações profissionais com assunto, predicado, valor, tipo de fonte, referência, estado e trilha de correção. Corrigir cria um novo registro e marca o anterior como substituído; não sobrescreve o histórico.
- Endpoints autenticados de leitura, criação, edição e remoção de itens estruturados; criação, consulta e correção de fatos.
- UI simples em **Perfil mestre** e **Fatos**; exportação de conta e exclusão incluem as novas tabelas.
- Verificação de isolamento entre contas e referência a evidências próprias.
- Alembic: revisão `0005_master_profile_fact_ledger`; corrigido bug antigo de configuração do Alembic e da migration inicial que criava tabelas de versões futuras.

## Limitações e segurança
- `USER_DECLARED` é sempre uma declaração do usuário; a presença de `source_reference` não autentica a fonte. O endpoint público recusa `external_review` como origem autoatribuída.
- O ledger preserva o histórico de correções, mas **não é imutável criptograficamente** e administradores do banco podem alterá-lo. A exclusão de conta remove os registros, conforme a política do produto.
- O Master Profile ainda não é preenchido automaticamente por todas as importações; a sincronização com a extração e o diagnóstico será um próximo incremento. Não alegar fluxo completo fechado.
- Edição de item estruturado não cria revisão histórica do item; histórico append-only aplica-se apenas ao Fact Ledger.
- UI utiliza campos de texto para categorias e origem, com validação de servidor; melhorar selects e acessibilidade.
- Não foi realizado teste em PostgreSQL real nem E2E no Chromium.

## Validação realizada
- `pytest tests -q --ignore=tests/browser_smoke_v9.py`: **59 testes aprovados**, um aviso de depreciação.
- `node --check web/app.js`: passou.
- `alembic upgrade head` e `alembic current`: passaram com SQLite descartável e chegaram à revisão `0005_master_profile_fact_ledger`.
- A suíte não comprova implantação comercial nem preço de R$ 299/mês.

## Próxima entrega
Sincronização com importação após revisão humana, extração de fatos a partir de evidências confirmadas, tratamento de contradições e geração de currículo estritamente baseada em fatos ativos.
