"""Job Agent production API. Requires a migrated PostgreSQL database."""
import hashlib, hmac, json, logging, os, re, secrets, time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Annotated
from fastapi import Depends, FastAPI, Header, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session as DBSession, sessionmaker
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from models import User, Session, Profile, Evidence, Job, Application, Task, Subscription, WebhookEvent, Audit, EvidenceLink, CareerSnapshot, CareerOutcome, EvidenceAssessment, ArtifactReview, MasterProfileItem, CareerFact

logging.basicConfig(level=os.getenv('LOG_LEVEL','INFO'),format='%(asctime)s %(levelname)s %(message)s')
log=logging.getLogger('jobagent')
DB_URL=os.environ.get('DATABASE_URL','')
if not DB_URL: raise RuntimeError('DATABASE_URL obrigatório; use PostgreSQL e aplique Alembic')
if not DB_URL.startswith('postgresql+') and os.getenv('ALLOW_TEST_SQLITE')!='1': raise RuntimeError('Banco de produção deve ser PostgreSQL')
engine=create_engine(DB_URL,pool_pre_ping=True,pool_size=5 if DB_URL.startswith('postgresql') else 0)
SessionLocal=sessionmaker(engine,expire_on_commit=False)
ph=PasswordHasher(time_cost=3,memory_cost=65536,parallelism=2)
DUMMY_PASSWORD_HASH=ph.hash('never-valid-password-123456')
app=FastAPI(title='Job Agent Production API',version='3.0.0',docs_url=None if os.getenv('APP_ENV')=='production' else '/api/docs')
rate=defaultdict(deque); rate_lock=Lock()

def getdb():
    with SessionLocal() as s:
        yield s

def audit(s,uid,action): s.add(Audit(user_id=uid,action=action))

def now(): return datetime.now(timezone.utc)

def serialize(obj, keys): return {k:getattr(obj,k) for k in keys}

@app.middleware('http')
async def headers(req:Request, call_next):
    start=time.monotonic()
    if req.url.path in ('/api/auth/login','/api/auth/register'):
        # Local defense in depth; production must also use gateway-wide rate limits.
        key=(req.client.host if req.client else 'unknown',req.url.path)
        with rate_lock:
            q=rate[key]; t=time.monotonic()
            while q and q[0]<t-60:q.popleft()
            if len(q)>=10:return JSONResponse({'detail':'Tente novamente mais tarde'},429,headers={'Retry-After':'60'})
            q.append(t)
    response=await call_next(req)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Cache-Control']='no-store'
    response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains' if os.getenv('APP_ENV')=='production' else 'max-age=0'
    log.info('request method=%s path=%s status=%s latency_ms=%d',req.method,req.url.path,response.status_code,int((time.monotonic()-start)*1000))
    return response

def current_user(authorization:Annotated[str|None,Header()]=None,s:DBSession=Depends(getdb)):
    if not authorization or not authorization.startswith('Bearer '):raise HTTPException(401,'Autenticação necessária')
    token_hash=hashlib.sha256(authorization[7:].encode()).hexdigest()
    token=s.get(Session,token_hash)
    if not token or (token.expires_at if token.expires_at.tzinfo else token.expires_at.replace(tzinfo=timezone.utc)) <= now() or not s.get(User,token.user_id):raise HTTPException(401,'Sessão inválida')
    return token.user_id

class Credentials(BaseModel):
    email:str=Field(min_length=5,max_length=254)
    password:str=Field(min_length=12,max_length=256)
class ProfileIn(BaseModel):
    name:str=Field(default='',max_length=120)
    target_role:str=Field(default='',max_length=120)
    current_salary_cents:int|None=Field(default=None,ge=0,le=10000000000)
    target_salary_cents:int|None=Field(default=None,ge=0,le=10000000000)
    hours_per_week:int=Field(default=5,ge=0,le=100)
    location:str=Field(default='',max_length=160)
    summary:str=Field(default='',max_length=3000)
class EvidenceIn(BaseModel):
    kind:str=Field(pattern='^(skill|project|experience|education|certificate|language)$')
    title:str=Field(min_length=2,max_length=160)
    description:str=Field(min_length=5,max_length=4000)
    url:str=Field(default='',max_length=1000)
class JobIn(BaseModel):
    title:str=Field(min_length=2,max_length=160)
    company:str=Field(min_length=2,max_length=160)
    description:str=Field(min_length=10,max_length=10000)
    requirements:list[str]=Field(default_factory=list,max_length=40)
    source_url:str=Field(default='',max_length=1000)
class ApplicationIn(BaseModel):
    job_id:int
    status:str=Field(default='saved',pattern='^(saved|prepared|applied|interview|offer|rejected|withdrawn)$')
    notes:str=Field(default='',max_length=3000)
class TaskIn(BaseModel):
    title:str=Field(min_length=3,max_length=300)
class TaskUpdate(BaseModel):
    done:bool

def require_premium(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    sub=s.get(Subscription,uid)
    if not sub or sub.status not in ('active','trialing'):
        raise HTTPException(402,'Career Professional necessário')
    return uid

def owned(s,model,uid,item_id):
    obj=s.scalar(select(model).where(model.id==item_id,model.user_id==uid))
    if not obj:raise HTTPException(404,'Não encontrado')
    return obj

@app.get('/health/live')
def live():return {'status':'ok'}
@app.get('/health/ready')
def ready(s:DBSession=Depends(getdb)):
    from sqlalchemy import text
    s.execute(text('SELECT 1'))
    return {'status':'ready'}

@app.post('/api/auth/register',status_code=201)
def register(p:Credentials,s:DBSession=Depends(getdb)):
    email=p.email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):raise HTTPException(422,'Email inválido')
    if s.scalar(select(User.id).where(User.email==email)):raise HTTPException(409,'Email já cadastrado')
    u=User(email=email,password_hash=ph.hash(p.password));s.add(u)
    try:
        s.flush();s.add(Profile(user_id=u.id));audit(s,u.id,'account.register');s.commit()
    except IntegrityError:
        s.rollback();raise HTTPException(409,'Email já cadastrado')
    return {'ok':True}
@app.post('/api/auth/login')
def login(p:Credentials,s:DBSession=Depends(getdb)):
    u=s.scalar(select(User).where(User.email==p.email.strip().lower()))
    try:
        if not u:
            ph.verify(DUMMY_PASSWORD_HASH,p.password)
            raise HTTPException(401,'Credenciais inválidas')
        if not ph.verify(u.password_hash,p.password):raise HTTPException(401,'Credenciais inválidas')
    except (VerifyMismatchError,VerificationError):raise HTTPException(401,'Credenciais inválidas')
    token=secrets.token_urlsafe(48);expires=now()+timedelta(days=7)
    s.add(Session(token_hash=hashlib.sha256(token.encode()).hexdigest(),user_id=u.id,expires_at=expires));audit(s,u.id,'account.login');s.commit()
    return {'access_token':token,'token_type':'bearer','expires_at':expires.isoformat()}
