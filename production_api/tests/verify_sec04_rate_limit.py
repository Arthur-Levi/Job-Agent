#!/usr/bin/env python3
"""SEC-04 bounded abuse test: disposable, separate API process only.
Start *dedicated* uvicorn on port 8002 pointed at jobagent_ux.
One-shot MAX 11 login requests, no accounts created, no DB mutation.
"""
import os, sys, time
from urllib.parse import urlparse
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url=os.environ.get("JOB_AGENT_URL","").rstrip("/")
database=os.environ.get("DATABASE_URL","")
if (os.environ.get("JOB_AGENT_DISPOSABLE")!="YES_I_CONFIRM_DISPOSABLE"
    or url!="http://127.0.0.1:8002" or not database):
    sys.exit("ABORT: disposable confirmation, dedicated localhost:8002 and DATABASE_URL required")
db=make_url(database)
assert (db.drivername,db.username,db.host,db.port,db.database)==("postgresql+psycopg","ux_test","127.0.0.1",55433,"jobagent_ux"), "ABORT wrong database"
engine=create_engine(db,connect_args={"connect_timeout":5})
with engine.connect() as connection:
    assert connection.execute(text("SELECT current_database(),current_user")).one()==("jobagent_ux","ux_test")
engine.dispose()
results=[]
client=httpx.Client(base_url=url,timeout=20,follow_redirects=False)
try:
    ready=client.get("/health/ready")
    assert ready.status_code==200, f"API not ready: {ready.status_code}"
    for n in range(11):
        r=client.post("/api/auth/login",json={"email":"sec04-does-not-exist@example.invalid","password":"Sec04-incorrect-credential-123"})
        results.append(r.status_code)
        if n<10 and r.status_code!=401:
            raise AssertionError(f"request {n+1} should be 401, got {r.status_code}; dedicated API may have preexisting traffic")
        if n==10:
            assert r.status_code==429, f"request 11 expected 429 got {r.status_code}"
            assert r.headers.get("Retry-After")=="60", "429 missing expected Retry-After:60"
        assert "traceback" not in r.text.lower() and "password_hash" not in r.text.lower(),"Internal details leaked"
    print("PASS: 10 invalid-login attempts rejected 401; attempt 11 throttled 429 + Retry-After=60")
    print("PASS: no stack traces or password hashes exposed in error bodies")
    print("PASS: strictly bounded 11 requests against disposable isolated API at 127.0.0.1:8002")
finally:
    client.close()
