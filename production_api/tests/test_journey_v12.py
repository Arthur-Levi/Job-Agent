from resume_journey import suggestions

def test_extract_structured_sections_without_fabrication():
    result=suggestions('Objetivo:\nAnalista de dados\nExperiência:\nAtualizei painéis de Power BI na empresa.\nProjetos:\nConstruí planilhas para logística.')
    assert result['target_role_draft']=='Analista de dados'
    assert [x['kind'] for x in result['evidence_drafts']]==['experience','project']
    assert all(x['status']=='DRAFT_UNVERIFIED' for x in result['evidence_drafts'])

def test_no_sections_no_invention():
    assert suggestions('Eu sei SQL e trabalhei com relatórios.')['evidence_drafts']==[]

def test_long_lines_bounded():
    x=suggestions('Projetos:\n'+'a'*10000)['evidence_drafts'][0]
    assert len(x['description'])<=3500
