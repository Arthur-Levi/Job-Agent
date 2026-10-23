import uuid
from test_production import c,register

def test_assessment_history_and_cross_tenant_access():
    a=register('strength-a-'+uuid.uuid4().hex[:10]+'@example.org')
    b=register('strength-b-'+uuid.uuid4().hex[:10]+'@example.org')
    item=c.post('/api/evidence',headers=a,json={'kind':'project','title':'API com Python','description':'API com endpoints para pedidos'}).json()
    payload={'scope':'Desenvolvi um serviço local para gerenciar pedidos e validar entradas.',
             'personal_contribution':'Implementei pessoalmente as rotas e a estrutura de dados da aplicação.'}
    assert c.post(f"/api/evidence/{item['id']}/assessments",headers=b,json=payload).status_code==404
    first=c.post(f"/api/evidence/{item['id']}/assessments",headers=a,json=payload)
    assert first.status_code==201,first.text
    assert first.json()['result']['documentation_score']==40
    second=c.post(f"/api/evidence/{item['id']}/assessments",headers=a,json={**payload,'method':'Implementei testes automatizados locais e tratei erros de validação.'})
    assert second.status_code==201
    history=c.get(f"/api/evidence/{item['id']}/assessments",headers=a).json()
    assert len(history)==2 and history[0]['result']['documentation_score']==60
    assert c.get(f"/api/evidence/{item['id']}/assessments",headers=b).status_code==404
    assert c.get('/api/career/evidence-quality',headers=b).json()['items']==[]
    export=c.get('/api/account/export',headers=a).json()
    assert len(export['evidence_assessments'])==2
    assert c.delete(f"/api/evidence/{item['id']}",headers=a).status_code==200
    assert c.get('/api/career/evidence-quality',headers=a).json()['items']==[]
