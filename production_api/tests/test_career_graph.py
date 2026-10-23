from test_production import c,register

def test_graph_isolation_snapshot_and_outcomes():
    a=register('graph-owner@example.com');b=register('graph-other@example.com')
    e=c.post('/api/evidence',headers=a,json={'kind':'project','title':'API Python','description':'Implementei uma API REST com Python e testes'}).json()
    j=c.post('/api/jobs',headers=a,json={'title':'Backend','company':'Empresa','description':'Vaga Python backend','requirements':['Python','Docker']}).json()
    assert c.get('/api/career/graph').status_code==401
    assert c.get('/api/career/graph',headers=b).json()['evidence']==[]
    assert c.post('/api/career/graph/links',headers=b,json={'evidence_id':e['id'],'requirement':'Python'}).status_code==404
    r=c.post('/api/career/graph/links',headers=a,json={'evidence_id':e['id'],'requirement':'Python','rationale':'Projeto usa Python'})
    assert r.status_code==201,r.text
    link=r.json()['id']
    assert c.post('/api/career/graph/links',headers=a,json={'evidence_id':e['id'],'requirement':'Python'}).status_code==409
    assert c.delete(f'/api/career/graph/links/{link}',headers=b).status_code==404
    first=c.post('/api/career/checkins',headers=a);assert first.status_code==201,first.text
    assert first.json()['unchanged'] is False
    assert c.post('/api/career/checkins',headers=a).json()['unchanged'] is True
    assert c.get('/api/career/checkins',headers=b).json()==[]
    assert c.post('/api/career/outcomes',headers=b,json={'kind':'interview','description':'Entrevista','job_id':j['id']}).status_code==404
    assert c.post('/api/career/outcomes',headers=a,json={'kind':'rejection','description':'Não avançou na etapa','job_id':j['id']}).status_code==201
    loop=c.get('/api/career/loop',headers=a).json()
    assert loop['next_actions'][0]['action'].startswith('Revisar o feedback')
    assert c.post('/api/career/checkins',headers=a).json()['unchanged'] is False
    assert len(c.get('/api/career/checkins',headers=a).json())==2
    export=c.get('/api/account/export',headers=a).json()
    assert len(export['evidence_links'])==1 and len(export['career_snapshots'])==2 and len(export['career_outcomes'])==1
    assert c.delete(f'/api/career/graph/links/{link}',headers=a).status_code==200
    assert c.get('/api/career/graph',headers=a).json()['links']==[]

def test_graph_requires_valid_payload():
    a=register('graph-invalid@example.com')
    assert c.post('/api/career/outcomes',headers=a,json={'kind':'hired-guaranteed','description':'Fake'}).status_code==422
    assert c.post('/api/career/graph/links',headers=a,json={'evidence_id':999999,'requirement':'Python'}).status_code==404
