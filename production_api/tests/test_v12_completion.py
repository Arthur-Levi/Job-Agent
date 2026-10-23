from resume_journey import suggestions, normalize

def test_multiple_entries_and_formats():
    sample='''WORK EXPERIENCE
- Analista | Empresa A | 2023
  Atualizei dashboards e indicadores.
- Assistente | Empresa B | 2024
  Organizei planilhas de controle.

PROJECTS
- Projeto Alpha
  Desenvolvi um sistema de relatórios.
- Projeto Beta
  Implementei uma API com testes.

EDUCATION
Graduação em Sistemas
Universidade Exemplo 2025
'''
    result=suggestions(sample)
    assert len([e for e in result['evidence_drafts'] if e['kind']=='experience'])==2
    assert len([e for e in result['evidence_drafts'] if e['kind']=='project'])==2
    assert any(e['kind']=='education' for e in result['evidence_drafts'])

def test_accented_sections_and_normalization():
    result=suggestions('EXPERIÊNCIA PROFISSIONAL\n• Empresa Um — 2023\nAtuei em operações.\n• Empresa Dois — 2024\nAtualizei relatórios.\nFORMAÇÃO ACADÊMICA\nCurso técnico em logística')
    assert len([e for e in result['evidence_drafts'] if e['kind']=='experience'])==2
    assert normalize('  EXPERIÊNCIA   Profissional ') == normalize('experiencia profissional')
