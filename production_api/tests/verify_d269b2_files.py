#!/usr/bin/env python3
"""B2.5: PDF/DOCX/TXT import smoke test. Isolated Codespaces DB ONLY."""
import io, json, re, subprocess, sys, uuid
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE='http://127.0.0.1:8001'
checks=[]
def check(name, passed, detail=''):
    checks.append(passed)
    print(('PASS' if passed else 'FAIL')+' | '+name+(' | '+detail if detail else ''),flush=True)

def verify_isolation():
    try:
        output=subprocess.check_output(['ss','-ltnp','sport = :8001'],text=True)
        pids=set(re.findall(r'pid=(\d+)',output))
        if len(pids)!=1:raise RuntimeError('Nao foi possivel identificar um unico processo da porta 8001')
        raw=open('/proc/'+pids.pop()+'/environ','rb').read()
        env=dict(v.decode('utf-8','replace').split('=',1) for v in raw.split(b'\0') if b'=' in v)
        url=urlsplit(env.get('DATABASE_URL',''))
        if not (url.hostname in ('127.0.0.1','localhost') and url.port==55433 and url.path=='/jobagent_ux'):
            raise RuntimeError('A API nao aponta para jobagent_ux:55433')
        print('PASS | Guard de seguranca: API aponta para banco descartavel',flush=True)
    except Exception as e:
        print('FAIL | Guard de seguranca: '+str(e),flush=True)
        sys.exit(2)

def request(path,method='GET',data=None,token=None,filename=None):
    headers={'Accept':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    if filename is not None:
        boundary='JobAgentBoundaryForLocalTests'
        headers['Content-Type']='multipart/form-data; boundary='+boundary
        body=(('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="'+filename+'"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
              +data+b'\r\n--'+boundary.encode()+b'--\r\n')
    elif data is not None:
        headers['Content-Type']='application/json'
        body=json.dumps(data).encode()
    else:body=None
    try:
        with urlopen(Request(BASE+path,data=body,headers=headers,method=method),timeout=25) as resp:
            code=resp.status;content=resp.read()
    except HTTPError as err:code=err.code;content=err.read()
    except URLError as err:return 0,{'error':type(err).__name__}
    try:return code,json.loads(content)
    except (ValueError,UnicodeDecodeError):return code,{}

def fixtures():
    from docx import Document
    from pypdf import PdfWriter
    from reportlab.pdfgen import canvas
    text=('Curriculo de teste ficticio. Experiencia de projeto educacional com Python, SQL e FastAPI. '
          'Realizou testes com PostgreSQL, Git e Docker. Desenvolveu um demonstrador de APIs. ')
    out={'txt':text.encode('utf-8')}
    doc=Document();doc.add_paragraph(text);buff=io.BytesIO();doc.save(buff);out['docx']=buff.getvalue()
    pdf=io.BytesIO();page=canvas.Canvas(pdf);page.drawString(40,780,text[:110]);page.save();out['pdf']=pdf.getvalue()
    return out

def main():
    verify_isolation()
    code,_=request('/health/ready');check('Readiness',code==200,str(code))
    tag=uuid.uuid4().hex[:10];creds={'email':f'b25-{tag}@example.com','password':'B25_OnlyForTesting!2026'}
    code,_=request('/api/auth/register','POST',creds);check('Cadastro ficticio',code==201,str(code))
    code,body=request('/api/auth/login','POST',creds)
    token=body.get('access_token')
    check('Login ficticio',code==200 and bool(token),str(code))
    if not token:return 1
    code,initial=request('/api/evidence',token=token)
    before=len(initial) if isinstance(initial,list) else -1
    check('Evidencias iniciais',code==200 and before>=0,str(code))
    try:files=fixtures()
    except ImportError as exc:
        print('FAIL | Dependencia ausente para fixtures: '+str(exc))
        return 1
    for ext,payload in files.items():
        code,data=request('/api/import/resume/file-preview','POST',payload,token,f'curriculo-teste.{ext}')
        ok=code==200 and data.get('format')==ext and data.get('source')=='user_uploaded_file' and bool(data.get('skill_mentions'))
        check('Preview '+ext.upper(),ok,str(code))
    code,data=request('/api/import/resume/file-preview','POST',b'conteudo invalido de teste',token,'invalido.pdf')
    check('PDF invalido rejeitado',code==422,str(code))
    code,data=request('/api/import/resume/file-preview','POST',b'x'*2_000_001,token,'excesso.txt')
    check('Arquivo acima de 2MB rejeitado',code==422,str(code))
    code,after=request('/api/evidence',token=token)
    check('Preview nao grava evidencias',code==200 and isinstance(after,list) and len(after)==before,str(code))
    passed=sum(checks)
    print('RESULTADO: '+str(passed)+'/'+str(len(checks)))
    print('STATUS: '+('PASS' if passed==len(checks) else 'FAIL'))
    return 0 if passed==len(checks) else 1
if __name__=='__main__':sys.exit(main())
