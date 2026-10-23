import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

def test_product_account_and_progress():
    with tempfile.TemporaryDirectory() as d:
        os.environ['JOB_AGENT_MVP_DB'] = str(Path(d)/'test.sqlite3')
        import importlib, app as app_module
        m=importlib.reload(app_module)
        c=TestClient(m.app)
        assert c.get('/api/product').json()['billing_enabled'] is False
        assert c.post('/api/auth/register',json={'email':'sample@example.com','password':'a-long-test-password'}).status_code==201
        token=c.post('/api/auth/login',json={'email':'sample@example.com','password':'a-long-test-password'}).json()['access_token']
        h={'Authorization':'Bearer '+token}
        assert c.get('/api/diagnostic/quality',headers=h).json()['complete']==0
        assert c.put('/api/profile',headers=h,json={'name':'Teste','target_role':'Backend Python','summary':'Experiência declarada em projetos reais.'}).status_code==200
        assert c.get('/api/diagnostic/quality',headers=h).json()['complete']==2
        assert c.get('/api/activity',headers=h).json()
        assert c.get('/api/account/export',headers=h).json()['user']['email']=='sample@example.com'
        assert c.post('/api/account/change-password',headers=h,json={'current_password':'a-long-test-password','new_password':'a-new-long-password'}).status_code==200
        assert c.get('/api/me',headers=h).status_code==401
        token2=c.post('/api/auth/login',json={'email':'sample@example.com','password':'a-new-long-password'}).json()['access_token']
        h2={'Authorization':'Bearer '+token2}
        assert c.delete('/api/account',headers=h2).status_code==200
        assert c.get('/api/me',headers=h2).status_code==401
