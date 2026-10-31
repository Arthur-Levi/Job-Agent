"""API end-to-end contract and adversarial isolation tests, with an ephemeral database.
No external Stripe or PostgreSQL connectivity is claimed.
"""
import os,sys,tempfile,uuid
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('ALLOW_TEST_SQLITE','1')
os.environ.setdefault('DATABASE_URL','sqlite:///'+str(Path(tempfile.mkdtemp())/'homologation.sqlite'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlalchemy import select
from models import Base,Subscription,WebhookEvent
import main
Base.metadata.create_all(main.engine)
c=TestClient(main.app)
def user():
    email=f'{uuid.uuid4().hex}@example.com';pw='strong-pass-12345'
    assert c.post('/api/auth/register',json={'email':email,'password':pw}).status_code==201
    r=c.post('/api/auth/login',json={'email':email,'password':pw});assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['access_token']},email,pw

def test_journey_all_modules_and_account_lifecycle():
    a,email,pw=user(); b,_,_=user()
    assert c.get('/api/me',headers=a).json()['email']==email
    profile={'name':'Pessoa Teste','target_role':'Backend','current_salary_cents':350000,'target_salary_cents':600000,'hours_per_week':7,'location':'Remoto','summary':'Projetos documentados em Python'}
    assert c.put('/api/profile',headers=a,json=profile).status_code==200
    assert c.get('/api/profile',headers=b).json()['name']==''
    ev=c.post('/api/evidence',headers=a,json={'kind':'project','title':'Python API','description':'API construída em Python com testes','url':'https://example.com/repo'})
    assert ev.status_code==201;eid=ev.json()['id']
    job=c.post('/api/jobs',headers=a,json={'title':'Backend','company':'Teste','description':'Vaga para Python com PostgreSQL','requirements':['Python','PostgreSQL']})
    assert job.status_code==201;jid=job.json()['id']
    assert c.get('/api/diagnostic/deep',headers=a).json()['requirements'][0]['candidate_evidence'][0]['id']==eid
    assert c.get('/api/diagnostic',headers=a).json()['confidence']=='LIMITED_UNVERIFIED'
    assert c.get(f'/api/jobs/{jid}/match',headers=a).status_code==402
    assert c.get(f'/api/jobs/{jid}/interview',headers=a).status_code==402
    assert c.get('/api/resume',headers=a).status_code==402
    app=c.post('/api/applications',headers=a,json={'job_id':jid,'status':'saved','notes':'primeira análise'});assert app.status_code==201
    aid=app.json()['id']
    assert c.post('/api/applications',headers=a,json={'job_id':jid,'status':'saved'}).status_code==409
    assert c.post('/api/applications',headers=b,json={'job_id':jid,'status':'saved'}).status_code==404
    assert c.put(f'/api/applications/{aid}',headers=b,json={'job_id':jid,'status':'offer'}).status_code==404
    assert c.put(f'/api/applications/{aid}',headers=a,json={'job_id':jid,'status':'interview'}).status_code==200
    task=c.post('/api/tasks',headers=a,json={'title':'Preparar projeto demonstrável'});assert task.status_code==201
    tid=task.json()['id']
    assert c.patch(f'/api/tasks/{tid}',headers=b,json={'done':True}).status_code==404
    assert c.patch(f'/api/tasks/{tid}',headers=a,json={'done':True}).json()['done'] is True
    assert c.get('/api/progress',headers=a).json()['tasks_done']==1
    assert c.get('/api/dashboard',headers=a).json()=={'evidence':1,'jobs':1,'applications':1,'tasks':1}
    export=c.get('/api/account/export',headers=a).json()
    assert len(export['evidence'])==1 and len(export['jobs'])==1 and len(export['tasks'])==1
    assert c.delete(f'/api/evidence/{eid}',headers=b).status_code==404
    assert c.delete(f'/api/jobs/{jid}',headers=b).status_code==404
    assert c.post('/api/account/delete',headers=a,json={'password':'wrong'}).status_code==403
    assert c.post('/api/account/delete',headers=a,json={'password':pw}).status_code==200
    assert c.get('/api/me',headers=a).status_code==401
    assert c.get('/api/me',headers=b).status_code==200

def test_premium_access_is_account_scoped_and_not_client_controlled():
    a,_,_=user();b,_,_=user()
    jid=c.post('/api/jobs',headers=a,json={'title':'Dev','company':'Empresa','description':'Projeto backend com Python','requirements':['Python']}).json()['id']
    with main.SessionLocal() as s:
        uid=c.get('/api/me',headers=a).json()['id']
        s.add(Subscription(user_id=uid,status='active'));s.commit()
    assert c.get(f'/api/jobs/{jid}/match',headers=a).status_code==200
    assert c.get(f'/api/jobs/{jid}/interview',headers=a).status_code==200
    assert c.get('/api/resume',headers=a).status_code==200
    assert c.get(f'/api/jobs/{jid}/match',headers=b).status_code==402
    assert c.get('/api/billing/status',headers=b).json()['premium_enabled'] is False
    assert c.post('/api/account/delete',headers=a,json={'password':'strong-pass-12345'}).status_code==409

def test_password_rotation_revokes_sessions():
    a,email,pw=user()
    second=c.post('/api/auth/login',json={'email':email,'password':pw}).json()
    h2={'Authorization':'Bearer '+second['access_token']}
    assert c.post('/api/auth/change-password',headers=a,json={'current_password':pw,'new_password':'another-secure-password'}).status_code==200
    assert c.get('/api/me',headers=a).status_code==401
    assert c.get('/api/me',headers=h2).status_code==401
    assert c.post('/api/auth/login',json={'email':email,'password':pw}).status_code==401
    assert c.post('/api/auth/login',json={'email':email,'password':'another-secure-password'}).status_code==200

def test_validation_and_no_html_interpolation():
    a,_,_=user()
    assert c.post('/api/evidence',headers=a,json={'kind':'hacked','title':'ok','description':'valid description'}).status_code==422
    assert c.post('/api/jobs',headers=a,json={'title':'x','company':'a','description':'short'}).status_code==422
    assert c.get('/api/account/export').status_code==401
    assert c.get('/metrics').status_code==404
    assert c.get('/health/live').status_code==200
    assert c.get('/health/ready').status_code==200
    assert c.get('/').status_code==200
    assert c.get('/assets/app.js').status_code==200
    assert "innerHTML" not in c.get('/assets/app.js').text
    assert c.get('/').headers['x-content-type-options']=='nosniff'
    assert "frame-ancestors 'none'" in c.get('/').headers['content-security-policy']

def test_webhook_invalid_configuration_and_checkout_unavailable():
    a,_,_=user()
    with patch.dict(os.environ,{'STRIPE_SECRET_KEY':''}):
        assert c.post('/api/billing/checkout',headers=a).status_code==503
        assert c.post('/api/billing/webhook',content=b'{}').status_code==503
    assert c.post('/api/billing/checkout').status_code==401

def test_duplicate_registration_and_auth():
    a,email,pw=user()
    assert c.post('/api/auth/register',json={'email':email.upper(),'password':pw}).status_code==409
    assert c.get('/api/me',headers={'Authorization':'Bearer invalid'}).status_code==401
    assert c.post('/api/auth/login',json={'email':email,'password':'incorrect-password'}).status_code==401

def test_billing_webhook_signature_rejection_and_idempotent_checkout(monkeypatch):
    from types import SimpleNamespace
    a,_,_=user(); uid=c.get('/api/me',headers=a).json()['id']
    calls=[]
    def checkout_create(**kw):
        calls.append(kw)
        return SimpleNamespace(url='https://checkout.stripe.com/c/pay_test')
    class Webhook:
        @staticmethod
        def construct_event(payload,signature,secret):
            if signature!='valid-test-signature':
                raise ValueError('invalid signature')
            return {'id':'evt_'+uuid.uuid4().hex,'type':'checkout.session.completed','data':{'object':{'mode':'subscription','status':'complete','client_reference_id':str(uid),'customer':'cus_test_'+str(uid)}}}
    class Customer:
        @staticmethod
        def modify(*args,**kwargs):return {}
    fake=SimpleNamespace(checkout=SimpleNamespace(Session=SimpleNamespace(create=checkout_create)),Webhook=Webhook,Customer=Customer,error=SimpleNamespace(SignatureVerificationError=ValueError))
    monkeypatch.setattr(main,'stripe_sdk',lambda:fake)
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','whsec_test')
    monkeypatch.setenv('STRIPE_PRICE_ID','price_test')
    monkeypatch.setenv('PUBLIC_BASE_URL','https://example.com')
    assert c.post('/api/billing/webhook',content=b'{}',headers={'stripe-signature':'invalid'}).status_code==400
    first=c.post('/api/billing/checkout',headers=a)
    second=c.post('/api/billing/checkout',headers=a)
    assert first.status_code==second.status_code==200
    assert calls[0]['idempotency_key']==calls[1]['idempotency_key']
    assert c.post('/api/billing/webhook',content=b'{}',headers={'stripe-signature':'valid-test-signature'}).status_code==200
    with main.SessionLocal() as s:
        assert s.get(Subscription,uid).stripe_customer_id=='cus_test_'+str(uid)
    assert c.post('/api/billing/checkout',headers=a).status_code==200 # checkout remains possible before subscription event

def test_subscription_webhook_authoritative_remote_state(monkeypatch):
    from types import SimpleNamespace
    a,_,_=user();uid=c.get('/api/me',headers=a).json()['id']
    customer='cus_'+str(uid); sid='sub_'+str(uid)
    class Webhook:
        @staticmethod
        def construct_event(payload,signature,secret):
            return {'id':'evt_'+uuid.uuid4().hex,'type':'customer.subscription.updated','data':{'object':{'customer':customer,'id':sid,'metadata':{'job_agent_user_id':str(uid)},'status':'canceled'}}}
    class SubscriptionAPI:
        @staticmethod
        def retrieve(*args):return {'status':'active'}
    fake=SimpleNamespace(Webhook=Webhook,Subscription=SubscriptionAPI,Customer=SimpleNamespace(retrieve=lambda customer:{'metadata':{'job_agent_user_id':str(uid)}}),error=SimpleNamespace(SignatureVerificationError=ValueError))
    monkeypatch.setattr(main,'stripe_sdk',lambda:fake)
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','whsec_test')
    assert c.post('/api/billing/webhook',content=b'{}').status_code==200
    monkeypatch.setenv('STRIPE_PRICE_ID','price_test');monkeypatch.setenv('PUBLIC_BASE_URL','https://example.com')
    assert c.get('/api/billing/status',headers=a).json()['premium_enabled'] is True
    assert c.post('/api/billing/checkout',headers=a).status_code==409


def test_sec05_wrong_price_cannot_unlock_premium(monkeypatch):
    """SEC05-FC01 (negative): an active subscription to a DIFFERENT Stripe price must not grant premium."""
    from types import SimpleNamespace
    a,_,_=user()
    uid=c.get('/api/me',headers=a).json()['id']
    customer='cus_sec05_'+str(uid)
    sid='sub_sec05_'+str(uid)
    class Webhook:
        @staticmethod
        def construct_event(payload,signature,secret):
            return {
                'id':'evt_sec05_'+uuid.uuid4().hex,
                'type':'customer.subscription.updated',
                'data':{'object':{
                    'customer':customer,'id':sid,
                    'metadata':{'job_agent_user_id':str(uid)},
                    'status':'active',
                }},
            }
    class SubscriptionAPI:
        @staticmethod
        def retrieve(*args):
            return {
                'id':sid,'customer':customer,'status':'active',
                'items':{'data':[{'price':{'id':'price_unrelated_product'}}]},
            }
    fake=SimpleNamespace(
        Webhook=Webhook,Subscription=SubscriptionAPI,
        Customer=SimpleNamespace(retrieve=lambda _:{'metadata':{'job_agent_user_id':str(uid)}}),
        error=SimpleNamespace(SignatureVerificationError=ValueError),
    )
    monkeypatch.setattr(main,'stripe_sdk',lambda:fake)
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','whsec_simulated')
    monkeypatch.setenv('STRIPE_PRICE_ID','price_jobagent_299')
    response=c.post('/api/billing/webhook',content=b'{}')
    assert response.status_code in (200,400,409,422), response.text
    status=c.get('/api/billing/status',headers=a).json()
    assert status['premium_enabled'] is False, (
        'SEC05-FC01 FAIL: a foreign Stripe price unlocked Job Agent Premium'
    )
