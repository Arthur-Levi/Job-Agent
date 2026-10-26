"""Readable, evidence-grounded actions from the existing lexical analysis."""
def summarize(opportunity):
    rows=[]
    for r in opportunity.get('requirements',[]):
        refs=r.get('candidate_evidence') or []
        if refs:
            action='Revise a experiência indicada e descreva sua contribuição real, contexto e resultado, quando existirem.'
            label='Menção encontrada — não verificada'
        else:
            action='Confira se possui experiência real com este requisito; se possuir, registre evidência. Caso contrário, considere um projeto prático.'
            label='Não documentado — não significa desconhecimento'
        rows.append({'requirement':r['requirement'],'status':r['state'],'label':label,
                     'explanation':r['explanation'],'evidence':[{'id':e['evidence_id'],'title':e['title'],'kind':e['kind']} for e in refs[:4]],
                     'next_action':action,'action_title':('Revisar evidência: ' if refs else 'Documentar requisito: ')+r['requirement'][:130]})
    return {'job_id':opportunity['job_id'],'title':opportunity['title'],'company':opportunity['company'],
            'requirements':rows,'counts':{'mentioned_unverified':sum(bool(r['evidence']) for r in rows),
            'not_documented':sum(not r['evidence'] for r in rows),'total':len(rows)},
            'limitations':['Comparação textual não comprova domínio de habilidades.',
            'Falta de menção não significa ausência de competência.',
            'Não calculamos chance de contratação ou adequação percentual.'],
            'hiring_probability':None}
