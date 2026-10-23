"""Explainable career intelligence: deterministic, tenant-scoped inputs; no hiring predictions.

Every match is a *candidate* based on lexical evidence, not a verified skill.
"""
import re, unicodedata
from collections import Counter

STOP={'de','da','do','dos','das','e','em','para','com','ou','um','uma','the','and','of','for','a','an','experience','experiencia','conhecimento','knowledge','familiaridade','dominio','habilidade','skills','skill','uso','using','utilizacao','experiencia','pratica'}
ALIASES={
 'postgres':['postgresql','postgres'], 'postgresql':['postgresql','postgres'],
 'javascript':['javascript','js'], 'typescript':['typescript','ts'],
 'nodejs':['nodejs','node.js'], 'react':['react','reactjs'],
 'python':['python'], 'sql':['sql'], 'powerbi':['powerbi','power bi'],
 'fastapi':['fastapi'], 'docker':['docker'], 'git':['git'],
 'aws':['aws','amazon web services'], 'excel':['excel'],
 'ci/cd':['ci/cd','continuous integration','integracao continua'],
}
def normalize(value):
    value=unicodedata.normalize('NFKD',str(value or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'\s+',' ',value).strip()

def tokens(value):
    return [t for t in re.findall(r'[a-z0-9+#.]+',normalize(value)) if t not in STOP and len(t)>1]

def lexical_support(requirement,evidence):
    """Conservative candidate retrieval, never a verification decision."""
    req=normalize(requirement)
    if not req:return None
    body=normalize(' '.join((evidence['title'],evidence['description'])))
    key=re.sub(r'[^a-z0-9]','',req)
    aliases=ALIASES.get(key)
    if aliases:
        if any(re.search(r'(?<![a-z0-9])'+re.escape(alias)+r'(?![a-z0-9])',body) for alias in aliases):
            return {'basis':'explicit_term','matched_terms':[req]}
        return None
    required=set(tokens(req))
    if not required:return None
    observed=set(tokens(body))
    if required.issubset(observed):return {'basis':'all_requirement_terms','matched_terms':sorted(required)}
    return None

def analyze(profile,evidence,jobs,applications=(),tasks=()):
    """Pure engine. Inputs must already be scoped to authenticated user by caller."""
    reqs={};job_views=[]
    for job in jobs:
        requirements=job['requirements'][:40]
        rows=[]
        for raw in requirements:
            req=str(raw).strip()
            if not req:continue
            norm=normalize(req)
            if norm not in reqs:reqs[norm]={'requirement':req,'jobs':set(),'candidates':[]}
            reqs[norm]['jobs'].add(job['id'])
            candidates=[]
            for e in evidence:
                matched=lexical_support(req,e)
                if matched:
                    candidates.append({'evidence_id':e['id'],'title':e['title'],'kind':e['kind'],
                                       'status':e.get('status','DECLARED'),'source_url':e.get('url') or None,
                                       **matched})
            candidates.sort(key=lambda c:(c['kind'] not in ('project','experience'),c['evidence_id']))
            rows.append({'requirement':req,'state':'CANDIDATE_UNVERIFIED' if candidates else 'NOT_DOCUMENTED',
                         'candidate_evidence':candidates[:8],
                         'explanation':('Termos presentes em evidências declaradas; confirme profundidade e autoria.' if candidates else 'Nenhuma evidência textual suficiente; não significa falta de competência.')})
            if candidates:
                known={c['evidence_id'] for c in reqs[norm]['candidates']}
                reqs[norm]['candidates'] += [c for c in candidates if c['evidence_id'] not in known]
        job_views.append({'job_id':job['id'],'title':job['title'],'company':job['company'],
                          'source_url':job.get('source_url') or None,'requirements':rows,
                          'documented_candidates':sum(r['state']=='CANDIDATE_UNVERIFIED' for r in rows),
                          'not_documented':sum(r['state']=='NOT_DOCUMENTED' for r in rows),
                          'fit_probability':None})
    priorities=[]
    for entry in reqs.values():
        frequency=len(entry['jobs'])
        documented=bool(entry['candidates'])
        # Priority is deterministic and explainable, not a hiring probability.
        priorities.append({'requirement':entry['requirement'],'jobs_requiring':frequency,
                           'job_ids':sorted(entry['jobs']),
                           'state':'CANDIDATE_UNVERIFIED' if documented else 'NOT_DOCUMENTED',
                           'evidence_refs':entry['candidates'][:8],
                           'priority_points':frequency*10+(0 if documented else 5),
                           'rationale':f'Presente em {frequency} vaga(s); '+('há indícios textuais, mas falta validação.' if documented else 'não há evidência textual documentada.'),
                           'next_action':('Revisar a evidência e adicionar resultados mensuráveis reais, se existirem.' if documented else 'Verificar se já possui essa competência; se sim, documentar projeto real; se não, planejar prática.')})
    priorities.sort(key=lambda x:(-x['priority_points'],normalize(x['requirement'])))
    actions=[]
    if not profile.get('target_role'):actions.append({'type':'profile','action':'Definir cargo-alvo e critérios de escolha.','why':'Cargo-alvo ausente.','linked_jobs':[]})
    if not jobs:actions.append({'type':'opportunities','action':'Cadastrar 2 a 3 vagas reais com requisitos explícitos.','why':'Ainda não há vagas para comparar.','linked_jobs':[]})
    if not evidence:actions.append({'type':'evidence','action':'Registrar um projeto ou experiência com escopo, contribuição e resultado.','why':'Nenhuma evidência declarada.','linked_jobs':[]})
    for p in priorities[:max(0,3-len(actions))]:
        actions.append({'type':'verify' if p['state']=='CANDIDATE_UNVERIFIED' else 'document',
                        'action':p['next_action']+' Foco: '+p['requirement'],
                        'why':p['rationale'],'linked_jobs':p['job_ids']})
    if not actions:actions.append({'type':'review','action':'Revisar o plano e atualizar os resultados das candidaturas.','why':'Nenhuma lacuna inicial identificada pelos dados disponíveis.','linked_jobs':[]})
    app_counts=dict(Counter(a['status'] for a in applications))
    done=sum(bool(t.get('done')) for t in tasks)
    coverage={'jobs_with_requirements':sum(bool(j['requirements']) for j in jobs),'total_jobs':len(jobs),
              'evidence_with_sources':sum(bool(e.get('url')) for e in evidence),'total_evidence':len(evidence),
              'requirements_with_candidates':sum(bool(p['evidence_refs']) for p in priorities),'total_requirements':len(priorities)}
    return {'engine':'Career Intelligence v1','method':'regras determinísticas, comparação lexical conservadora e priorização por frequência nas vagas',
            'target_role':profile.get('target_role',''),'quality':{'coverage':coverage,'data_quality_notes':[
                'URLs informadas pelo usuário não foram abertas nem verificadas.',
                'Evidências declaradas não equivalem a competências comprovadas.',
                'Requisitos devem ser extraídos de vagas reais e revisados pelo usuário.']},
            'opportunities':job_views,'requirement_priorities':priorities,'top_actions':actions[:3],
            'progress':{'applications_by_status':app_counts,'tasks_done':done,'tasks_total':len(tasks)},
            'uncertainties':['Não mede proficiência nem autenticidade de projetos.','Não estima contratação ou remuneração.',
                             'A ausência de correspondência textual não demonstra ausência de habilidade.'],
            'hiring_probability':None}
