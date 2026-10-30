#!/usr/bin/env python3
"""SEC-04 account enumeration smoke, isolated localhost API at port 8003.
One ephemeral account. Detects duplicate registration disclosure. Never uses real emails.
Runs max 6 auth calls. Does not attempt password guessing.
"""
import os, sys, secrets
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
api=os.environ.get("JOB_AGENT_URL","")
db_raw=os.environ.get("DATABASE_URL","")
if os.environ.get("JOB_AGENT_DISPOSABLE")!="YES_I_CONFIRM_DISPOSABLE" or api!="http://127.0.0.1:8003" or not db_raw:
    sys.exit("ABORT: require disposable confirmation, localhost port 8003 and DATABASE_URL")
db=make_url(db_raw)
if (db.drivername,db.username,db.host,db.port,db.database)!=("postgresql+psycopg","ux_test","127.0.0.1",55433,"jobagent_ux"):
    sys.exit("ABORT: wrong DB target")
engine=create_engine(db,connect_args={"connect_timeout":5})
with engine.connect() as c:
    assert tuple(c.execute(text("SELECT current_database(),current_user")).one())==("jobagent_ux","ux_test")
engine.dispose()
email="sec04-"+secrets.token_hex(10)+"@example.invalid"
unknown="sec04-unknown-"+secrets.token_hex(10)+"@example.invalid"
password="Sec04-"+secrets.token_urlsafe(22)
client=httpx.Client(base_url=api,timeout=20,follow_redirects=False)
created=False
try:
    assert client.get("/health/ready").status_code==200
    initial=client.post("/api/auth/register",json={"email":email,"password":password})
    assert initial.status_code==201, f"register failed: {initial.status_code}"
    created=True
    duplicate=client.post("/api/auth/register",json={"email":email,"password":password})
    login_existing=client.post("/api/auth/login",json={"email":email,"password":"Wrong-Password-123456"})
    login_unknown=client.post("/api/auth/login",json={"email":unknown,"password":"Wrong-Password-123456"})
    assert login_existing.status_code==login_unknown.status_code==401
    assert login_existing.json()==login_unknown.json(), "FAIL: login enumerates existing accounts"
    print("PASS: login returns indistinguishable 401 body for existing/unknown account")
    # Explicitly identify rather than hide the confirmed registration leak.
    if duplicate.status_code==409 and "cadastrad" in duplicate.text.lower():
        print("FAIL (expected before remediation): register reveals existing account via HTTP 409")
        sys.exit(2)
    assert duplicate.status_code==initial.status_code and duplicate.json()==initial.json(), (
        "FAIL: duplicate registration response differs from new registration"
    )
    print("PASS: registration hides existence of account in both status and body")
finally:
    if created:
        login=client.post("/api/auth/login",json={"email":email,"password":password})
        if login.status_code==200:
            t=login.json()["access_token"]
            delete=client.post("/api/account/delete",headers={"Authorization":"Bearer "+t},json={"password":password})
            print("CLEANUP:", "ephemeral account deleted" if delete.status_code==200 else f"delete failed HTTP {delete.status_code}")
        else:print("WARNING: cleanup login failed; ephemeral account may remain",file=sys.stderr)
    client.close()
