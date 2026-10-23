"""Synthetic comparison fixtures. NOT cases from actual users."""
from evidence_strength import evaluate

def test_comparative_synthetic_examples():
    project={'url':'https://example.org/project'}
    thin={'scope':'Fiz um projeto Python'}
    partial={'scope':'Construí uma API para organizar pedidos em um projeto pessoal.',
             'personal_contribution':'Desenhei endpoints, modelei dados e implementei a API sozinho.',
             'method':'Usei FastAPI, testes unitários e revisão de erros no código.'}
    detailed={**partial,'result':'Executei vinte testes locais e registrei os resultados; sem usuários externos.',
              'limitations':'O projeto não foi implantado nem testado sob carga real; autoria não foi auditada.'}
    a,b,c=[evaluate(project,x) for x in (thin,partial,detailed)]
    assert [x['documentation_score'] for x in (a,b,c)]==[0,60,100]
    assert a['documentation_band']=='DOCUMENTATION_THIN'
    assert b['documentation_band']=='DOCUMENTATION_PARTIAL'
    assert c['documentation_band']=='DOCUMENTATION_DETAILED'
    assert all(x['proficiency_score'] is None and not x['authorship_verified'] for x in (a,b,c))

def test_fake_long_text_does_not_claim_verified():
    x=evaluate({'url':'https://example.com'}, {k:'declaração sem prova '*10 for k in ('scope','personal_contribution','method','result','limitations')})
    assert x['documentation_score']==100
    assert x['verification_status']=='NOT_INDEPENDENTLY_VERIFIED'
    assert not x['authorship_verified']

def test_no_url_fetch_and_url_not_scored():
    text={'scope':'Este texto contém detalhes sobre um projeto demonstrativo suficientemente longo.'}
    a=evaluate({'url':'http://127.0.0.1/admin'},text)
    b=evaluate({'url':''},text)
    assert a['documentation_score']==b['documentation_score']
    assert 'URLs não são abertas' in a['caveats'][1]
