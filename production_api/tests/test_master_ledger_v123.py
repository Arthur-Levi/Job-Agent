import uuid
from fastapi.testclient import TestClient
from main import app,engine
from models import Base
Base.metadata.create_all(engine)
c=TestClient(app)

def account():
    data={'email':f'ledger-{uuid.uuid4().hex}@example.com','password':'very-strong-password-123'}
    assert c.post('/api/auth/register',json=data).status_code==201
    token=c.post('/api/auth/login',json=data).json()['access_token']
    return {'Authorization':'Bearer '+token}

def test_master_profile_crud_isolation_and_export():
    a,b=account(),account()
    item={'category':'experience','title':'Analista de dados','organization':'Empresa X','start_date':'2025-01','end_date':'','description':'Dashboards'}
    r=c.post('/api/master-profile/items',headers=a,json=item);assert r.status_code==201,r.text
    id=r.json()['id']
    assert c.get('/api/master-profile',headers=b).json()['items']==[]
    assert c.put(f'/api/master-profile/items/{id}',headers=b,json=item).status_code==404
    assert c.delete(f'/api/master-profile/items/{id}',headers=b).status_code==404
    assert c.put(f'/api/master-profile/items/{id}',headers=a,json={**item,'title':'Analista BI'}).json()['title']=='Analista BI'
    assert len(c.get('/api/account/export',headers=a).json()['master_profile_items'])==1
    assert c.delete(f'/api/master-profile/items/{id}',headers=a).status_code==200

def test_fact_ledger_append_only_corrections_and_ownership():
    a,b=account(),account()
    p={'subject':'Projeto Alpha','predicate':'tecnologia','value':'Python','source_type':'user_statement'}
    r=c.post('/api/fact-ledger',headers=a,json=p);assert r.status_code==201,r.text
    id=r.json()['id'];assert r.json()['verification']=='USER_DECLARED'
    assert c.get('/api/fact-ledger',headers=b).json()['facts']==[]
    assert c.post(f'/api/fact-ledger/{id}/correct',headers=b,json={'value':'Go','reason':'Revisão'}).status_code==404
    correction=c.post(f'/api/fact-ledger/{id}/correct',headers=a,json={'value':'FastAPI','reason':'Corrigi o framework'})
    assert correction.status_code==201,correction.text
    assert correction.json()['supersedes_id']==id
    assert len(c.get('/api/fact-ledger',headers=a).json()['facts'])==1
    history=c.get('/api/fact-ledger?include_history=true',headers=a).json()['facts']
    assert len(history)==2 and {x['status'] for x in history}=={'ACTIVE','SUPERSEDED'}
    assert c.post(f'/api/fact-ledger/{id}/correct',headers=a,json={'value':'Rust','reason':'Mudança'}).status_code==409
    assert len(c.get('/api/account/export',headers=a).json()['fact_ledger'])==2
    assert c.post('/api/fact-ledger',headers=a,json={**p,'source_type':'external_review'}).status_code==422

def test_references_are_owned_and_endpoints_require_auth():
    a,b=account(),account()
    ev=c.post('/api/evidence',headers=b,json={'kind':'project','title':'Privado','description':'Projeto interno confidencial'}).json()['id']
    p={'category':'project','title':'Projeto privado','source_evidence_id':ev}
    assert c.post('/api/master-profile/items',headers=a,json=p).status_code==404
    assert c.post('/api/fact-ledger',headers=a,json={'subject':'Projeto','predicate':'usa','value':'Python','source_type':'evidence','source_reference':str(ev)}).status_code==404
    assert c.get('/api/master-profile').status_code==401
    assert c.get('/api/fact-ledger').status_code==401
