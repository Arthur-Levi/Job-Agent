from test_production import c, register

def test_intelligence_auth_and_isolation():
    assert c.get('/api/intelligence').status_code==401
    a=register('intelligence-alpha@example.com')
    b=register('intelligence-bravo@example.com')
    r=c.post('/api/evidence',headers=a,json={'kind':'project','title':'Python FastAPI','description':'Construí uma API com Python e FastAPI'})
    assert r.status_code==201
    j=c.post('/api/jobs',headers=a,json={'title':'Backend','company':'Acme','description':'Desenvolvimento de API Python','requirements':['Python','Docker']})
    assert j.status_code==201
    own=c.get('/api/intelligence',headers=a).json()
    other=c.get('/api/intelligence',headers=b).json()
    assert own['quality']['coverage']['total_requirements']==2
    assert other['quality']['coverage']['total_requirements']==0
    assert other['opportunities']==[]
    assert own['opportunities'][0]['requirements'][0]['candidate_evidence'][0]['evidence_id']==r.json()['id']
