import uuid
from fastapi.testclient import TestClient
from main import app,engine
from models import Base
Base.metadata.create_all(engine)
c=TestClient(app)

def user():
    data={'email':f'v124-{uuid.uuid4().hex}@example.com','password':'strong-pass-123456789'}
    assert c.post('/api/auth/register',json=data).status_code==201
    token=c.post('/api/auth/login',json=data).json()['access_token']
    return {'Authorization':'Bearer '+token}

def test_confirm_projects_facts_and_idempotence():
    h=user();p={'evidence':[{'kind':'project','title':'Sistema de relatórios','description':'Criei relatórios para controle de estoque','url':''}], 'target_role':'Analista'}
    r=c.post('/api/import/resume/confirm',headers=h,json=p);assert r.status_code==201,r.text
    j=r.json();assert j['count']==1 and len(j['master_item_ids'])==1 and len(j['fact_ids'])==1
    again=c.post('/api/import/resume/confirm',headers=h,json=p);assert again.status_code==201,again.text
    assert again.json()['count']==0 and not again.json()['fact_ids']
    assert len(c.get('/api/master-profile',headers=h).json()['items'])==1
    draft=c.post('/api/resume/grounded-draft',headers=h,json={});assert draft.status_code==200,draft.text
    assert draft.json()['claims'][0]['fact_id']==j['fact_ids'][0]
    assert 'Criei relatórios' in draft.json()['text']

def test_contradictions_and_cross_user_isolation():
    a,b=user(),user()
    p={'subject':'Empresa A','predicate':'cargo','value':'Analista','source_type':'user_statement'}
    first=c.post('/api/fact-ledger',headers=a,json=p);assert first.status_code==201
    c.post('/api/fact-ledger',headers=a,json={**p,'value':'Gerente'})
    assert len(c.get('/api/fact-ledger/contradictions',headers=a).json()['conflicts'])==1
    assert c.get('/api/fact-ledger/contradictions',headers=b).json()['conflicts']==[]
    assert c.post('/api/resume/grounded-draft',headers=b,json={'fact_ids':[first.json()['id']]}).status_code==404
    assert c.post('/api/resume/grounded-draft',headers=a,json={'fact_ids':[first.json()['id']]}).status_code==200
    assert c.post('/api/fact-ledger/'+str(first.json()['id'])+'/correct',headers=a,json={'value':'Especialista','reason':'Corrigir cargo'}).status_code==201
    assert c.post('/api/resume/grounded-draft',headers=a,json={'fact_ids':[first.json()['id']]}).status_code==404

def test_require_auth_and_no_fabrication():
    assert c.get('/api/fact-ledger/contradictions').status_code==401
    assert c.get('/api/diagnostic/fact-grounded').status_code==401
    assert c.post('/api/resume/grounded-draft',json={}).status_code==401
    h=user()
    r=c.get('/api/diagnostic/fact-grounded',headers=h);assert r.status_code==200
    assert r.json()['hiring_probability'] is None
    assert c.post('/api/resume/grounded-draft',headers=h,json={}).status_code==422
