"""Job Agent MVP — standalone secure beta API (no external AI or payments)."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from collections import defaultdict, deque
from threading import Lock
import time

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('JOB_AGENT_MVP_DB', str(ROOT / 'job_agent_mvp.sqlite3')))
app = FastAPI(title='Job Agent Career Workspace', version='1.1.0', docs_url='/api/docs')

# Local single-process abuse protection; use a shared limiter behind a reverse proxy for deployment.
_rate = defaultdict(deque)
_rate_lock = Lock()
@app.middleware('http')
async def security_headers(request: Request, call_next):
    if request.url.path in ('/api/auth/login', '/api/auth/register'):
        key = (request.client.host if request.client else 'unknown', request.url.path)
        with _rate_lock:
            q = _rate[key]; ts = time.monotonic()
            while q and q[0] < ts - 60: q.popleft()
            if len(q) >= 12:
                return JSONResponse({'detail':'Muitas tentativas. Aguarde um minuto.'},status_code=429,headers={'Retry-After':'60'})
            q.append(ts)
    response = await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Cache-Control']='no-store' if request.url.path.startswith('/api/') else 'no-cache'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    return response

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tokens (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS profiles (user_id INTEGER PRIMARY KEY REFERENCES users(id), name TEXT NOT NULL DEFAULT '', target_role TEXT NOT NULL DEFAULT '', current_salary REAL, target_salary REAL, hours_per_week INTEGER NOT NULL DEFAULT 5, location TEXT NOT NULL DEFAULT '', summary TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS evidence (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), kind TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL, url TEXT NOT NULL DEFAULT '', verified INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), title TEXT NOT NULL, company TEXT NOT NULL, description TEXT NOT NULL, requirements TEXT NOT NULL DEFAULT '[]', url TEXT NOT NULL DEFAULT '', salary_min REAL, salary_max REAL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), job_id INTEGER NOT NULL REFERENCES jobs(id), status TEXT NOT NULL DEFAULT 'saved', notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(user_id,job_id));
CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), category TEXT NOT NULL, description TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_activity_user ON activity(user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_user ON evidence(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
'''

def log_activity(conn, uid, category, description):
    conn.execute('INSERT INTO activity(user_id,category,description,created_at) VALUES (?,?,?,?)',(uid,category,description,now()))

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

with db() as conn:
    conn.executescript(SCHEMA)

def pw_hash(password: str, salt: bytes | None = None):
    salt = salt or secrets.token_bytes(16)
    return salt.hex() + ':' + hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 260000).hex()

def pw_verify(password: str, encoded: str):
    salt, digest = encoded.split(':')
    return hmac.compare_digest(pw_hash(password, bytes.fromhex(salt)).split(':')[1], digest)

def auth(authorization: Annotated[str | None, Header()] = None):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Autenticação necessária')
    token_hash = hashlib.sha256(authorization[7:].encode()).hexdigest()
    with db() as conn:
        row = conn.execute('SELECT user_id FROM tokens WHERE token_hash=? AND expires_at>?', (token_hash, now())).fetchone()
    if not row:
        raise HTTPException(401, 'Sessão inválida ou expirada')
    return row['user_id']

def own(table, item_id, uid):
    with db() as conn:
        row = conn.execute(f'SELECT * FROM {table} WHERE id=? AND user_id=?', (item_id, uid)).fetchone()
    if not row:
        raise HTTPException(404, 'Registro não encontrado')
    return dict(row)

class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=256)

class Profile(BaseModel):
    name: str = Field(default='', max_length=120)
    target_role: str = Field(default='', max_length=120)
    current_salary: float | None = Field(default=None, ge=0, le=1e8)
    target_salary: float | None = Field(default=None, ge=0, le=1e8)
    hours_per_week: int = Field(default=5, ge=0, le=100)
    location: str = Field(default='', max_length=160)
    summary: str = Field(default='', max_length=3000)

class Evidence(BaseModel):
    kind: str = Field(pattern='^(skill|project|experience|education|certificate|language)$')
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=5, max_length=4000)
    url: str = Field(default='', max_length=1000)

class Job(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    company: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=10000)
    requirements: list[str] = Field(default_factory=list, max_length=40)
    url: str = Field(default='', max_length=1000)
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)

class Application(BaseModel):
    job_id: int
    status: str = Field(default='saved', pattern='^(saved|prepared|applied|interview|offer|rejected|withdrawn)$')
    notes: str = Field(default='', max_length=3000)

class Status(BaseModel):
    status: str = Field(pattern='^(saved|prepared|applied|interview|offer|rejected|withdrawn)$')
    notes: str = Field(default='', max_length=3000)

class Task(BaseModel):
    title: str = Field(min_length=3, max_length=300)

@app.post('/api/auth/register', status_code=201)
def register(payload: Credentials):
    email = payload.email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise HTTPException(422, 'E-mail inválido')
    with db() as conn:
        try:
            cursor = conn.execute('INSERT INTO users(email,password_hash,created_at) VALUES (?,?,?)', (email,pw_hash(payload.password),now()))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'E-mail já cadastrado')
        conn.execute('INSERT INTO profiles(user_id) VALUES (?)', (cursor.lastrowid,))
        log_activity(conn,cursor.lastrowid,'account','Conta criada')
    return {'message':'Conta criada'}

@app.post('/api/auth/login')
def login(payload: Credentials):
    with db() as conn:
        row = conn.execute('SELECT * FROM users WHERE email=?', (payload.email.strip().lower(),)).fetchone()
        if not row or not pw_verify(payload.password, row['password_hash']):
            raise HTTPException(401, 'Credenciais inválidas')
        token = secrets.token_urlsafe(48)
        expires = (datetime.now(timezone.utc)+timedelta(days=7)).isoformat()
        conn.execute('INSERT INTO tokens VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(),row['id'],expires))
    return {'access_token':token,'token_type':'bearer','expires_at':expires}

@app.post('/api/auth/logout')
def logout(uid: int = Depends(auth), authorization: Annotated[str | None, Header()] = None):
    with db() as conn:
        conn.execute('DELETE FROM tokens WHERE token_hash=? AND user_id=?', (hashlib.sha256(authorization[7:].encode()).hexdigest(),uid))
    return {'ok':True}

@app.get('/api/me')
def me(uid: int = Depends(auth)):
    with db() as conn:
        return dict(conn.execute('SELECT id,email,created_at FROM users WHERE id=?', (uid,)).fetchone())

@app.get('/api/profile')
def get_profile(uid: int = Depends(auth)):
    with db() as conn:
        return dict(conn.execute('SELECT * FROM profiles WHERE user_id=?', (uid,)).fetchone())

@app.put('/api/profile')
def put_profile(payload: Profile, uid: int = Depends(auth)):
    with db() as conn:
        conn.execute('''UPDATE profiles SET name=?,target_role=?,current_salary=?,target_salary=?,hours_per_week=?,location=?,summary=? WHERE user_id=?''',(*payload.model_dump().values(),uid))
        log_activity(conn,uid,'profile','Perfil atualizado')
    return get_profile(uid)

@app.get('/api/evidence')
def list_evidence(uid: int = Depends(auth)):
    with db() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM evidence WHERE user_id=? ORDER BY id DESC',(uid,))]

@app.post('/api/evidence', status_code=201)
def add_evidence(payload: Evidence, uid: int = Depends(auth)):
    with db() as conn:
        cursor = conn.execute('INSERT INTO evidence(user_id,kind,title,description,url,created_at) VALUES (?,?,?,?,?,?)',(uid,payload.kind,payload.title,payload.description,payload.url,now()))
        log_activity(conn,uid,'evidence','Evidência registrada: '+payload.title[:100])
    return own('evidence',cursor.lastrowid,uid)

@app.delete('/api/evidence/{item_id}')
def delete_evidence(item_id:int, uid:int=Depends(auth)):
    own('evidence',item_id,uid)
    with db() as conn:
        conn.execute('DELETE FROM evidence WHERE id=? AND user_id=?',(item_id,uid))
        log_activity(conn,uid,'evidence','Evidência excluída')
    return {'ok':True}

@app.get('/api/jobs')
def list_jobs(uid:int=Depends(auth)):
    with db() as conn:
        return [{**dict(r),'requirements':json.loads(r['requirements'])} for r in conn.execute('SELECT * FROM jobs WHERE user_id=? ORDER BY id DESC',(uid,))]

@app.post('/api/jobs', status_code=201)
def add_job(payload:Job,uid:int=Depends(auth)):
    with db() as conn:
        cursor=conn.execute('INSERT INTO jobs(user_id,title,company,description,requirements,url,salary_min,salary_max,created_at) VALUES (?,?,?,?,?,?,?,?,?)',(uid,payload.title,payload.company,payload.description,json.dumps(payload.requirements,ensure_ascii=False),payload.url,payload.salary_min,payload.salary_max,now()))
        log_activity(conn,uid,'job','Vaga registrada: '+payload.title[:100])
    result=own('jobs',cursor.lastrowid,uid)
    result['requirements']=json.loads(result['requirements'])
    return result

@app.delete('/api/jobs/{item_id}')
def delete_job(item_id:int,uid:int=Depends(auth)):
    own('jobs',item_id,uid)
    with db() as conn:
        conn.execute('DELETE FROM applications WHERE user_id=? AND job_id=?',(uid,item_id))
        conn.execute('DELETE FROM jobs WHERE user_id=? AND id=?',(uid,item_id))
    return {'ok':True}

STOP={'de','da','do','para','com','the','and','em','uma','um','nos','das','dos','que','por','uma','of','on','and'}
def tokens(s):
    return set(w for w in re.findall(r'[a-zA-ZÀ-ÿ0-9+#.]{2,}',s.lower()) if w not in STOP)

def match(job:dict, evidence:list[dict]):
    """Transparent keyword overlap; NOT probability of hiring or verified skill assessment."""
    corpus=' '.join(e['title']+' '+e['description'] for e in evidence)
    normalized=tokens(corpus)
    requirements=job['requirements']
    found=[]; missing=[]
    for req in requirements:
        key=tokens(req)
        (found if key and key.issubset(normalized) else missing).append(req)
    return {'matched_requirements':found,'unconfirmed_requirements':missing,'coverage':round(len(found)/len(requirements)*100) if requirements else None,'disclaimer':'Cobertura textual de requisitos declarados, não probabilidade de contratação. Evidências não verificadas externamente.'}

@app.get('/api/jobs/{item_id}/analysis')
def job_analysis(item_id:int,uid:int=Depends(auth)):
    job=own('jobs',item_id,uid)
    job['requirements']=json.loads(job['requirements'])
    return {'job':job,'analysis':match(job,list_evidence(uid))}

@app.get('/api/diagnostic')
def diagnostic(uid:int=Depends(auth)):
    p=get_profile(uid); ev=list_evidence(uid); jobs=list_jobs(uid)
    gaps=[]
    if not p['target_role']:gaps.append('Definir o cargo-alvo específico.')
    if not p['summary']:gaps.append('Descrever sua experiência e contexto profissional.')
    if not any(e['kind']=='project' for e in ev):gaps.append('Adicionar um projeto demonstrável, com escopo e resultados reais.')
    if not any(e['kind']=='experience' for e in ev):gaps.append('Registrar experiência real, inclusive estágio ou atividades relevantes, se houver.')
    if not jobs:gaps.append('Cadastrar ao menos uma vaga real para comparar requisitos.')
    actions=[{'day':i+1,'action':a} for i,a in enumerate((gaps+['Revisar os requisitos de uma vaga real.','Aprimorar a descrição de um projeto com evidências.','Preparar respostas para três perguntas técnicas.','Registrar uma candidatura qualificada.','Revisar o que funcionou e atualizar seu plano.'])[:7])]
    return {'profile':p,'evidence_count':len(ev),'job_count':len(jobs),'strengths_declared':[e['title'] for e in ev[:8]],'unknowns':gaps,'seven_day_plan':actions,'methodology':'Análise determinística de informações fornecidas pelo usuário. Não verifica evidências nem prevê salário, contratação ou adequação.'}

@app.get('/api/jobs/{item_id}/resume')
def resume(item_id:int,uid:int=Depends(auth)):
    job=own('jobs',item_id,uid); p=get_profile(uid); ev=list_evidence(uid)
    lines=[p['name'] or 'Nome não informado',p['target_role'] or 'Objetivo profissional não informado',p['location'], '', 'RESUMO PROFISSIONAL',p['summary'] or 'Resumo não informado', '', 'EVIDÊNCIAS DECLARADAS']
    lines += [f"{e['kind'].upper()}: {e['title']} — {e['description']}" + (f" ({e['url']})" if e['url'] else '') for e in ev]
    lines += ['',f"VAGA DE REFERÊNCIA: {job['title']} — {job['company']}",'ATENÇÃO: revise todas as informações antes de enviar. Não foram verificadas externamente.']
    return {'resume_text':'\n'.join(lines),'disclaimer':'Rascunho baseado somente em informações declaradas. Não é enviado automaticamente.'}

@app.get('/api/jobs/{item_id}/interview')
def interview(item_id:int,uid:int=Depends(auth)):
    job=own('jobs',item_id,uid); req=json.loads(job['requirements'])
    questions=[f'Descreva uma situação concreta em que você utilizou {r}. Qual foi seu papel e o resultado?' for r in req[:8]]
    questions += ['Conte sobre um problema técnico que você investigou. Como confirmou a causa?','Como você organizaria seus primeiros 30 dias nesta função?','Qual competência exigida nesta vaga você ainda precisa desenvolver?']
    return {'job_title':job['title'],'questions':questions,'guidance':'Responda com exemplos verdadeiros, contexto, ações, evidências e limitações. Não invente experiência.'}

@app.get('/api/applications')
def list_applications(uid:int=Depends(auth)):
    with db() as conn:
        return [dict(r) for r in conn.execute('SELECT a.*,j.title AS job_title,j.company FROM applications a JOIN jobs j ON j.id=a.job_id AND j.user_id=a.user_id WHERE a.user_id=? ORDER BY a.updated_at DESC',(uid,))]

@app.post('/api/applications',status_code=201)
def add_application(payload:Application,uid:int=Depends(auth)):
    own('jobs',payload.job_id,uid)
    with db() as conn:
        try:
            cursor=conn.execute('INSERT INTO applications(user_id,job_id,status,notes,created_at,updated_at) VALUES (?,?,?,?,?,?)',(uid,payload.job_id,payload.status,payload.notes,now(),now()))
            log_activity(conn,uid,'application','Candidatura adicionada: '+payload.status)
        except sqlite3.IntegrityError:
            raise HTTPException(409,'Vaga já está no acompanhamento')
    return own('applications',cursor.lastrowid,uid)

@app.patch('/api/applications/{item_id}')
def update_application(item_id:int,payload:Status,uid:int=Depends(auth)):
    own('applications',item_id,uid)
    with db() as conn:
        conn.execute('UPDATE applications SET status=?,notes=?,updated_at=? WHERE id=? AND user_id=?',(payload.status,payload.notes,now(),item_id,uid))
        log_activity(conn,uid,'application','Candidatura atualizada: '+payload.status)
    return own('applications',item_id,uid)

@app.get('/api/tasks')
def list_tasks(uid:int=Depends(auth)):
    with db() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC',(uid,))]

@app.post('/api/tasks',status_code=201)
def add_task(payload:Task,uid:int=Depends(auth)):
    with db() as conn:
        cursor=conn.execute('INSERT INTO tasks(user_id,title,created_at) VALUES (?,?,?)',(uid,payload.title,now()))
        log_activity(conn,uid,'task','Tarefa adicionada: '+payload.title[:100])
    return own('tasks',cursor.lastrowid,uid)

@app.patch('/api/tasks/{item_id}/toggle')
def toggle_task(item_id:int,uid:int=Depends(auth)):
    t=own('tasks',item_id,uid)
    with db() as conn:
        conn.execute('UPDATE tasks SET done=? WHERE id=? AND user_id=?',(0 if t['done'] else 1,item_id,uid))
        log_activity(conn,uid,'task','Tarefa '+('reaberta' if t['done'] else 'concluída'))
    return own('tasks',item_id,uid)

@app.get('/api/dashboard')
def dashboard(uid:int=Depends(auth)):
    with db() as conn:
        jobs=conn.execute('SELECT COUNT(*) FROM jobs WHERE user_id=?',(uid,)).fetchone()[0]
        evidence=conn.execute('SELECT COUNT(*) FROM evidence WHERE user_id=?',(uid,)).fetchone()[0]
        tasks=conn.execute('SELECT COUNT(*) FROM tasks WHERE user_id=? AND done=1',(uid,)).fetchone()[0]
        statuses={r['status']:r['n'] for r in conn.execute('SELECT status,COUNT(*) AS n FROM applications WHERE user_id=? GROUP BY status',(uid,))}
    return {'jobs':jobs,'evidence':evidence,'tasks_done':tasks,'applications_by_status':statuses}

@app.get('/api/health')
def health():
    return {'status':'ok','version':'1.0.0-beta'}

@app.get('/')
def home():
    return FileResponse(ROOT/'index.html')


# Product additions: account control, transparent diagnostic quality and progress timeline.
class ChangePassword(BaseModel):
    current_password: str = Field(min_length=12,max_length=256)
    new_password: str = Field(min_length=12,max_length=256)

@app.post('/api/account/change-password')
def change_password(payload:ChangePassword,uid:int=Depends(auth)):
    with db() as conn:
        row=conn.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()
        if not pw_verify(payload.current_password,row['password_hash']):
            raise HTTPException(403,'Senha atual incorreta')
        conn.execute('UPDATE users SET password_hash=? WHERE id=?',(pw_hash(payload.new_password),uid))
        conn.execute('DELETE FROM tokens WHERE user_id=?',(uid,))
        log_activity(conn,uid,'security','Senha alterada; sessões encerradas')
    return {'ok':True,'message':'Senha alterada. Entre novamente.'}

@app.delete('/api/account')
def delete_account(uid:int=Depends(auth)):
    with db() as conn:
        for table in ('activity','applications','tasks','jobs','evidence','profiles','tokens'):
            conn.execute(f'DELETE FROM {table} WHERE '+('user_id' if table!='tokens' else 'user_id')+'=?',(uid,))
        conn.execute('DELETE FROM users WHERE id=?',(uid,))
    return {'ok':True,'message':'Conta e dados associados excluídos do banco ativo. Backups, se existentes, seguem política própria de retenção.'}

@app.get('/api/account/export')
def export_account(uid:int=Depends(auth)):
    with db() as conn:
        user=dict(conn.execute('SELECT id,email,created_at FROM users WHERE id=?',(uid,)).fetchone())
        collections={}
        for table in ('profiles','evidence','jobs','applications','tasks','activity'):
            collections[table]=[dict(r) for r in conn.execute(f'SELECT * FROM {table} WHERE user_id=?',(uid,))]
    return {'user':user,'data':collections,'exported_at':now(),'note':'Dados declarados pelo usuário; não constituem verificação profissional.'}

@app.get('/api/activity')
def activity(uid:int=Depends(auth)):
    with db() as conn:
        return [dict(r) for r in conn.execute('SELECT id,category,description,created_at FROM activity WHERE user_id=? ORDER BY id DESC LIMIT 100',(uid,))]

@app.get('/api/diagnostic/quality')
def diagnostic_quality(uid:int=Depends(auth)):
    p=get_profile(uid); ev=list_evidence(uid); jobs=list_jobs(uid)
    checks=[
      {'item':'Cargo-alvo definido','passed':bool(p['target_role'])},
      {'item':'Contexto profissional descrito','passed':bool(p['summary'])},
      {'item':'Projeto com descrição factual','passed':any(x['kind']=='project' and len(x['description'])>=40 for x in ev)},
      {'item':'Referência de vaga real adicionada','passed':bool(jobs)},
      {'item':'Fonte de evidência indicada','passed':any(x['url'] for x in ev)},
    ]
    return {'checks':checks,'complete':sum(x['passed'] for x in checks),'total':len(checks),'disclaimer':'Indicador de completude das informações, NÃO de empregabilidade, contratação ou verificação externa.'}

@app.get('/api/product')
def product():
    return {'product':'Job Agent Career Professional','status':'local-beta','paid_plan':'planned-not-active','billing_enabled':False,'external_applications_enabled':False,'ai_analysis_enabled':False,'disclaimer':'Produto em validação. Nenhuma cobrança ou candidatura externa é realizada.'}
