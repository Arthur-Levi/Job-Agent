"""Local Chromium smoke: run against disposable SQLite only; not production E2E."""
import os,sys,tempfile,time,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
db=Path(tempfile.mkdtemp())/'browser.sqlite'
env={**os.environ,'ALLOW_TEST_SQLITE':'1','DATABASE_URL':'sqlite:///'+str(db),'APP_ENV':'test'}
subprocess.run([sys.executable,'-c','from models import Base; from main import engine; Base.metadata.create_all(engine)'],cwd=root,env=env,check=True)
server=subprocess.Popen([sys.executable,'-m','uvicorn','main:app','--host','127.0.0.1','--port','18765'],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page()
        for _ in range(30):
            try:
                response=page.goto('http://127.0.0.1:18765',timeout=2000)
                if response.status==200: break
                time.sleep(.3)
            except Exception: time.sleep(.2)
        assert 'JOB AGENT' in page.locator('body').inner_text()
        page.locator('#email').fill('browser-v9@example.com')
        page.locator('#password').fill('secure-password-12345')
        page.locator('#register').click()
        page.get_by_role('button',name='Entrar').click()
        page.get_by_text('Comece por aqui').wait_for(timeout=10000)
        page.locator('[data-tab="diagnostic"]').click()
        page.get_by_text('Career Intelligence — diagnóstico rastreável').wait_for()
        page.locator('[data-tab="tasks"]').click()
        page.get_by_text('Execução semanal').wait_for()
        page.locator('[data-tab="account"]').click()
        page.get_by_text('Conta e privacidade').wait_for()
        browser.close()
        print('BROWSER_SMOKE_PASS: register/login/dashboard/diagnostic/tasks/account')
finally:
    server.terminate()
    try:server.wait(timeout=5)
    except:server.kill()
