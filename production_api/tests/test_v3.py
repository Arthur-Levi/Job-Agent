import os,sys,tempfile,uuid
from pathlib import Path
os.environ['ALLOW_TEST_SQLITE']='1'
os.environ['DATABASE_URL']='sqlite:///'+str(Path(tempfile.mkdtemp())/'v3.sqlite3')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from models import Base,Session,User,Subscription
from main import app,engine,SessionLocal
Base.metadata.create_all(engine)
c=TestClient(app)
def identity():
    email=str(uuid.uuid4())+'@example.com'
    p={'email':email,'password':'a-long-password-123'}
    assert c.post('/api/auth/register',json=p).status_code==201
    t=c.post('/api/auth/login',json=p).json()['access_token']
    return p,{'Authorization':'Bearer '+t}
def test_ui_and_security_headers():
    r=c.get('/');assert r.status_code==200 and 'JOB AGENT' in r.text
    assert 'frame-ancestors' in r.headers['content-security-policy']
    assert c.get('/assets/app.js').status_code==200
    assert c.get('/api/me').status_code==401
def test_account_password_and_isolation():
    p,a=identity();_,b=identity()
    assert c.post('/api/auth/change-password',headers=a,json={'current_password':'wrong','new_password':'new-secure-pass-123'}).status_code==403
    assert c.post('/api/auth/change-password',headers=a,json={'current_password':p['password'],'new_password':'new-secure-pass-123'}).status_code==200
    assert c.get('/api/me',headers=a).status_code==401
    assert c.post('/api/auth/login',json=p).status_code==401
    p['password']='new-secure-pass-123';a={'Authorization':'Bearer '+c.post('/api/auth/login',json=p).json()['access_token']}
    job=c.post('/api/jobs',headers=a,json={'title':'Dev Backend','company':'Empresa A','description':'Precisamos de Python e PostgreSQL','requirements':['Python','PostgreSQL']}).json()
    assert c.delete('/api/jobs/'+str(job['id']),headers=b).status_code==404
    assert c.get('/api/diagnostic/deep',headers=b).json()['requirements']==[]
    assert c.post('/api/evidence',headers=a,json={'kind':'project','title':'Python','description':'Criei uma API Python para estudar'}).status_code==201
    d=c.get('/api/diagnostic/deep',headers=a).json()
    assert d['requirements'][0]['classification']=='POSSIBLE_DECLARED_EVIDENCE'
    assert d['requirements'][1]['classification']=='NOT_DOCUMENTED'
    assert d['evidence_policy']=='DECLARED_ONLY'
    assert c.get('/api/progress',headers=a).status_code==200
    assert c.get('/api/account/export',headers=b).json()['evidence']==[]
def test_checkout_requires_config_and_blocks_existing_subscription(monkeypatch):
    _,a=identity()
    import main
    class StripeStub:
        class checkout:
            class Session:
                @staticmethod
                def create(**kwargs):return type('S',(),{'url':'https://checkout.stripe.com/test'})()
    monkeypatch.setattr(main,'stripe_sdk',lambda:StripeStub)
    monkeypatch.setenv('STRIPE_PRICE_ID','price_test');monkeypatch.setenv('PUBLIC_BASE_URL','https://example.org')
    r=c.post('/api/billing/checkout',headers=a)
    assert r.status_code==200 and r.json()['url'].startswith('https://')
    uid=c.get('/api/me',headers=a).json()['id']
    with SessionLocal() as s:s.add(Subscription(user_id=uid,status='active',stripe_customer_id='cus_test'));s.commit()
    assert c.post('/api/billing/checkout',headers=a).status_code==409
    assert c.get('/api/billing/status',headers=a).json()['premium_enabled']
def test_validation_and_delete():
    p,a=identity()
    assert c.post('/api/evidence',headers=a,json={'kind':'invented','title':'X','description':'bad'}).status_code==422
    assert c.post('/api/account/delete',headers=a,json={'password':'wrong'}).status_code==403
    assert c.post('/api/account/delete',headers=a,json={'password':p['password']}).status_code==200
    assert c.get('/api/me',headers=a).status_code==401
