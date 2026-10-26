#!/usr/bin/env python3
"""D2.6.9-A HTTP regression. ONLY run against isolated jobagent_ux database."""
import json
import os
import re
import subprocess
import sys
from urllib.parse import urlsplit
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8001"
TAG = uuid.uuid4().hex[:12]
PASSES = []
def record(name, ok, info=""):
    PASSES.append(bool(ok))
    print(("PASS" if ok else "FAIL") + " | " + name + ((" | "+info) if info else ""), flush=True)
    return bool(ok)
def send(path, method="GET", payload=None, token=None):
    headers={"Accept":"application/json"}
    if token:headers["Authorization"]="Bearer "+token
    body=None if payload is None else json.dumps(payload).encode("utf-8")
    if body is not None:headers["Content-Type"]="application/json"
    req=Request(BASE+path,data=body,headers=headers,method=method)
    try:
        with urlopen(req,timeout=20) as resp:
            code=resp.status
            raw=resp.read()
    except HTTPError as err:
        code=err.code
        raw=err.read()
    except (URLError,TimeoutError) as err:
        return 0,{"error":type(err).__name__}
    try: parsed=json.loads(raw)
    except (ValueError,UnicodeDecodeError): parsed={}
    return code,parsed

def main():
    # The API may be running in a different shell environment: this check must run
    # in the Codespaces terminal with the actual API PID checked separately.
    try:
        listeners=subprocess.check_output(["ss","-ltnp","sport = :8001"],text=True)
        pids=re.findall(r"pid=(\\d+)",listeners)
        if len(set(pids))!=1:raise RuntimeError("PID da API nao identificado")
        environ=open("/proc/"+pids[0]+"/environ","rb").read().split(b"\\0")
        env=dict(item.decode("utf-8","replace").split("=",1) for item in environ if b"=" in item)
        db=urlsplit(env.get("DATABASE_URL",""))
        assert db.hostname in ("127.0.0.1","localhost") and db.port==55433 and db.path=="/jobagent_ux", "API nao usa DB descartavel 55433/jobagent_ux"
        print("PASS | Segurança: processo da porta 8001 aponta para o banco isolado")
    except Exception as exc:
        print("FAIL | Segurança: nao comprovado banco isolado no PID da porta 8001:",str(exc))
        return 2
    for path in ["/health/live","/health/ready","/","/assets/style.css","/assets/app.js"]:
        status,_=send(path)
        record("HTTP "+path,status==200,str(status))
    if not all(PASSES):return 1
    pwd="UxCase!2026_SecretPass"
    a={"email":f"ux-a-{TAG}@example.com","password":pwd}
    b={"email":f"ux-b-{TAG}@example.com","password":pwd}
    for name,user in [("Cadastro A",a),("Cadastro B",b)]:
        code,_=send("/api/auth/register","POST",user)
        record(name,code==201,str(code))
    tokens=[]
    for name,user in [("Login A",a),("Login B",b)]:
        code,data=send("/api/auth/login","POST",user)
        ok=code==200 and bool(data.get("access_token"))
        record(name,ok,str(code))
        tokens.append(data.get("access_token"))
    if not all(tokens):
        print("STATUS: FAIL — sem tokens, encerrando sem executar mais gravações")
        return 1
    ta,tb=tokens
    for name,user,token in [("Identidade A",a,ta),("Identidade B",b,tb)]:
        code,data=send("/api/me",token=token)
        record(name,code==200 and data.get("email")==user["email"],str(code))
    code,_=send("/api/me")
    record("Proteção sem token",code==401,str(code))
    cv_text=("Profissional fictício com experiência acadêmica em Python, SQL, PostgreSQL, FastAPI, "
             "Git, Docker e documentação de projetos. Desenvolveu APIs REST e testes automatizados. "
             "Implementou endpoints de demonstração, organizou dados e documentou resultados reais "
             "de projeto acadêmico simulado. Busca vaga de desenvolvimento backend junior.")
    code,data=send("/api/import/resume/preview","POST",{"text":cv_text},ta)
    record("Preview sem gravar",code==200 and isinstance(data,dict),str(code))
    code,data=send("/api/import/resume/confirm","POST",{"target_role":"Backend Junior","evidence":[{"kind":"project","title":"Projeto QA "+TAG,"description":"Projeto fictício de testes API com Python e PostgreSQL; sem atividade profissional real.","url":""}]},ta)
    record("Confirmação importação",code in (200,201),str(code))
    code,ev_a=send("/api/evidence",token=ta)
    record("Evidências A",code==200 and isinstance(ev_a,list) and any(TAG in x.get("title","") for x in ev_a),str(code))
    code,ev_b=send("/api/evidence",token=tb)
    record("Isolamento entre usuários",code==200 and isinstance(ev_b,list) and not any(TAG in x.get("title","") for x in ev_b),str(code))
    for name,path in [("Diagnóstico","/api/intelligence"),("Ações prioritárias","/api/diagnostic/priority-actions"),("Vagas","/api/jobs"),("Candidaturas","/api/applications"),("Tarefas","/api/tasks"),("Premium","/api/billing/status")]:
        code,_=send(path,token=ta)
        record(name,code==200,str(code))
    passed=sum(PASSES)
    print(f"RESULTADO: {passed}/{len(PASSES)}")
    print("STATUS:", "PASS" if passed==len(PASSES) else "FAIL")
    return 0 if passed==len(PASSES) else 1

if __name__=="__main__":
    sys.exit(main())
