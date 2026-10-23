import uuid, os, sys, tempfile
from pathlib import Path
os.environ.setdefault("ALLOW_TEST_SQLITE","1")
os.environ.setdefault("DATABASE_URL","sqlite:///"+str(Path(tempfile.mkdtemp())/"v9.sqlite3"))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from main import app,engine
from models import Base
Base.metadata.create_all(engine)
c=TestClient(app)

def account():
    email=f'cx-{uuid.uuid4().hex}@example.com'
    payload={'email':email,'password':'strong-password-12345'}
    assert c.post('/api/auth/register',json=payload).status_code==201
    token=c.post('/api/auth/login',json=payload).json()['access_token']
    return {'Authorization':f'Bearer {token}'}

def test_onboarding_and_weekly_brief_are_user_scoped():
    a,b=account(),account()
    first=c.get('/api/onboarding',headers=a).json()
    assert first['completed']==0 and first['total']==4
    profile={'name':'Teste','target_role':'Backend Python','summary':'Desenvolvo APIs reais','hours_per_week':6,'location':'SP','current_salary_cents':None,'target_salary_cents':None}
    assert c.put('/api/profile',headers=a,json=profile).status_code==200
    evidence=c.post('/api/evidence',headers=a,json={'kind':'project','title':'API REST','description':'Desenvolvi API Python com testes'}).json()
    job=c.post('/api/jobs',headers=a,json={'title':'Dev Backend','company':'Empresa A','description':'Backend Python com SQL','requirements':['Python','SQL']}).json()
    assert c.get('/api/onboarding',headers=a).json()['completed']==4
    assert c.get('/api/onboarding',headers=b).json()['completed']==0
    priorities=c.get('/api/career/opportunity-priorities',headers=a).json()
    assert len(priorities['opportunities'])==1
    assert priorities['opportunities'][0]['possible_documentary_matches']==1
    assert c.get('/api/career/opportunity-priorities',headers=b).json()['opportunities']==[]
    brief=c.get('/api/career/weekly-brief',headers=a).json()
    assert brief['hours_available']==6
    assert c.get('/api/career/weekly-brief',headers=b).json()['hours_available']==5
    assert c.put(f"/api/evidence/{evidence['id']}",headers=b,json={'kind':'project','title':'Roubado','description':'Alteração indevida'}).status_code==404
    assert c.put(f"/api/evidence/{evidence['id']}",headers=a,json={'kind':'project','title':'API revisada','description':'Projeto revisado com fatos'}).status_code==200
    task=c.post('/api/tasks',headers=a,json={'title':'Documentar API'}).json()
    assert c.delete(f"/api/tasks/{task['id']}",headers=b).status_code==404
    assert c.delete(f"/api/tasks/{task['id']}",headers=a).status_code==200
    assert c.get('/api/tasks',headers=a).json()==[]

def test_missing_authentication_for_new_customer_endpoints():
    for path in ['/api/onboarding','/api/career/weekly-brief','/api/career/opportunity-priorities']:
        assert c.get(path).status_code==401
