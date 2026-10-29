#!/usr/bin/env python3
"""Live isolation/security smoke test. Operates ONLY against explicitly confirmed disposable loopback API.
Create two ephemeral accounts and clean up through account deletion. No migrations, no DB commands, no production endpoints.
Run: JOB_AGENT_DISPOSABLE=YES_I_CONFIRM_DISPOSABLE JOB_AGENT_URL=http://127.0.0.1:8001 python tests/verify_prebeta_live_isolation.py
"""
import os, json, secrets, sys
from urllib.parse import urlparse
import httpx

url=os.getenv("JOB_AGENT_URL","").rstrip("/")
parsed=urlparse(url)
if os.getenv("JOB_AGENT_DISPOSABLE")!="YES_I_CONFIRM_DISPOSABLE" or parsed.scheme!="http" or parsed.hostname not in ("127.0.0.1","localhost") or parsed.port!=8001 or parsed.path not in ("","/"):
    sys.exit("ABORT: explicit disposable confirmation and http://127.0.0.1:8001 required")
if not url.endswith(":8001"):
    sys.exit("ABORT: exact port 8001 required")

client=httpx.Client(base_url=url,timeout=12,follow_redirects=False)
password="Q22-Discard-"+secrets.token_urlsafe(24)
uids=[f"q22-{secrets.token_hex(9)}@example.invalid" for _ in range(2)]
tokens=[]
created=[]
passed=0
def req(method,path,tok=None,data=None):
    h={"Authorization":"Bearer "+tok} if tok else {}
    return client.request(method,"/api"+path,headers=h,json=data)
def expect(method,path,tok=None,data=None,status=200):
    global passed
    r=req(method,path,tok,data)
    if r.status_code!=status:
        raise AssertionError(f"{method} {path}: expected {status}, got {r.status_code}: {r.text[:220]}")
    passed+=1
    return r.json()
def deny(method,path,tok,data=None):
    global passed
    r=req(method,path,tok,data)
    if r.status_code not in (401,403,404):
        raise AssertionError(f"UNAUTHORIZED ACCESS: {method} {path}: {r.status_code} {r.text[:220]}")
    passed+=1
try:
    ready=client.get("/health/ready")
    if ready.status_code!=200:
        sys.exit("ABORT: disposable API not ready (health/ready != 200)")
    for email in uids:
        expect("POST","/auth/register",data={"email":email,"password":password},status=201)
        tokens.append(expect("POST","/auth/login",data={"email":email,"password":password})["access_token"])
        created.append(email)
    A,B=tokens
    deny("GET","/me",None)
    ea=expect("POST","/evidence",A,{"kind":"project","title":"Projeto fictício de A","description":"Experimento descartável com evidência fictícia"},201)["id"]
    ja=expect("POST","/jobs",A,{"title":"Analista fictício","company":"Empresa fictícia","description":"Uma vaga fictícia de testes de isolamento","requirements":["SQL"]},201)["id"]
    ta=expect("POST","/tasks",A,{"title":"Tarefa descartável de A"},201)["id"]
    aa=expect("POST","/applications",A,{"job_id":ja,"status":"saved","notes":"Somente de A"},201)["id"]
    ma=expect("POST","/master-profile/items",A,{"category":"project","title":"Projeto teste A"},201)["id"]
    fa=expect("POST","/fact-ledger",A,{"subject":"Projeto A","predicate":"uses","value":"SQL","source_type":"user_statement"},201)["id"]
    # Read isolation and export.
    for path in ("/evidence","/jobs","/tasks","/applications","/master-profile","/fact-ledger","/account/export"):
        response=expect("GET",path,B)
        serialized=json.dumps(response,ensure_ascii=False)
        for forbidden in ("Projeto fictício de A","Tarefa descartável de A","Empresa fictícia","Projeto teste A","Projeto A","Somente de A"):
            if forbidden in serialized:raise AssertionError(f"CROSS ACCOUNT LEAK: {path} contains {forbidden}")
    # Ownership checks for mutated records.
    ev={"kind":"project","title":"Alteração de B","description":"Alteração indevida testada com dados fictícios"}
    for method,path,data in (
        ("PUT",f"/evidence/{ea}",ev),("DELETE",f"/evidence/{ea}",None),
        ("DELETE",f"/jobs/{ja}",None),
        ("PATCH",f"/tasks/{ta}",{"done":True}),("DELETE",f"/tasks/{ta}",None),
        ("PUT",f"/applications/{aa}",{"job_id":ja,"status":"applied","notes":"B"}), 
        ("PUT",f"/master-profile/items/{ma}",{"category":"project","title":"Mudança indevida"}),
        ("DELETE",f"/master-profile/items/{ma}",None),
        ("POST",f"/fact-ledger/{fa}/correct",{"value":"Modificado","reason":"Tentativa de outro usuário"})):
        deny(method,path,B,data)
    # B cannot register a new application for a job owned by A, or a fact referring to A's evidence.
    deny("POST","/applications",B,{"job_id":ja,"status":"saved","notes":"Teste"})
    deny("POST","/fact-ledger",B,{"subject":"Outro","predicate":"uses","value":"SQL","source_type":"evidence","source_reference":str(ea)})
    # Premium endpoints are separately tested after enabling Stripe test-mode entitlement.\n    # A non-premium account may receive 402 before ownership is checked; treating that\n    # as proof of cross-account isolation would produce a false-positive.\n    # Logout invalidates session.
    expect("POST","/auth/logout",A)
    deny("GET","/me",A)
    # Password change invalidates all sessions for B.
    new_password="Q22-New-"+secrets.token_urlsafe(22)
    expect("POST","/auth/change-password",B,{"current_password":password,"new_password":new_password})
    deny("GET","/me",B)
    B2=expect("POST","/auth/login",data={"email":uids[1],"password":new_password})["access_token"]
    expect("POST","/account/delete",B2,{"password":new_password})
    created.remove(uids[1])
    A2=expect("POST","/auth/login",data={"email":uids[0],"password":password})["access_token"]
    export=expect("GET","/account/export",A2)
    assert export["user"]["email"]==uids[0]
    expect("POST","/account/delete",A2,{"password":password})
    created.remove(uids[0])
    print(f"PASS: {passed} live API status checks; isolation, sessions, export, deletion on ephemeral accounts")
except Exception as e:
    print("FAIL:",str(e),file=sys.stderr)
    sys.exit(1)
finally:
    if created:
        print("WARNING: one or more ephemeral accounts may remain after failure; do not run bulk deletion.",file=sys.stderr)
        print("Created ephemeral emails:",", ".join(created),file=sys.stderr)
    client.close()
