"""B5 smoke: guard recovered DB; verify guidance, isolation, actionable tasks."""
import sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_d269b2_files import verify_isolation, request

def main():
 verify_isolation()
 results=[]
 def check(name,ok):
  results.append(bool(ok));print(('PASS' if ok else 'FAIL')+' | '+name,flush=True)
 tokens=[]
 for i in range(2):
  creds={'email':f'b5-{uuid.uuid4().hex[:10]}-{i}@example.com','password':'B5_LocalOnly_2026!'}
  code,_=request('/api/auth/register','POST',creds);check('Register '+str(i+1),code==201)
  code,body=request('/api/auth/login','POST',creds);tokens.append(body.get('access_token'))
  check('Login '+str(i+1),code==200 and bool(tokens[-1]))
 if not all(tokens):return 1
 t1,t2=tokens
 code,job=request('/api/jobs','POST',{'title':'Desenvolvedor Backend','company':'Exemplo SA',
   'description':'Requisitos: Python e SQL para APIs backend em equipe','requirements':['Python','SQL'],'source_url':''},t1)
 jobid=job.get('id');check('Create job',code==201 and bool(jobid))
 code,preview=request('/api/jobs/'+str(jobid)+'/guidance',token=t1)
 check('Guidance for owner',code==200 and preview.get('counts',{}).get('total')==2)
 check('No hiring probability',preview.get('hiring_probability') is None)
 check('Initially undocumented',preview.get('counts',{}).get('not_documented')==2)
 code,_=request('/api/jobs/'+str(jobid)+'/guidance',token=t2)
 check('Other account cannot access',code==404)
 code,ev=request('/api/evidence','POST',{'kind':'project','title':'Projeto Python API','description':'Desenvolvi API em Python com testes','url':''},t1)
 check('Evidence created',code==201)
 code,after=request('/api/jobs/'+str(jobid)+'/guidance',token=t1)
 check('Matching declaration is unverified',code==200 and after.get('counts',{}).get('mentioned_unverified')==1 and after.get('hiring_probability') is None)
 req=(after.get('requirements') or [{}])[0]
 check('Readable next action',bool(req.get('next_action')) and bool(req.get('action_title')))
 code,task=request('/api/tasks','POST',{'title':req['action_title']},t1)
 check('Action saved in weekly plan',code==201)
 print('RESULTADO: '+str(sum(results))+'/'+str(len(results)))
 print('STATUS: '+('PASS' if all(results) else 'FAIL'))
 return 0 if all(results) else 1
if __name__=='__main__':sys.exit(main())
