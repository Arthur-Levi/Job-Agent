"""B4 regression. Uses the guarded DB check already established in B2.5."""
import sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_d269b2_files import verify_isolation,request
from job_ingestion import extract_job_preview

TEXT='''Cargo: Desenvolvedor Backend
Empresa: Empresa Exemplo
Requisitos:
- Python
- SQL
- Git
Responsabilidades:
- Desenvolver APIs internas para o time.
'''
def main():
 verify_isolation()
 checks=[]
 def check(label,ok):
  checks.append(ok);print(('PASS' if ok else 'FAIL')+' | '+label,flush=True)
 local=extract_job_preview(TEXT)
 check('Cargo sugerido',local['title_draft']=='Desenvolvedor Backend')
 check('Empresa sugerida',local['company_draft']=='Empresa Exemplo')
 check('Requisitos extraidos',all(any(k in req for req in local['requirements_draft']) for k in ('Python','SQL','Git')))
 check('Previa nao declara salvamento',local['saved'] is False)
 uid=uuid.uuid4().hex[:10]
 creds={'email':'b4-'+uid+'@example.com','password':'B4_TestOnly_2026!'}
 code,_=request('/api/auth/register','POST',creds);check('Cadastro de teste',code==201)
 code,auth=request('/api/auth/login','POST',creds)
 token=auth.get('access_token');check('Login de teste',code==200 and bool(token))
 if not token:return 1
 code,before=request('/api/jobs',token=token);check('Lista inicial de vagas',code==200 and isinstance(before,list))
 code,draft=request('/api/jobs/text-preview','POST',{'text':TEXT},token)
 check('Previa autenticada',code==200 and draft.get('source')=='user_supplied_text' and draft.get('saved') is False)
 code,unchanged=request('/api/jobs',token=token)
 check('Previa nao persiste vaga',code==200 and unchanged==before)
 code,short=request('/api/jobs/text-preview','POST',{'text':'vaga curta'},token)
 check('Texto curto rejeitado',code==422)
 payload={'title':draft['title_draft'],'company':draft['company_draft'],
 'description':draft['description_draft'],'requirements':draft['requirements_draft'],'source_url':''}
 code,saved=request('/api/jobs','POST',payload,token);check('Confirmacao salva vaga',code==201 and bool(saved.get('id')))
 code,after=request('/api/jobs',token=token)
 check('Vaga e requisitos persistidos',code==200 and any(x['id']==saved.get('id') and 'Python' in x['requirements'] for x in after))
 code,priorities=request('/api/diagnostic/priority-actions',token=token)
 check('Diagnostico continua disponivel',code==200 and isinstance(priorities.get('actions'),list))
 print('RESULTADO: '+str(sum(checks))+'/'+str(len(checks)))
 print('STATUS: '+('PASS' if all(checks) else 'FAIL'))
 return 0 if all(checks) else 1
if __name__=='__main__':sys.exit(main())
