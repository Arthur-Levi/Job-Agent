"""Chromium real DOM E2E with ASGI TestClient network interception.
No TCP loopback required. Uses disposable SQLite; NOT PostgreSQL homologation.
"""
import os, tempfile, sys, uuid
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.environ['ALLOW_TEST_SQLITE']='1'
os.environ['DATABASE_URL']='sqlite:///'+str(Path(tempfile.mkdtemp())/'browser-e2e.sqlite')
os.environ['APP_ENV']='test'
sys.path.insert(0,str(root))
from fastapi.testclient import TestClient
from models import Base
from main import app, engine
from playwright.sync_api import sync_playwright
Base.metadata.create_all(engine)
client=TestClient(app)

def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--no-proxy-server'])
        page=browser.new_page()
        errors=[]
        page.on('pageerror',lambda exc: errors.append(str(exc)))
        def dispatch(route):
            req=route.request
            path=req.url.split('jobagent.test',1)[-1] or '/'
            hdr={k:v for k,v in req.headers.items() if k.lower() in ('authorization','content-type','accept')}
            resp=client.request(req.method,path,headers=hdr,content=req.post_data_buffer)
            route.fulfill(status=resp.status_code,body=resp.content,headers={k:v for k,v in resp.headers.items() if k.lower() in ('content-type','content-security-policy','cache-control')})
        page.route('**/*',dispatch)
        page.goto('http://jobagent.test/')
        assert 'JOB AGENT' in page.locator('body').inner_text()
        email='browser-'+uuid.uuid4().hex+'@example.com'
        page.locator('#email').fill(email)
        page.locator('#password').fill('browser-secure-pass-12345')
        page.locator('#register').click()
        page.get_by_text('Conta criada. Agora clique em Entrar.').wait_for(timeout=12000)
        page.locator('#authForm button[type=submit]').click()
        page.get_by_text('Comece por aqui').wait_for(timeout=12000)
        for tab,expected in [('import','Importar currículo'),('master','Perfil profissional estruturado'),('ledger','Registro de fatos'),('diagnostic','Career Intelligence — diagnóstico rastreável'),('tasks','Execução semanal'),('account','Conta e privacidade')]:
            page.locator(f'[data-tab="{tab}"]').click()
            page.get_by_text(expected,exact=False).first.wait_for(timeout=12000)
        page.locator('#logout').click()
        page.locator('#auth').wait_for(state='visible')
        assert not errors,errors
        browser.close()
        print('CHROMIUM_ASGI_E2E_PASS register/login/dashboard/import/master/ledger/diagnostic/tasks/account/logout')
if __name__=='__main__':main()
