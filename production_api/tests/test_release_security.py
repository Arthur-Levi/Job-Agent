"""Authorization regression checks for the v12.4 release candidate."""
import uuid
from fastapi.testclient import TestClient
from main import app, engine
from models import Base
Base.metadata.create_all(engine)
c=TestClient(app)
def account():
    data={'email':uuid.uuid4().hex+'@example.test','password':'a-very-strong-password-123'}
    assert c.post('/api/auth/register',json=data).status_code==201
    r=c.post('/api/auth/login',json=data)
    assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['access_token']}
def test_cross_tenant_master_source_rejected():
    a,b=account(),account()
    e=c.post('/api/evidence',headers=a,json={'kind':'project','title':'Private work','description':'Private work not for other accounts'}).json()
    item={'category':'project','title':'Copied source','source_evidence_id':e['id']}
    assert c.post('/api/master-profile/items',headers=b,json=item).status_code==404
    own=c.post('/api/master-profile/items',headers=a,json=item)
    assert own.status_code==201
    assert c.put('/api/master-profile/items/'+str(own.json()['id']),headers=b,json=item).status_code==404
    assert c.delete('/api/master-profile/items/'+str(own.json()['id']),headers=b).status_code==404
    assert c.get('/api/master-profile',headers=b).json()['items']==[]
def test_cross_tenant_job_and_fact_reference_rejected():
    a,b=account(),account()
    j=c.post('/api/jobs',headers=a,json={'title':'Backend Engineer','company':'Private Inc','description':'Role for internal engineering only'}).json()
    f=c.post('/api/fact-ledger',headers=a,json={'subject':'Work','predicate':'description','value':'I built a service','source_type':'user_statement'}).json()
    assert c.post('/api/resume/grounded-draft',headers=b,json={'job_id':j['id'],'fact_ids':[f['id']]}).status_code==404
    assert c.post('/api/resume/grounded-draft',headers=b,json={'fact_ids':[f['id']]}).status_code==404
    assert c.post('/api/fact-ledger/'+str(f['id'])+'/correct',headers=b,json={'value':'changed','reason':'not allowed'}).status_code==404
    assert c.get('/api/diagnostic/fact-grounded',headers=b).json()['active_fact_count']==0
def test_session_logout_revokes_token():
    a=account()
    assert c.get('/api/me',headers=a).status_code==200
    assert c.post('/api/auth/logout',headers=a).status_code==200
    assert c.get('/api/me',headers=a).status_code==401
def test_security_headers_and_public_metrics():
    r=c.get('/')
    assert r.headers['x-content-type-options']=='nosniff'
    assert "frame-ancestors 'none'" in r.headers['content-security-policy']
    assert r.headers['cache-control']=='no-store'
    assert c.get('/metrics').status_code==404
