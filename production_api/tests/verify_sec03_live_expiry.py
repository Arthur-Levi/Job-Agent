#!/usr/bin/env python3
"""SEC-03 real token expiry. Run ONLY with disposable local API + matching disposable DB.
Updates expires_at for ONE freshly created test session, and deletes ONE test account.
Never run against another DB or port.
"""
import hashlib, os, secrets, sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

api=os.getenv("JOB_AGENT_URL","").rstrip("/")
u=urlparse(api);raw=os.getenv("DATABASE_URL","")
if os.getenv("JOB_AGENT_DISPOSABLE")!="YES_I_CONFIRM_DISPOSABLE" or api!="http://127.0.0.1:8001":
    sys.exit("ABORT: explicit disposable API http://127.0.0.1:8001 required")
if not raw:sys.exit("ABORT: DATABASE_URL required")
db=make_url(raw)
if (db.drivername,db.username,db.host,db.port,db.database)!=("postgresql+psycopg","ux_test","127.0.0.1",55433,"jobagent_ux"):
    sys.exit("ABORT: only jobagent_ux disposable PostgreSQL at 127.0.0.1:55433 allowed")
engine=create_engine(db,connect_args={"connect_timeout":5})
with engine.connect() as con:
    ident=con.execute(text("select current_database(),current_user")).one()
    assert ident==("jobagent_ux","ux_test"),"ABORT: database identity mismatch"
client=httpx.Client(base_url=api,timeout=15,follow_redirects=False)
email="sec03-"+secrets.token_hex(10)+"@example.invalid"
password="Sec03-"+secrets.token_urlsafe(24)
token=None;created=False;passes=0
def request(method,path,token=None,data=None):
    headers={"Authorization":"Bearer "+token} if token else {}
    return client.request(method,"/api"+path,json=data,headers=headers)
def check(response,status,step):
    global passes
    if response.status_code!=status:
        raise AssertionError(f"{step}: expected {status}, got {response.status_code}; body {response.text[:180]}")
    passes+=1
try:
    check(client.get("/health/ready"),200,"API ready")
    check(request("POST","/auth/register",data={"email":email,"password":password}),201,"register")
    created=True
    login=request("POST","/auth/login",data={"email":email,"password":password})
    check(login,200,"login")
    token=login.json()["access_token"]
    check(request("GET","/me",token),200,"valid token")
    token_hash=hashlib.sha256(token.encode()).hexdigest()
    with engine.begin() as con:
        result=con.execute(text("UPDATE sessions SET expires_at=:expired WHERE token_hash=:hash"),{"expired":datetime.now(timezone.utc)-timedelta(minutes=1),"hash":token_hash})
        if result.rowcount!=1:raise AssertionError("EXPIRED SESSION NOT FOUND, stop (schema may differ)")
    check(request("GET","/me",token),401,"expired token rejected")
    check(request("GET","/account/export",token),401,"expired token export rejected")
    fresh=request("POST","/auth/login",data={"email":email,"password":password})
    check(fresh,200,"relogin")
    fresh_token=fresh.json()["access_token"]
    check(request("POST","/auth/logout",fresh_token),200,"logout")
    check(request("GET","/me",fresh_token),401,"revoked token rejected")
    recovery=request("POST","/auth/login",data={"email":email,"password":password})
    check(recovery,200,"cleanup login")
    check(request("POST","/account/delete",recovery.json()["access_token"],{"password":password}),200,"cleanup delete")
    created=False
    print(f"PASS: {passes}/{passes} SEC-03 live checks; expiry and revocation; disposable account deleted")
except Exception as exc:
    print("FAIL:",type(exc).__name__,str(exc),file=sys.stderr)
    if created:print("WARNING: ephemeral account may remain:",email,file=sys.stderr)
    sys.exit(1)
finally:
    client.close();engine.dispose()
