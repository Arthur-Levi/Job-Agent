#!/usr/bin/env python3
"""SEC-04 shared Redis throttle acceptance, two disposable API instances.
Runs exactly 11 invalid logins, alternating between ports 8004 and 8005.
Both must target the same disposable PostgreSQL and Redis; no real accounts.
"""
import os,sys
import httpx
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
if os.getenv('JOB_AGENT_DISPOSABLE')!='YES_I_CONFIRM_DISPOSABLE':
    sys.exit('ABORT: disposable confirmation required')
dbraw=os.getenv('DATABASE_URL','')
if not dbraw:sys.exit('ABORT: DATABASE_URL missing')
db=make_url(dbraw)
assert (db.drivername,db.username,db.host,db.port,db.database)==('postgresql+psycopg','ux_test','127.0.0.1',55433,'jobagent_ux'),'ABORT: wrong db'
engine=create_engine(db,connect_args={'connect_timeout':5})
with engine.connect() as c:assert tuple(c.execute(text('SELECT current_database(), current_user')).one())==('jobagent_ux','ux_test')
engine.dispose()
redis_url=os.getenv('RATE_LIMIT_REDIS_URL','')
assert redis_url in ('redis://127.0.0.1:56379/15','redis://localhost:56379/15'),'ABORT: only isolated Redis 56379 db 15 supported'
from redis import Redis
r=Redis.from_url(redis_url,socket_connect_timeout=2,socket_timeout=2)
assert r.ping()
urls=['http://127.0.0.1:8004','http://127.0.0.1:8005']
with httpx.Client(timeout=10,follow_redirects=False) as client:
    for url in urls:assert client.get(url+'/health/ready').status_code==200,'API not ready: '+url
    statuses=[]
    for i in range(11):
        url=urls[i%2]
        resp=client.post(url+'/api/auth/login',json={'email':'sec04-not-registered@example.invalid','password':'Sec04-invalid-password-1234567'})
        statuses.append(resp.status_code)
        if i<10:assert resp.status_code==401,f'request {i+1} on {url} expected 401 got {resp.status_code}'
        else:
            assert resp.status_code==429,f'request 11 on {url} expected 429 got {resp.status_code}'
            assert 1<=int(resp.headers.get('Retry-After','0'))<=60,'missing valid Retry-After'
    print('PASS: two independent API processes share a Redis limit: 10 x 401 + 1 x 429')
    print('PASS: 429 returned with valid Retry-After; no real users created')
    print('PASS: exactly 11 bounded requests against 127.0.0.1:8004/8005')
