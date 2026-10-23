import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from career_intelligence import analyze, lexical_support

def test_exact_alias_no_substring_false_positive():
    e={'title':'JavaScript','description':'Escrevi scripts em JS'}
    assert lexical_support('JavaScript',e)
    assert lexical_support('Java',e) is None
    assert lexical_support('Python',e) is None

def test_accent_and_multiple_tokens():
    e={'title':'Testes automatizados','description':'Escrevi testes automatizados de integração'}
    assert lexical_support('testes automatizados',e)
    assert lexical_support('testes de integração',e)
    assert lexical_support('testes de segurança',e) is None

def test_priority_and_no_hiring_probability():
    p={'target_role':'Backend'}
    ev=[{'id':2,'kind':'project','title':'Python API','description':'API Python com FastAPI','url':'','status':'DECLARED'}]
    jobs=[{'id':1,'title':'Backend','company':'A','requirements':['Python','Docker'],'source_url':''},
          {'id':2,'title':'Backend','company':'B','requirements':['Docker','SQL'],'source_url':''}]
    r=analyze(p,ev,jobs)
    assert r['requirement_priorities'][0]['requirement']=='Docker'
    assert r['requirement_priorities'][0]['jobs_requiring']==2
    assert r['requirement_priorities'][0]['state']=='NOT_DOCUMENTED'
    assert r['hiring_probability'] is None
    assert r['quality']['coverage']['requirements_with_candidates']==1
    assert len(r['top_actions'])<=3

def test_empty_data_actionable():
    r=analyze({},[],[])
    assert len(r['top_actions'])==3
    assert r['quality']['coverage']['total_requirements']==0

def test_never_cross_tenant_in_engine():
    a=analyze({'target_role':'Python'},[{'id':1,'kind':'skill','title':'Python','description':'Python profissional','status':'DECLARED'}],
              [{'id':1,'title':'Python','company':'A','requirements':['Python']}])
    b=analyze({'target_role':'Python'},[],[{'id':2,'title':'Python','company':'B','requirements':['Python']}])
    assert a['opportunities'][0]['requirements'][0]['candidate_evidence']
    assert b['opportunities'][0]['requirements'][0]['candidate_evidence']==[]
