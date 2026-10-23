import os,sys,tempfile
from pathlib import Path
p=Path(tempfile.mkdtemp())/'test.sqlite3'
os.environ['ALLOW_TEST_SQLITE']='1'
os.environ['DATABASE_URL']='sqlite:///'+str(p)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from models import Base
from main import app,engine
Base.metadata.create_all(engine)
c=TestClient(app)
def register(email):
    assert c.post('/api/auth/register',json={'email':email,'password':'securepass12345'}).status_code==201
    r=c.post('/api/auth/login',json={'email':email,'password':'securepass12345'})
    assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['access_token']}

def test_user_isolation_and_diagnostic():
    a=register('alpha@example.com');b=register('bravo@example.com')
    e=c.post('/api/evidence',headers=a,json={'kind':'project','title':'Python API','description':'Projeto pessoal FastAPI sem verificação externa'}).json()
    assert e['status']=='DECLARED'
    assert len(c.get('/api/evidence',headers=b).json())==0
    assert c.delete('/api/evidence/'+str(e['id']),headers=b).status_code==404
    d=c.get('/api/diagnostic',headers=a).json()
    assert d['confidence']=='LIMITED_UNVERIFIED'
    assert 'hiring_probability' not in d
    job=c.post('/api/jobs',headers=a,json={'title':'Backend Junior','company':'Exemplo','description':'Vaga exemplo para desenvolvedor backend','requirements':['Python']}).json()
    assert c.get('/api/jobs/'+str(job['id'])+'/match',headers=b).status_code==402
    assert c.get('/api/jobs/'+str(job['id'])+'/match',headers=a).status_code==402
    assert c.get('/api/account/export',headers=b).json()['evidence']==[]
    assert c.get('/api/billing/status',headers=a).json()['premium_enabled'] is False

def test_auth_and_validation():
    assert c.get('/api/me').status_code==401
    assert c.post('/api/auth/register',json={'email':'invalid','password':'securepass12345'}).status_code==422
    assert c.post('/api/auth/login',json={'email':'nobody@example.com','password':'securepass12345'}).status_code==401

def test_webhook_requires_config():
    assert c.post('/api/billing/webhook',data='{}').status_code==503
