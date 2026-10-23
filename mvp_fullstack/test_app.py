import os
import tempfile
from pathlib import Path

os.environ['JOB_AGENT_MVP_DB'] = str(Path(tempfile.mkdtemp())/'test.sqlite3')
from fastapi.testclient import TestClient
from app import app

c=TestClient(app)

def signup(email):
    password='SecurePassword123!'
    assert c.post('/api/auth/register',json={'email':email,'password':password}).status_code==201
    r=c.post('/api/auth/login',json={'email':email,'password':password})
    assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['access_token']}

def test_user_isolation_and_flow():
    a=signup('a@example.com'); b=signup('b@example.com')
    assert c.get('/api/profile').status_code==401
    p={'name':'Ana','target_role':'Backend Python','current_salary':3500,'target_salary':6000,'hours_per_week':8,'location':'SP','summary':'Desenvolvo APIs em projetos de estudo.'}
    assert c.put('/api/profile',headers=a,json=p).status_code==200
    assert c.get('/api/profile',headers=b).json()['name']==''
    e=c.post('/api/evidence',headers=a,json={'kind':'project','title':'API Python','description':'API construída com Python e SQL','url':''})
    assert e.status_code==201
    assert c.get('/api/evidence',headers=b).json()==[]
    job=c.post('/api/jobs',headers=a,json={'title':'Backend Júnior','company':'Empresa X','description':'Desenvolver aplicações Python e SQL.','requirements':['Python','SQL','Kubernetes']})
    assert job.status_code==201
    jid=job.json()['id']
    assert c.get(f'/api/jobs/{jid}/analysis',headers=b).status_code==404
    match=c.get(f'/api/jobs/{jid}/analysis',headers=a).json()['analysis']
    assert 'Python' in match['matched_requirements']
    assert 'Kubernetes' in match['unconfirmed_requirements']
    assert c.get('/api/diagnostic',headers=a).status_code==200
    assert 'Ana' in c.get(f'/api/jobs/{jid}/resume',headers=a).json()['resume_text']
    assert c.get(f'/api/jobs/{jid}/interview',headers=a).status_code==200
    assert c.post('/api/applications',headers=b,json={'job_id':jid}).status_code==404
    application=c.post('/api/applications',headers=a,json={'job_id':jid})
    assert application.status_code==201
    assert c.patch(f"/api/applications/{application.json()['id']}",headers=b,json={'status':'offer'}).status_code==404
    task=c.post('/api/tasks',headers=a,json={'title':'Preparar entrevista técnica'})
    assert task.status_code==201
    assert c.patch(f"/api/tasks/{task.json()['id']}/toggle",headers=a).json()['done']==1
    assert c.get('/api/dashboard',headers=a).json()['tasks_done']==1
    assert c.delete(f"/api/evidence/{e.json()['id']}",headers=b).status_code==404
    assert c.delete(f"/api/evidence/{e.json()['id']}",headers=a).status_code==200
    assert c.post('/api/auth/logout',headers=a).status_code==200
    assert c.get('/api/profile',headers=a).status_code==401

def test_password_and_duplicate():
    assert c.post('/api/auth/register',json={'email':'bad','password':'short'}).status_code==422
    h=signup('duplicate@example.com')
    assert c.post('/api/auth/register',json={'email':'duplicate@example.com','password':'SecurePassword123!'}).status_code==409
    assert c.post('/api/auth/login',json={'email':'duplicate@example.com','password':'wrongpassword!'}).status_code==401