@app.post('/api/auth/logout')
def logout(authorization:Annotated[str|None,Header()]=None,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    s.delete(s.get(Session,hashlib.sha256(authorization[7:].encode()).hexdigest()));audit(s,uid,'account.logout');s.commit();return {'ok':True}
@app.get('/api/me')
def me(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    u=s.get(User,uid);return serialize(u,['id','email','created_at'])
@app.get('/api/profile')
def profile(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    return serialize(s.get(Profile,uid),list(ProfileIn.model_fields))
@app.put('/api/profile')
def update_profile(p:ProfileIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    o=s.get(Profile,uid)
    for k,v in p.model_dump().items():setattr(o,k,v)
    audit(s,uid,'profile.update');s.commit();return serialize(o,list(ProfileIn.model_fields))

# v12.3: user-confirmed structured profile and append-only fact history.
class MasterItemIn(BaseModel):
    category:str=Field(pattern='^(experience|project|education|certificate|language|skill)$')
    title:str=Field(min_length=2,max_length=180)
    organization:str=Field(default='',max_length=180)
    start_date:str=Field(default='',max_length=10,pattern=r'^(|\d{4}(-\d{2})?(-\d{2})?)$')
    end_date:str=Field(default='',max_length=10,pattern=r'^(|\d{4}(-\d{2})?(-\d{2})?)$')
    description:str=Field(default='',max_length=4000)
    source_evidence_id:int|None=None

class FactIn(BaseModel):
    subject:str=Field(min_length=2,max_length=180)
    predicate:str=Field(min_length=2,max_length=80,pattern=r'^[a-z][a-z0-9_]*$')
    value:str=Field(min_length=1,max_length=4000)
    source_type:str=Field(pattern='^(user_statement|resume_import|evidence|artifact|external_review)$')
    source_reference:str=Field(default='',max_length=300)

class FactCorrection(BaseModel):
    value:str=Field(min_length=1,max_length=4000)
    reason:str=Field(min_length=3,max_length=300)

def item_json(o):
    return serialize(o,['id','category','title','organization','start_date','end_date','description','source_evidence_id','created_at'])
def fact_json(o):
    return serialize(o,['id','subject','predicate','value','source_type','source_reference','verification','status','supersedes_id','created_at'])

@app.get('/api/master-profile')
def master_profile(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    return {'profile':serialize(s.get(Profile,uid),list(ProfileIn.model_fields)),
            'items':[item_json(x) for x in s.scalars(select(MasterProfileItem).where(MasterProfileItem.user_id==uid).order_by(MasterProfileItem.id))]}

@app.post('/api/master-profile/items',status_code=201)
def master_add(p:MasterItemIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    if p.source_evidence_id is not None:owned(s,Evidence,uid,p.source_evidence_id)
    o=MasterProfileItem(user_id=uid,**p.model_dump());s.add(o);audit(s,uid,'master_profile.item.create');s.commit();s.refresh(o)
    return item_json(o)

@app.put('/api/master-profile/items/{item_id}')
def master_edit(item_id:int,p:MasterItemIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    o=owned(s,MasterProfileItem,uid,item_id)
    if p.source_evidence_id is not None:owned(s,Evidence,uid,p.source_evidence_id)
    for k,v in p.model_dump().items():setattr(o,k,v)
    audit(s,uid,'master_profile.item.update');s.commit();return item_json(o)

@app.delete('/api/master-profile/items/{item_id}')
def master_delete(item_id:int,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    s.delete(owned(s,MasterProfileItem,uid,item_id));audit(s,uid,'master_profile.item.delete');s.commit();return {'ok':True}

@app.get('/api/fact-ledger')
def fact_ledger(include_history:bool=False,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    stmt=select(CareerFact).where(CareerFact.user_id==uid)
    if not include_history:stmt=stmt.where(CareerFact.status=='ACTIVE')
    return {'facts':[fact_json(x) for x in s.scalars(stmt.order_by(CareerFact.id.desc()).limit(500))],
            'notice':'USER_DECLARED não representa validação independente. Fontes são referências declaradas.'}

@app.post('/api/fact-ledger',status_code=201)
def fact_add(p:FactIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    if p.source_type=='evidence':
        if not p.source_reference.isdecimal():raise HTTPException(422,'ID de evidência necessário')
        owned(s,Evidence,uid,int(p.source_reference))
    if p.source_type=='external_review':raise HTTPException(422,'Revisão externa requer processo de verificação independente')
    o=CareerFact(user_id=uid,**p.model_dump(),verification='USER_DECLARED');s.add(o);audit(s,uid,'fact.create');s.commit();s.refresh(o);return fact_json(o)

@app.post('/api/fact-ledger/{fact_id}/correct',status_code=201)
def fact_correct(fact_id:int,p:FactCorrection,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    previous=owned(s,CareerFact,uid,fact_id)
    if previous.status!='ACTIVE':raise HTTPException(409,'Fato já substituído')
    previous.status='SUPERSEDED'
    o=CareerFact(user_id=uid,subject=previous.subject,predicate=previous.predicate,value=p.value,
        source_type='user_statement',source_reference='Correção declarada: '+p.reason,
        verification='USER_DECLARED',supersedes_id=previous.id)
    s.add(o);audit(s,uid,'fact.correct');s.commit();s.refresh(o);return fact_json(o)

# v12.4: deterministic contradiction review; conflicting claims are flags, not verdicts.
def _fact_norm(value):
    import unicodedata
    return ' '.join(unicodedata.normalize('NFKD',value.casefold()).encode('ascii','ignore').decode().split())

@app.get('/api/fact-ledger/contradictions')
def fact_contradictions(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    rows=list(s.scalars(select(CareerFact).where(CareerFact.user_id==uid,CareerFact.status=='ACTIVE')))
    buckets={}
    for f in rows:
        buckets.setdefault((_fact_norm(f.subject),f.predicate),[]).append(f)
    conflicts=[]
    for (subject,predicate),group in buckets.items():
        variants={_fact_norm(x.value) for x in group}
        if len(variants)>1:
            conflicts.append({'subject':subject,'predicate':predicate,
                'facts':[{'id':f.id,'value':f.value,'source_type':f.source_type,'verification':f.verification} for f in group],
                'reason':'Declarações diferentes para o mesmo assunto e atributo; revisão humana necessária.'})
    return {'conflicts':conflicts,'method':'Comparação conservadora de atributos declarados; divergência não comprova falsidade.'}

@app.get('/api/diagnostic/fact-grounded')
def diagnostic_fact_grounded(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    profile=s.get(Profile,uid)
    facts=list(s.scalars(select(CareerFact).where(CareerFact.user_id==uid,CareerFact.status=='ACTIVE').order_by(CareerFact.id)))
    jobs=list(s.scalars(select(Job).where(Job.user_id==uid).order_by(Job.id.desc()).limit(10)))
    requirements=[]
    for j in jobs:
        for req in json.loads(j.requirements_json or '[]'):
            if len(requirements)>=100:break
            refs=[{'fact_id':f.id,'subject':f.subject,'verification':f.verification} for f in facts
                  if _fact_norm(req) in _fact_norm(f.subject+' '+f.value)]
            requirements.append({'job_id':j.id,'requirement':req,'declared_support':refs,
                'interpretation':'Menção declarada; competência não verificada' if refs else 'Sem fato registrado correspondente'})
    return {'target_role':profile.target_role,'active_fact_count':len(facts),
        'requirements':requirements,'actions':[
            {'title':'Documentar evidência para '+x['requirement'][:90],'job_id':x['job_id'],'source':'job_requirement'}
            for x in requirements if not x['declared_support']][:5],
        'limitations':['Correspondência textual não prova competência.','Ausência de fato não prova ausência de habilidade.'],
        'hiring_probability':None}

class GroundedResumeIn(BaseModel):
    job_id:int|None=None
    fact_ids:list[int]=Field(default_factory=list,max_length=80)

@app.post('/api/resume/grounded-draft')
def grounded_resume(p:GroundedResumeIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    profile=s.get(Profile,uid)
    job=owned(s,Job,uid,p.job_id) if p.job_id is not None else None
    if len(p.fact_ids)!=len(set(p.fact_ids)):raise HTTPException(422,'IDs de fatos repetidos')
    if p.fact_ids:
        facts=list(s.scalars(select(CareerFact).where(CareerFact.user_id==uid,CareerFact.id.in_(p.fact_ids),CareerFact.status=='ACTIVE')))
        if len(facts)!=len(p.fact_ids):raise HTTPException(404,'Fato não encontrado ou substituído')
        by_id={f.id:f for f in facts};facts=[by_id[i] for i in p.fact_ids]
    else:
        facts=list(s.scalars(select(CareerFact).where(CareerFact.user_id==uid,CareerFact.status=='ACTIVE').order_by(CareerFact.id).limit(80)))
    if not facts:raise HTTPException(422,'Confirme fatos no Fact Ledger antes de gerar o currículo')
    # No generative paraphrase: each claim is an exact, traceable declared value.
    sections=[{'text':f.value,'subject':f.subject,'fact_id':f.id,'verification':f.verification,
               'source_type':f.source_type,'source_reference':f.source_reference} for f in facts]
    lines=[profile.name or 'Nome não informado',
           ('Vaga de referência: '+job.title+' — '+job.company) if job else ('Cargo-alvo: '+(profile.target_role or 'não definido')),
           'INFORMAÇÕES PROFISSIONAIS DECLARADAS']
    lines += [f'- {x["subject"]}: {x["text"]}' for x in sections]
    return {'text':'\n'.join(lines),'claims':sections,'job_id':p.job_id,
        'notice':'Rascunho exclusivamente baseado em fatos declarados. Revise antes de enviar; autoria e competência não verificadas.'}

@app.get('/api/evidence')
def evidence(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    return [serialize(o,['id','kind','title','description','url','status','verification_note','created_at']) for o in s.scalars(select(Evidence).where(Evidence.user_id==uid).order_by(Evidence.id.desc()))]
@app.post('/api/evidence',status_code=201)
def add_evidence(p:EvidenceIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    o=Evidence(user_id=uid,**p.model_dump());s.add(o);audit(s,uid,'evidence.create');s.commit();s.refresh(o)
    return serialize(o,['id','kind','title','description','url','status'])
@app.put('/api/evidence/{item_id}')
def edit_evidence(item_id:int,p:EvidenceIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    o=owned(s,Evidence,uid,item_id)
    for k,v in p.model_dump().items(): setattr(o,k,v)
    # Changing the narrative does not turn earlier assessments into verified competence.
    o.status='DECLARED'
    audit(s,uid,'evidence.update');s.commit()
    return serialize(o,['id','kind','title','description','url','status'])

@app.delete('/api/evidence/{item_id}')
def remove_evidence(item_id:int,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    s.delete(owned(s,Evidence,uid,item_id));audit(s,uid,'evidence.delete');s.commit();return {'ok':True}
@app.get('/api/jobs')
def jobs(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    return [{**serialize(o,['id','title','company','description','source_url']),'requirements':json.loads(o.requirements_json)} for o in s.scalars(select(Job).where(Job.user_id==uid).order_by(Job.id.desc()))]
@app.post('/api/jobs',status_code=201)
def add_job(p:JobIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    o=Job(user_id=uid,title=p.title,company=p.company,description=p.description,requirements_json=json.dumps(p.requirements,ensure_ascii=False),source_url=p.source_url);s.add(o);audit(s,uid,'job.create');s.commit();s.refresh(o)
    return {'id':o.id,'title':o.title}
@app.delete('/api/jobs/{item_id}')
def remove_job(item_id:int,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    s.delete(owned(s,Job,uid,item_id));audit(s,uid,'job.delete');s.commit();return {'ok':True}

def diagnostic_data(s,uid):
    p=s.get(Profile,uid); ev=list(s.scalars(select(Evidence).where(Evidence.user_id==uid)))
    by_kind={k:[e for e in ev if e.kind==k] for k in ('skill','project','experience','education','certificate','language')}
    gaps=[]
    if not p.target_role:gaps.append('Defina um cargo-alvo específico.')
    if not by_kind['project'] and not by_kind['experience']:gaps.append('Inclua um projeto ou experiência que demonstre trabalho real.')
    if not by_kind['skill']:gaps.append('Declare competências técnicas e relacione-as a evidências.')
    if not p.summary:gaps.append('Descreva sua experiência e objetivos com fatos concretos.')
    plan=[{'day':i+1,'action':a} for i,a in enumerate([
      'Revisar cargo-alvo e restrições de localização.',
      'Selecionar um projeto que demonstre competências.',
      'Documentar escopo, decisões e resultados desse projeto.',
      'Escolher uma vaga real e registrar seus requisitos.',
      'Comparar evidências existentes com os requisitos da vaga.',
      'Preparar um currículo sem adicionar experiências inexistentes.',
      'Revisar lacunas, feedback e prioridades da semana seguinte.'])]
    return {'target_role':p.target_role,'evidence_count':len(ev),'declared_evidence':[{'id':e.id,'kind':e.kind,'title':e.title,'status':e.status,'url':e.url} for e in ev],
       'gaps':gaps,'seven_day_plan':plan,'confidence':'LIMITED_UNVERIFIED','limitations':['Evidências enviadas não são verificadas automaticamente.','Não estima chance de contratação ou aumento salarial.','Recomendações dependem da qualidade dos dados declarados.']}
@app.get('/api/diagnostic')
def diagnostic(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):return diagnostic_data(s,uid)
@app.get('/api/jobs/{item_id}/match')
def match(item_id:int,uid:int=Depends(require_premium),s:DBSession=Depends(getdb)):
    j=owned(s,Job,uid,item_id); ev=list(s.scalars(select(Evidence).where(Evidence.user_id==uid)))
    requirements=json.loads(j.requirements_json)
    supported=[];unresolved=[]
    for req in requirements:
        # A keyword match is only a lead for review, never proof of competence.
        refs=[{'id':e.id,'title':e.title,'status':e.status} for e in ev if req.casefold() in (e.title+' '+e.description).casefold()]
        (supported if refs else unresolved).append({'requirement':req,'candidate_evidence':refs} if refs else {'requirement':req,'reason':'Nenhuma evidência textual correspondente; requer revisão humana.'})
    return {'job_id':j.id,'potential_matches':supported,'unresolved_requirements':unresolved,'hiring_probability':None,'disclaimer':'Correspondência textual não é verificação de competência nem probabilidade de contratação.'}
@app.get('/api/resume')
def resume(uid:int=Depends(require_premium),s:DBSession=Depends(getdb)):
    p=s.get(Profile,uid);ev=list(s.scalars(select(Evidence).where(Evidence.user_id==uid)))
    lines=[p.name or 'Nome não informado',p.target_role or 'Cargo-alvo não informado',p.summary or 'Resumo não informado']
    for e in ev:lines.append(f'{e.kind.upper()}: {e.title} — {e.description} (DECLARADO; {e.url or "sem URL"})')
    return {'text':'\n\n'.join(lines),'notice':'Rascunho baseado em declarações. Revise e aprove antes de utilizar externamente.'}
@app.get('/api/jobs/{item_id}/interview')
def interview(item_id:int,uid:int=Depends(require_premium),s:DBSession=Depends(getdb)):
    j=owned(s,Job,uid,item_id)
    reqs=json.loads(j.requirements_json)
    return {'job_id':j.id,'questions':[f'Explique um projeto em que utilizou {r} e quais evidências demonstram sua participação.' for r in reqs[:8]] or ['Descreva uma decisão técnica importante e seus resultados.'],'notice':'Perguntas preparatórias, não avaliação real de recrutadores.'}
@app.get('/api/applications')
def applications(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    return [serialize(o,['id','job_id','status','notes']) for o in s.scalars(select(Application).where(Application.user_id==uid))]
@app.post('/api/applications',status_code=201)
def add_application(p:ApplicationIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    owned(s,Job,uid,p.job_id)
    if s.scalar(select(Application.id).where(Application.user_id==uid,Application.job_id==p.job_id)):raise HTTPException(409,'Candidatura já registrada')
    o=Application(user_id=uid,**p.model_dump());s.add(o);audit(s,uid,'application.create');s.commit();s.refresh(o);return serialize(o,['id','job_id','status','notes'])
@app.put('/api/applications/{item_id}')
def update_application(item_id:int,p:ApplicationIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    o=owned(s,Application,uid,item_id);owned(s,Job,uid,p.job_id)
    o.job_id=p.job_id;o.status=p.status;o.notes=p.notes;audit(s,uid,'application.update');s.commit();return serialize(o,['id','job_id','status','notes'])
@app.get('/api/tasks')
def tasks(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    return [serialize(o,['id','title','done']) for o in s.scalars(select(Task).where(Task.user_id==uid))]
@app.post('/api/tasks',status_code=201)
def add_task(p:TaskIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    o=Task(user_id=uid,title=p.title);s.add(o);audit(s,uid,'task.create');s.commit();s.refresh(o);return serialize(o,['id','title','done'])
@app.patch('/api/tasks/{item_id}')
def update_task(item_id:int,p:TaskUpdate,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    o=owned(s,Task,uid,item_id);o.done=p.done;audit(s,uid,'task.update');s.commit();return serialize(o,['id','title','done'])
@app.delete('/api/tasks/{item_id}')
def delete_task(item_id:int,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    s.delete(owned(s,Task,uid,item_id));audit(s,uid,'task.delete');s.commit()
    return {'ok':True}

@app.get('/api/dashboard')
def dashboard(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    def count(model):return s.scalar(select(func.count()).select_from(model).where(model.user_id==uid))
    return {'evidence':count(Evidence),'jobs':count(Job),'applications':count(Application),'tasks':count(Task)}
@app.get('/api/onboarding')
def onboarding(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    p=s.get(Profile,uid)
    evidence_count=s.scalar(select(func.count()).select_from(Evidence).where(Evidence.user_id==uid))
    jobs_with_requirements=sum(bool(json.loads(j.requirements_json or '[]')) for j in s.scalars(select(Job).where(Job.user_id==uid)))
    checks=[
        {'key':'target','label':'Definir cargo-alvo','done':bool(p.target_role.strip()),'next_tab':'dashboard','focus':'profile'},
        {'key':'summary','label':'Descrever experiência real','done':bool(p.summary.strip()),'next_tab':'dashboard','focus':'profile'},
        {'key':'evidence','label':'Cadastrar ao menos uma evidência','done':bool(evidence_count),'next_tab':'evidence'},
        {'key':'job','label':'Adicionar uma vaga com requisitos','done':bool(jobs_with_requirements),'next_tab':'jobs'},
    ]
    return {'completed':sum(c['done'] for c in checks),'total':len(checks),'steps':checks,'disclaimer':'Completude do cadastro, não pontuação de empregabilidade.'}

@app.get('/api/career/opportunity-priorities')
def opportunity_priorities(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    # No fabricated fit probability: count traceable documentary signals only.
    # Derive from the already deployed, user-scoped intelligence endpoint.
    intelligence=career_intelligence(uid,s)
    rows=[]
    for opportunity in intelligence.get('opportunities',[]):
        requirements=opportunity.get('requirements',[])
        total=len(requirements)
        documented=sum(r.get('state')!='NOT_DOCUMENTED' for r in requirements)
        rows.append({'job_id':opportunity.get('job_id',opportunity.get('id')),'title':opportunity.get('title'),
                     'company':opportunity.get('company'),'requirements_total':total,
                     'possible_documentary_matches':documented,'undocumented':total-documented,
                     'priority_basis':'Quantidade de requisitos com indícios declarados; não é adequação profissional nem chance de contratação.'})
    rows.sort(key=lambda x:(-x['possible_documentary_matches'], x['undocumented'], x['title'] or ''))
    return {'opportunities':rows,'limitations':['Vagas são cadastradas pelo usuário e não validadas externamente.','Correspondência documental não comprova domínio técnico.','Ordenação não representa probabilidade de contratação.']}

@app.get('/api/career/weekly-brief')
def weekly_brief(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    p=s.get(Profile,uid)
    todo=list(s.scalars(select(Task).where(Task.user_id==uid,Task.done==False).order_by(Task.id.desc()).limit(5)))
    done=s.scalar(select(func.count()).select_from(Task).where(Task.user_id==uid,Task.done==True))
    total=s.scalar(select(func.count()).select_from(Task).where(Task.user_id==uid))
    applications=list(s.scalars(select(Application).where(Application.user_id==uid)))
    status_counts={k:sum(a.status==k for a in applications) for k in ('saved','prepared','applied','interview','offer','rejected','withdrawn')}
    onboarding_state=onboarding(uid,s)
    recommendations=[]
    if onboarding_state['completed']<onboarding_state['total']:
        recommendations.append({'action':'Completar informações essenciais do diagnóstico','why':'Há etapas do cadastro pendentes.'})
    if not todo:
        recommendations.append({'action':'Escolher uma ação profissional verificável para esta semana','why':'Não existem tarefas abertas no plano.'})
    else:
        recommendations.extend({'action':t.title,'why':'Tarefa pendente registrada por você.'} for t in todo[:3])
    if status_counts['applied'] and not status_counts['interview'] and not status_counts['offer']:
        recommendations.append({'action':'Revisar candidaturas e registrar feedback real','why':'Existem candidaturas enviadas, sem entrevista ou oferta registrada no pipeline atual.'})
    return {'target_role':p.target_role,'hours_available':p.hours_per_week,'onboarding':onboarding_state,
            'tasks':{'completed':done,'total':total,'open':total-done},'applications_by_status':status_counts,
            'next_actions':recommendations[:4],
            'limitations':['O relatório usa apenas dados informados no Job Agent.','Sem confirmação de resultados externos ou causalidade.']}

@app.get('/api/account/export')
def account_export(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    u=s.get(User,uid)
    p=s.get(Profile,uid)
    data={'user':serialize(u,['email','created_at']),'profile':serialize(p,list(ProfileIn.model_fields))}
    for key,model,fields in [('evidence',Evidence,['kind','title','description','url','status','verification_note']),('jobs',Job,['title','company','description','requirements_json','source_url']),('applications',Application,['job_id','status','notes']),('tasks',Task,['title','done'])]:
        data[key]=[serialize(obj,fields) for obj in s.scalars(select(model).where(model.user_id==uid))]
    for key,model,fields in [('evidence_links',EvidenceLink,['evidence_id','requirement','relation','rationale','created_at']),('career_snapshots',CareerSnapshot,['created_at','fingerprint','metrics_json','recommendations_json','explanation_json']),('career_outcomes',CareerOutcome,['kind','description','job_id','created_at']),('evidence_assessments',EvidenceAssessment,['evidence_id','rubric_version','submission_json','result_json','created_at']),('artifact_reviews',ArtifactReview,['evidence_id','review_version','inventory_sha256','result_json','created_at'])]:
        data[key]=[serialize(obj,fields) for obj in s.scalars(select(model).where(model.user_id==uid))]
    data['master_profile_items']=[item_json(x) for x in s.scalars(select(MasterProfileItem).where(MasterProfileItem.user_id==uid))]
    data['fact_ledger']=[fact_json(x) for x in s.scalars(select(CareerFact).where(CareerFact.user_id==uid))]
    return data

class DeleteConfirm(BaseModel):
    password:str

@app.post('/api/account/delete')
def account_delete(p:DeleteConfirm,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    u=s.get(User,uid)
    try:ph.verify(u.password_hash,p.password)
    except (VerifyMismatchError,VerificationError):raise HTTPException(403,'Senha incorreta')
    sub=s.get(Subscription,uid)
    if sub and (sub.stripe_subscription_id or sub.status in ('active','trialing','past_due','unpaid','incomplete','paused')):
        raise HTTPException(409,'Finalize ou resolva sua assinatura no Stripe antes de excluir a conta')
    for model in (CareerFact,MasterProfileItem,ArtifactReview,EvidenceAssessment,CareerOutcome,CareerSnapshot,EvidenceLink,Application,Task,Evidence,Job,Session,Profile,Subscription):
        for obj in s.scalars(select(model).where(model.user_id==uid)):s.delete(obj)
    s.flush();s.delete(u);s.commit()
    return {'ok':True}

@app.get('/api/billing/status')
def billing_status(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    o=s.get(Subscription,uid)
    return {'plan':'Career Professional','status':o.status if o else 'inactive','premium_enabled':bool(o and o.status in ('active','trialing'))}

def stripe_sdk():
    try:import stripe
    except ImportError:raise HTTPException(503,'Stripe SDK não instalado')
    if not os.getenv('STRIPE_SECRET_KEY'):raise HTTPException(503,'Cobrança não configurada')
    stripe.api_key=os.environ['STRIPE_SECRET_KEY'];return stripe

@app.post('/api/billing/checkout')
def checkout(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    stripe=stripe_sdk()
    price=os.getenv('STRIPE_PRICE_ID');base=os.getenv('PUBLIC_BASE_URL','')
    if not price or not base.startswith('https://'):raise HTTPException(503,'Configure STRIPE_PRICE_ID e PUBLIC_BASE_URL HTTPS')
    user=s.get(User,uid); sub=s.get(Subscription,uid)
    if sub and sub.status in ('active','trialing','past_due','unpaid','incomplete','paused'):
        raise HTTPException(409,'Assinatura existente; utilize o portal para gerenciá-la')
    params=dict(mode='subscription',line_items=[{'price':price,'quantity':1}],client_reference_id=str(uid),
        subscription_data={'metadata':{'job_agent_user_id':str(uid)}},
        success_url=base+'/billing/success',cancel_url=base+'/billing/cancel',
        allow_promotion_codes=False,idempotency_key=None)
    params.pop('idempotency_key')
    if sub and sub.stripe_customer_id:params['customer']=sub.stripe_customer_id
    else:params['customer_email']=user.email
    # Stable idempotency key during a short interval prevents retry-based duplicate checkout sessions.
    key='ja-checkout-'+str(uid)+'-'+str(int(time.time()//600))
    # Reuse Stripe customer for subsequent checkout attempts; bind customer to this account.
    session=stripe.checkout.Session.create(**params,idempotency_key=key)
    audit(s,uid,'billing.checkout.started');s.commit()
    return {'url':session.url}
@app.post('/api/billing/portal')
def billing_portal(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    stripe=stripe_sdk();o=s.get(Subscription,uid);base=os.getenv('PUBLIC_BASE_URL','')
    if not o or not o.stripe_customer_id:raise HTTPException(404,'Nenhuma assinatura encontrada')
    if not base.startswith('https://'):raise HTTPException(503,'URL pública HTTPS necessária')
    session=stripe.billing_portal.Session.create(customer=o.stripe_customer_id,return_url=base+'/account')
    return {'url':session.url}
@app.post('/api/billing/webhook')
async def stripe_webhook(req:Request,s:DBSession=Depends(getdb)):
    stripe=stripe_sdk();secret=os.getenv('STRIPE_WEBHOOK_SECRET')
    if not secret:raise HTTPException(503,'Webhook não configurado')
    payload=await req.body()
    if len(payload)>1048576:raise HTTPException(413,'Payload muito grande')
    try:event=stripe.Webhook.construct_event(payload,req.headers.get('stripe-signature',''),secret)
    except (ValueError,stripe.error.SignatureVerificationError):raise HTTPException(400,'Assinatura inválida')
    if s.get(WebhookEvent,event['id']):return {'received':True,'duplicate':True}
    obj=event['data']['object'];typ=event['type']
    if typ in ('customer.subscription.created','customer.subscription.updated','customer.subscription.deleted'):
        customer=obj.get('customer');subscription_id=obj.get('id')
        if not customer or not subscription_id:raise HTTPException(400,'Evento incompleto')
        existing=s.scalar(select(Subscription).where(Subscription.stripe_subscription_id==subscription_id))
        if not existing:existing=s.scalar(select(Subscription).where(Subscription.stripe_customer_id==customer))
        if not existing:
            cust=stripe.Customer.retrieve(customer)
            uid_raw=(obj.get('metadata') or {}).get('job_agent_user_id') or (cust.get('metadata') or {}).get('job_agent_user_id')
            if uid_raw and str(uid_raw).isdigit() and s.get(User,int(uid_raw)):
                existing=s.get(Subscription,int(uid_raw)) or Subscription(user_id=int(uid_raw))
                if not existing in s:s.add(existing)
        if existing:
            if existing.stripe_customer_id and existing.stripe_customer_id!=customer:
                raise HTTPException(409,'Assinatura vinculada a outro cliente Stripe')
            if existing.stripe_subscription_id and existing.stripe_subscription_id!=subscription_id:
                log.error('multiple subscriptions customer=%s',customer)
                raise HTTPException(409,'Assinaturas conflitantes: requer reconciliação')
            # Always retrieve current authoritative subscription state: event arrival order cannot downgrade a newer state.
            remote=stripe.Subscription.retrieve(subscription_id)
            existing.stripe_customer_id=customer
            existing.stripe_subscription_id=subscription_id
            existing.status=remote.get('status','inactive')
        else:
            log.warning('unmatched subscription event=%s',event['id'])
            raise HTTPException(503,'Assinatura sem usuário; tentar novamente após checkout')
    elif typ=='checkout.session.completed':
        if obj.get('mode')!='subscription' or obj.get('status')!='complete':
            raise HTTPException(400,'Checkout não confirmado')
        uid_raw=obj.get('client_reference_id');customer=obj.get('customer')
        if uid_raw and str(uid_raw).isdigit() and s.get(User,int(uid_raw)) and customer:
            conflicting=s.scalar(select(Subscription).where(Subscription.stripe_customer_id==customer,Subscription.user_id!=int(uid_raw)))
            if conflicting:raise HTTPException(409,'Cliente Stripe já vinculado')
            sub=s.get(Subscription,int(uid_raw))
            if not sub:sub=Subscription(user_id=int(uid_raw));s.add(sub)
            if sub.stripe_customer_id and sub.stripe_customer_id!=customer:raise HTTPException(409,'Conta Stripe conflitante')
            sub.stripe_customer_id=customer
            stripe.Customer.modify(customer,metadata={'job_agent_user_id':str(uid_raw)})
        else:
            raise HTTPException(503,'Checkout sem vínculo válido; evento será reprocessado')
    s.add(WebhookEvent(id=event['id']))
    try:s.commit()
    except IntegrityError:
        s.rollback()
        if s.get(WebhookEvent,event['id']):return {'received':True,'duplicate':True}
        raise HTTPException(409,'Conflito de persistência; evento deve ser reprocessado')
    return {'received':True}

class ChangePassword(BaseModel):
    current_password:str
    new_password:str=Field(min_length=12,max_length=256)

@app.post('/api/auth/change-password')
def change_password(p:ChangePassword,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    u=s.get(User,uid)
    try:ph.verify(u.password_hash,p.current_password)
    except (VerifyMismatchError,VerificationError):raise HTTPException(403,'Senha atual incorreta')
    if p.current_password==p.new_password:raise HTTPException(422,'Escolha uma senha diferente')
    u.password_hash=ph.hash(p.new_password)
    for sess in s.scalars(select(Session).where(Session.user_id==uid)):s.delete(sess)
    audit(s,uid,'account.password.changed');s.commit()
    return {'ok':True,'message':'Todas as sessões foram encerradas'}

@app.get('/api/diagnostic/deep')
def deep_diagnostic(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    p=s.get(Profile,uid)
    ev=list(s.scalars(select(Evidence).where(Evidence.user_id==uid)))
    jobs=list(s.scalars(select(Job).where(Job.user_id==uid)))
    requirements=[]
    for j in jobs:
        for req in json.loads(j.requirements_json):
            if req.strip() and req.casefold() not in [x.casefold() for x in requirements]:requirements.append(req.strip())
    comparisons=[]
    for req in requirements[:60]:
        candidates=[{'id':e.id,'title':e.title,'kind':e.kind,'status':e.status,'source_url':e.url or None} for e in ev if req.casefold() in (e.title+' '+e.description).casefold()]
        comparisons.append({'requirement':req,'classification':'POSSIBLE_DECLARED_EVIDENCE' if candidates else 'NOT_DOCUMENTED','candidate_evidence':candidates,
            'recommended_action':'Revisar a evidência e comprovar com projeto ou resultado verificável.' if candidates else 'Documentar evidência verdadeira ou priorizar aprendizado prático.'})
    missing=[x['requirement'] for x in comparisons if x['classification']=='NOT_DOCUMENTED']
    actions=[]
    if not p.target_role:actions.append('Definir um cargo-alvo e critérios de escolha.')
    if not jobs:actions.append('Cadastrar ao menos uma vaga real com requisitos explícitos.')
    if not ev:actions.append('Registrar projetos, experiências e competências com contexto e resultados.')
    actions += ['Produzir evidência prática para: '+x for x in missing[:3]]
    if not actions:actions.append('Revisar as evidências candidatas e validar cada requisito manualmente.')
    return {'target_role':p.target_role,'jobs_compared':len(jobs),'evidence_count':len(ev),'requirements':comparisons,
        'priority_actions':actions,'evidence_policy':'DECLARED_ONLY','method':'comparação textual transparente; não usa IA generativa nem validação externa',
        'limitations':['Correspondência textual não prova proficiência.','A ausência de evidência não prova ausência de competência.','Não estima contratação, salário ou chance de aprovação.']}

@app.get('/api/intelligence')
def career_intelligence(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    """Unified explainable analysis. Never accepts another user's IDs from the caller."""
    from career_intelligence import analyze
    p=s.get(Profile,uid)
    evidence=[{'id':e.id,'kind':e.kind,'title':e.title,'description':e.description,
               'url':e.url,'status':e.status} for e in s.scalars(select(Evidence).where(Evidence.user_id==uid))]
    jobs=[{'id':j.id,'title':j.title,'company':j.company,'source_url':j.source_url,
           'requirements':json.loads(j.requirements_json)} for j in s.scalars(select(Job).where(Job.user_id==uid))]
    apps=[{'status':a.status} for a in s.scalars(select(Application).where(Application.user_id==uid))]
    tasks=[{'done':t.done} for t in s.scalars(select(Task).where(Task.user_id==uid))]
    return analyze({'target_role':p.target_role},evidence,jobs,apps,tasks)

@app.get('/api/progress')
def progress(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    apps=list(s.scalars(select(Application).where(Application.user_id==uid)))
    tasks=list(s.scalars(select(Task).where(Task.user_id==uid)))
    return {'applications_by_status':{status:sum(a.status==status for a in apps) for status in ('saved','prepared','applied','interview','offer','rejected','withdrawn')},
        'tasks_done':sum(t.done for t in tasks),'tasks_total':len(tasks),'note':'Indicadores operacionais; não representam probabilidade de contratação.'}


# Career graph: user-owned, explicit links; links do not verify proficiency.
class EvidenceLinkIn(BaseModel):
    evidence_id:int=Field(gt=0)
    requirement:str=Field(min_length=2,max_length=160)
    rationale:str=Field(default='',max_length=1000)

class OutcomeIn(BaseModel):
    kind:str=Field(pattern='^(interview|rejection|offer|application_sent|feedback|milestone)$')
    description:str=Field(min_length=3,max_length=2000)
    job_id:int|None=None

def graph_payload(s,uid):
    ev=list(s.scalars(select(Evidence).where(Evidence.user_id==uid)))
    links=list(s.scalars(select(EvidenceLink).where(EvidenceLink.user_id==uid)))
    jobs=list(s.scalars(select(Job).where(Job.user_id==uid)))
    requirements=sorted({r.strip() for j in jobs for r in json.loads(j.requirements_json) if r.strip()},key=str.casefold)
    return {'evidence':[serialize(e,['id','kind','title','status','url']) for e in ev],
            'requirements':requirements,
            'links':[serialize(l,['id','evidence_id','requirement','relation','rationale','created_at']) for l in links],
            'disclaimer':'Ligações declaradas pelo usuário; não representam verificação independente de proficiência.'}

@app.get('/api/career/graph')
def get_graph(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    return graph_payload(s,uid)

@app.post('/api/career/graph/links',status_code=201)
def create_link(p:EvidenceLinkIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    owned(s,Evidence,uid,p.evidence_id)
    req=p.requirement.strip()
    if not req:raise HTTPException(422,'Requisito vazio')
    existing=s.scalar(select(EvidenceLink).where(EvidenceLink.user_id==uid,EvidenceLink.evidence_id==p.evidence_id,EvidenceLink.requirement==req))
    if existing:raise HTTPException(409,'Ligação já existe')
    link=EvidenceLink(user_id=uid,evidence_id=p.evidence_id,requirement=req,relation='SUPPORTS',rationale=p.rationale)
    s.add(link);s.commit();s.refresh(link)
    return serialize(link,['id','evidence_id','requirement','relation','rationale'])

@app.delete('/api/career/graph/links/{link_id}')
def delete_link(link_id:int,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    link=owned(s,EvidenceLink,uid,link_id);s.delete(link);s.commit();return {'ok':True}

@app.post('/api/career/outcomes',status_code=201)
def add_outcome(p:OutcomeIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    if p.job_id is not None:owned(s,Job,uid,p.job_id)
    o=CareerOutcome(user_id=uid,kind=p.kind,description=p.description,job_id=p.job_id)
    s.add(o);s.commit();s.refresh(o);return serialize(o,['id','kind','description','job_id','created_at'])

@app.get('/api/career/outcomes')
def get_outcomes(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    return [serialize(o,['id','kind','description','job_id','created_at']) for o in s.scalars(select(CareerOutcome).where(CareerOutcome.user_id==uid).order_by(CareerOutcome.id.desc()).limit(100))]

def career_metrics(s,uid):
    from career_intelligence import analyze
    p=s.get(Profile,uid)
    ev=list(s.scalars(select(Evidence).where(Evidence.user_id==uid)))
    jobs=list(s.scalars(select(Job).where(Job.user_id==uid)))
    tasks=list(s.scalars(select(Task).where(Task.user_id==uid)))
    apps=list(s.scalars(select(Application).where(Application.user_id==uid)))
    links=list(s.scalars(select(EvidenceLink).where(EvidenceLink.user_id==uid)))
    outcomes=list(s.scalars(select(CareerOutcome).where(CareerOutcome.user_id==uid)))
    analysis=analyze({'target_role':p.target_role},[serialize(e,['id','kind','title','description','url','status']) for e in ev],
        [{'id':j.id,'title':j.title,'company':j.company,'source_url':j.source_url,'requirements':json.loads(j.requirements_json)} for j in jobs],
        [{'status':a.status} for a in apps],[{'done':t.done} for t in tasks])
    metrics={'evidence':len(ev),'jobs':len(jobs),'links':len(links),'tasks_completed':sum(t.done for t in tasks),
             'applications':sum(a.status in ('applied','interview','offer','rejected') for a in apps),
             'interviews_reported':sum(o.kind=='interview' for o in outcomes),'offers_reported':sum(o.kind=='offer' for o in outcomes)}
    recommendations=analysis.get('top_actions',[])
    if not links and ev and jobs:
        recommendations=[{'action':'Vincular evidências existentes aos requisitos das vagas','why':'Ainda não há conexões explícitas entre competências e requisitos.','linked_jobs':[]}]+recommendations
    if any(o.kind=='rejection' for o in outcomes):
        recommendations=[{'action':'Revisar o feedback de candidaturas recusadas','why':'Há rejeições registradas; avalie feedback antes de alterar a estratégia.','linked_jobs':[]}]+recommendations
    return metrics,recommendations[:3],{'analysis_quality':analysis.get('quality',{}),'limitations':analysis.get('uncertainties',[]),'source':'dados declarados e registros operacionais'}

@app.post('/api/career/checkins',status_code=201)
def create_checkin(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    metrics,recs,explanation=career_metrics(s,uid)
    payload=json.dumps({'metrics':metrics,'recommendations':recs},sort_keys=True,ensure_ascii=False)
    fingerprint=hashlib.sha256(payload.encode()).hexdigest()
    previous=s.scalar(select(CareerSnapshot).where(CareerSnapshot.user_id==uid).order_by(CareerSnapshot.id.desc()))
    if previous and previous.fingerprint==fingerprint:
        return {'id':previous.id,'unchanged':True,'metrics':metrics,'recommendations':recs,'delta':{k:0 for k in metrics}}
    prior=json.loads(previous.metrics_json) if previous else {}
    delta={k:metrics[k]-prior.get(k,0) for k in metrics}
    snapshot=CareerSnapshot(user_id=uid,fingerprint=fingerprint,metrics_json=json.dumps(metrics),recommendations_json=json.dumps(recs,ensure_ascii=False),explanation_json=json.dumps(explanation,ensure_ascii=False))
    s.add(snapshot);s.commit();s.refresh(snapshot)
    return {'id':snapshot.id,'unchanged':False,'metrics':metrics,'recommendations':recs,'delta':delta}

@app.get('/api/career/checkins')
def checkin_history(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    rows=list(s.scalars(select(CareerSnapshot).where(CareerSnapshot.user_id==uid).order_by(CareerSnapshot.id.desc()).limit(52)))
    return [{'id':r.id,'created_at':r.created_at,'metrics':json.loads(r.metrics_json),
             'recommendations':json.loads(r.recommendations_json),'explanation':json.loads(r.explanation_json)} for r in rows]

@app.get('/api/career/loop')
def adaptive_loop(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    metrics,recs,explanation=career_metrics(s,uid)
    latest=s.scalar(select(CareerSnapshot).where(CareerSnapshot.user_id==uid).order_by(CareerSnapshot.id.desc()))
    prior=json.loads(latest.metrics_json) if latest else {}
    return {'current':metrics,'since_last_checkin':{k:metrics[k]-prior.get(k,0) for k in metrics},
            'next_actions':recs,'last_checkin':latest.created_at if latest else None,
            'method':'Comparação determinística dos registros do usuário. Mudanças não demonstram causalidade ou aumento de empregabilidade.',
            'explanation':explanation}


# V10: privacy-preserving, review-before-save onboarding from pasted CV text.
class ResumeImportIn(BaseModel):
    text: str = Field(min_length=30, max_length=25000)

class ResumeImportConfirm(BaseModel):
    evidence: list[EvidenceIn] = Field(default_factory=list, max_length=15)
    target_role: str | None = Field(default=None, max_length=120)
    allow_possible_duplicates: bool = False
    populate_master_profile: bool = True
    record_declared_facts: bool = True

SKILL_TERMS = ('python','sql','postgresql','javascript','typescript','react','node.js','fastapi','django','excel','power bi','docker','git','aws','azure','java','c#','html','css','kubernetes','pandas')

def preview_resume_text(text):
    # No model guessing: identify literal skill mentions only, never claim competence.
    import unicodedata
    compact=' '.join(text.split())
    lower=unicodedata.normalize('NFKC',compact).casefold()
    matches=[]
    for term in SKILL_TERMS:
        if re.search(r'(?<![\w])'+re.escape(term)+r'(?![\w])',lower):matches.append(term)
    return {'skill_mentions':matches,'character_count':len(text),
            'caveats':['Menções textuais não comprovam experiência, autoria ou proficiência.',
                       'Revise cada item antes de salvar. O texto original não é armazenado.'],
            'source':'user_pasted_text'}

@app.post('/api/import/resume/file-preview')
async def resume_file_preview(file:UploadFile=File(...),uid:int=Depends(current_user)):
    from resume_ingestion import extract_resume, suggested_sections, MAX_BYTES
    # Stream capped before parsing; do not log or persist raw personal information.
    payload=await file.read(MAX_BYTES+1)
    try:
        extracted=extract_resume(file.filename or '',payload)
    except (ValueError, ImportError) as exc:
        raise HTTPException(422,str(exc))
    except Exception:
        raise HTTPException(422,'Não foi possível extrair texto deste documento')
    preview=preview_resume_text(extracted['text'])
    preview['source']='user_uploaded_file'
    preview['format']=extracted['format']
    preview['sections']=suggested_sections(extracted['text'])
    from resume_journey import suggestions
    preview.update(suggestions(extracted['text']))
    preview['privacy']='Arquivo e texto bruto não são persistidos por este endpoint'
    return preview

@app.post('/api/import/resume/preview')
def resume_preview(p:ResumeImportIn,uid:int=Depends(current_user)):
    from resume_journey import suggestions
    return {**preview_resume_text(p.text), **suggestions(p.text)}

@app.post('/api/import/resume/confirm',status_code=201)
def resume_confirm(p:ResumeImportConfirm,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    # Confirmation is intentionally separate from preview; never auto-persist scraped text.
    seen=set()
    for e in p.evidence:
        key=(e.kind,e.title.strip().casefold())
        if key in seen:raise HTTPException(422,'Evidências duplicadas na importação')
        seen.add(key)
    from resume_journey import normalize
    existing=list(s.scalars(select(Evidence).where(Evidence.user_id==uid)))
    existing_keys={(e.kind,normalize(e.title),normalize(e.description)) for e in existing}
    from resume_similarity import classify, similarity
    # Reject ambiguous matches before writing anything; require an explicit user choice.
    conflicts=[]
    for incoming in p.evidence:
        for old in existing:
            match=classify(incoming,old)
            if match=='possible_duplicate':
                conflicts.append({'incoming_title':incoming.title,'existing_id':old.id,'existing_title':old.title,'reason':match})
    if conflicts and not p.allow_possible_duplicates:
        raise HTTPException(409,{'message':'Possíveis duplicidades: revise antes de confirmar','conflicts':conflicts})
    created=[];skipped=[]
    for e in p.evidence:
        key=(e.kind,normalize(e.title),normalize(e.description))
        if key in existing_keys or any(classify(e,old)=='duplicate' for old in existing):
            skipped.append({'kind':e.kind,'title':e.title,'reason':'already_exists_or_near_exact'});continue
        row=Evidence(user_id=uid,kind=e.kind,title=e.title.strip(),description=e.description,url=e.url,status='DECLARED',verification_note='Importado após confirmação manual; não verificado')
        s.add(row);s.flush();created.append(row.id);existing_keys.add(key)
    if p.target_role is not None:
        profile=s.get(Profile,uid)
        if profile is None:raise HTTPException(409,'Perfil não encontrado')
        profile.target_role=p.target_role
    # Transactionally project confirmed resume evidence into structured profile and declared facts.
    # Only newly created evidence is projected, making repeated imports idempotent.
    projected=[]; fact_ids=[]
    if p.populate_master_profile or p.record_declared_facts:
        for eid in created:
            ev=s.get(Evidence,eid)
            category=ev.kind
            if p.populate_master_profile:
                item=MasterProfileItem(user_id=uid,category=category,title=ev.title,
                    description=ev.description,source_evidence_id=eid)
                s.add(item);s.flush();projected.append(item.id)
            if p.record_declared_facts:
                fact=CareerFact(user_id=uid,subject=ev.title[:180],predicate='descricao_profissional',
                    value=ev.description,source_type='resume_import',source_reference=f'evidence:{eid}',
                    verification='USER_DECLARED',status='ACTIVE')
                s.add(fact);s.flush();fact_ids.append(fact.id)
    audit(s,uid,'resume_import.confirm');s.commit()
    return {'created_ids':created,'count':len(created),'skipped_duplicates':skipped,
        'master_item_ids':projected,'fact_ids':fact_ids,'verification':'DECLARED'}

@app.get('/api/diagnostic/priority-actions')
def diagnostic_priority_actions(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    """Actionable, source-linked gaps; deterministic, not a hiring prediction."""
    profile=s.get(Profile,uid)
    evidence=list(s.scalars(select(Evidence).where(Evidence.user_id==uid)))
    jobs=list(s.scalars(select(Job).where(Job.user_id==uid)))
    actions=[]
    if not profile.target_role.strip():
        actions.append({'priority':1,'action':'Definir cargo-alvo','why':'Falta um objetivo para priorizar requisitos','source':'profile.target_role','next_tab':'dashboard'})
    if not evidence:
        actions.append({'priority':1,'action':'Importar currículo e confirmar evidências','why':'Ainda não existem evidências profissionais declaradas','source':'evidence','next_tab':'import'})
    if not jobs:
        actions.append({'priority':2,'action':'Adicionar vaga real com requisitos','why':'Sem vaga de referência não há comparação específica','source':'jobs','next_tab':'jobs'})
    for job in jobs[:5]:
        requirements=json.loads(job.requirements_json or '[]')
        for req in requirements[:30]:
            refs=[e for e in evidence if req.casefold() in (e.title+' '+e.description).casefold()]
            if not refs:
                actions.append({'priority':2,'action':f'Documentar evidência para: {req[:100]}',
                    'why':f'Requisito informado na vaga {job.title}; nenhuma menção textual encontrada nas evidências cadastradas',
                    'source':f'job:{job.id}','next_tab':'evidence'})
            elif all(e.status=='DECLARED' for e in refs):
                actions.append({'priority':3,'action':f'Fortalecer evidência de: {req[:100]}',
                    'why':'Há menção textual, mas não comprovação independente de competência',
                    'source':f'job:{job.id};evidence:{refs[0].id}','next_tab':'evidence'})
    if not actions:
        actions.append({'priority':3,'action':'Revisar currículo e candidaturas da semana',
            'why':'Nenhuma lacuna textual foi identificada nos dados fornecidos; isso não comprova adequação à vaga',
            'source':'user_data','next_tab':'diagnostic'})
    actions.sort(key=lambda x:x['priority'])
    return {'target_role':profile.target_role,'actions':actions[:5],
        'method':'Regras determinísticas com origem indicada; comparação textual não verifica competência.',
        'hiring_probability':None}

@app.get('/api/journey/first-result')
def journey_first_result(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    """First useful output even before a job is registered; never fabricates fit."""
    profile=s.get(Profile,uid)
    ev=list(s.scalars(select(Evidence).where(Evidence.user_id==uid)))
    jobs=list(s.scalars(select(Job).where(Job.user_id==uid)))
    actions=[]
    if not profile.target_role.strip():actions.append({'title':'Definir cargo-alvo','why':'Sem objetivo não é possível priorizar requisitos','next_tab':'dashboard'})
    if not ev:actions.append({'title':'Importar e confirmar currículo','why':'Precisamos de informações profissionais declaradas','next_tab':'import'})
    if not jobs:actions.append({'title':'Adicionar uma vaga de referência','why':'Requisitos reais tornam as recomendações específicas','next_tab':'jobs'})
    if ev and not any(e.kind in ('experience','project') for e in ev):actions.append({'title':'Documentar experiência ou projeto','why':'Menções de habilidades não demonstram aplicação','next_tab':'evidence'})
    if jobs and not any(json.loads(j.requirements_json or '[]') for j in jobs):actions.append({'title':'Informar requisitos da vaga','why':'Uma vaga sem requisitos não permite comparação','next_tab':'jobs'})
    if not actions:actions.append({'title':'Revisar diagnóstico e escolher uma ação','why':'Compare as evidências declaradas com os requisitos','next_tab':'diagnostic'})
    return {'target_role':profile.target_role,'evidence_count':len(ev),'jobs_count':len(jobs),
            'next_actions':actions[:3],'first_result':'Diagnóstico preliminar com dados declarados',
            'limitations':['Não é uma avaliação de proficiência nem probabilidade de contratação.','A precisão depende dos dados e das vagas informadas.']}

@app.get('/api/diagnostic/readiness')
def diagnostic_readiness(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    profile=s.get(Profile,uid)
    ev=list(s.scalars(select(Evidence).where(Evidence.user_id==uid)))
    jobs=list(s.scalars(select(Job).where(Job.user_id==uid)))
    checks=[{'key':'target','done':bool(profile.target_role.strip()),'why':'Defina o cargo desejado'},
            {'key':'evidence','done':bool(ev),'why':'Cadastre pelo menos uma evidência'},
            {'key':'job','done':bool(jobs),'why':'Cadastre uma vaga de referência'},
            {'key':'job_requirements','done':any(json.loads(j.requirements_json or '[]') for j in jobs),'why':'Informe requisitos de uma vaga'}]
    return {'ready':all(x['done'] for x in checks),'checks':checks,'confidence_note':'Completude de dados, não precisão comprovada ou probabilidade de contratação'}

@app.get('/metrics')
def metrics():
    # Avoid public metrics leaking traffic volume: enable only behind private monitoring network.
    if os.getenv('EXPOSE_METRICS')!='1':raise HTTPException(404)
    return {'service':'job-agent','status':'up'}

static_dir=os.path.join(os.path.dirname(__file__),'web')
app.mount('/assets',StaticFiles(directory=static_dir),name='assets')
@app.get('/',include_in_schema=False)
def home():return FileResponse(os.path.join(static_dir,'index.html'))
@app.get('/billing/success',include_in_schema=False)
def billing_success():return RedirectResponse('/?billing=success')
@app.get('/billing/cancel',include_in_schema=False)
def billing_cancel():return RedirectResponse('/?billing=cancel')
@app.get('/account',include_in_schema=False)
def account_page():return RedirectResponse('/?tab=account')


# Evidence documentation strength: separate from competency or independent verification.
from evidence_strength import evaluate, RUBRIC_VERSION
class EvidenceAssessmentIn(BaseModel):
    scope:str=Field(default='',max_length=2000)
    personal_contribution:str=Field(default='',max_length=2000)
    method:str=Field(default='',max_length=2000)
    result:str=Field(default='',max_length=2000)
    limitations:str=Field(default='',max_length=2000)

@app.post('/api/evidence/{item_id}/assessments',status_code=201)
def assess_evidence(item_id:int,p:EvidenceAssessmentIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    e=owned(s,Evidence,uid,item_id)
    submission=p.model_dump()
    result=evaluate({'url':e.url},submission)
    row=EvidenceAssessment(user_id=uid,evidence_id=e.id,rubric_version=RUBRIC_VERSION,
                           submission_json=json.dumps(submission,ensure_ascii=False),
                           result_json=json.dumps(result,ensure_ascii=False))
    s.add(row);audit(s,uid,'evidence.assessment.create');s.commit();s.refresh(row)
    return {'id':row.id,'evidence_id':e.id,'created_at':row.created_at,'result':result}

@app.get('/api/evidence/{item_id}/assessments')
def list_assessments(item_id:int,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    owned(s,Evidence,uid,item_id)
    rows=s.scalars(select(EvidenceAssessment).where(EvidenceAssessment.user_id==uid,
        EvidenceAssessment.evidence_id==item_id).order_by(EvidenceAssessment.id.desc()).limit(50))
    return [{'id':r.id,'created_at':r.created_at,'submission':json.loads(r.submission_json),
             'result':json.loads(r.result_json)} for r in rows]

@app.get('/api/career/evidence-quality')
def evidence_quality(uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    ev=list(s.scalars(select(Evidence).where(Evidence.user_id==uid)))
    rows=[]
    for e in ev:
        latest=s.scalar(select(EvidenceAssessment).where(EvidenceAssessment.user_id==uid,
            EvidenceAssessment.evidence_id==e.id).order_by(EvidenceAssessment.id.desc()))
        rows.append({'evidence_id':e.id,'title':e.title,'documentation':json.loads(latest.result_json) if latest else None,
                     'assessed_at':latest.created_at if latest else None})
    return {'rubric_version':RUBRIC_VERSION,'items':rows,'disclaimer':'Não avalia proficiência, autenticidade ou chance de contratação.'}


# Technical artifact inventory: accepts user-pasted source files, never executes or fetches URLs.
from artifact_review import review as review_artifacts, VERSION as ARTIFACT_VERSION
class ArtifactFileIn(BaseModel):
    path:str=Field(min_length=1,max_length=240)
    content:str=Field(max_length=120000)
class ArtifactSubmissionIn(BaseModel):
    files:list[ArtifactFileIn]=Field(min_length=1,max_length=30)

@app.post('/api/evidence/{item_id}/artifact-reviews',status_code=201)
def submit_artifact_review(item_id:int,p:ArtifactSubmissionIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    e=owned(s,Evidence,uid,item_id)
    try:result=review_artifacts([f.model_dump() for f in p.files])
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    row=ArtifactReview(user_id=uid,evidence_id=e.id,review_version=ARTIFACT_VERSION,
                       inventory_sha256=result['inventory_sha256'],result_json=json.dumps(result,ensure_ascii=False))
    s.add(row);audit(s,uid,'evidence.artifact_review.create');s.commit();s.refresh(row)
    return {'id':row.id,'evidence_id':e.id,'created_at':row.created_at,'result':result}

@app.get('/api/evidence/{item_id}/artifact-reviews')
def list_artifact_reviews(item_id:int,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    owned(s,Evidence,uid,item_id)
    rows=s.scalars(select(ArtifactReview).where(ArtifactReview.user_id==uid,
        ArtifactReview.evidence_id==item_id).order_by(ArtifactReview.id.desc()).limit(50))
    return [{'id':r.id,'created_at':r.created_at,'result':json.loads(r.result_json)} for r in rows]

# V8: static-only technical review. Never executes submitted code on API workers.
from technical_quality import analyze as analyze_technical_quality
from contribution_review import summarize as summarize_contributions

class CommitSummaryIn(BaseModel):
    sha:str=Field(min_length=7,max_length=64)
    author:str=Field(min_length=1,max_length=120)
    files:list[str]=Field(default_factory=list,max_length=100)

class TechnicalReviewIn(BaseModel):
    files:list[ArtifactFileIn]=Field(min_length=1,max_length=30)
    commits:list[CommitSummaryIn]=Field(default_factory=list,max_length=200)

@app.post('/api/evidence/{item_id}/technical-reviews',status_code=201)
def submit_technical_review(item_id:int,p:TechnicalReviewIn,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    evidence=owned(s,Evidence,uid,item_id)
    try:
        submitted=[f.model_dump() for f in p.files]
        result=analyze_technical_quality(submitted)
        result['contributions']=summarize_contributions([c.model_dump() for c in p.commits])
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    row=ArtifactReview(user_id=uid,evidence_id=evidence.id,review_version=result['version'],
        inventory_sha256=result['inventory_sha256'],result_json=json.dumps(result,ensure_ascii=False))
    s.add(row);audit(s,uid,'evidence.technical_review.create');s.commit();s.refresh(row)
    return {'id':row.id,'evidence_id':evidence.id,'created_at':row.created_at,'result':result}

@app.get('/api/evidence/{item_id}/technical-reviews')
def list_technical_reviews(item_id:int,uid:int=Depends(current_user),s:DBSession=Depends(getdb)):
    owned(s,Evidence,uid,item_id)
    rows=s.scalars(select(ArtifactReview).where(ArtifactReview.user_id==uid,
        ArtifactReview.evidence_id==item_id,ArtifactReview.review_version=='technical-static-v1')
        .order_by(ArtifactReview.id.desc()).limit(50))
    return [{'id':r.id,'created_at':r.created_at,'result':json.loads(r.result_json)} for r in rows]
