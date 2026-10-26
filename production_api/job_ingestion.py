"""Conservative job text parsing: suggestions for human review, no web access."""
import re

HEADINGS=('requisitos','requisitos obrigatorios','requisitos desejaveis','qualificacoes',
          'qualificacoes necessarias','o que buscamos','voce precisa ter',
          'competencias','habilidades','requirements','qualifications',
          'responsabilidades','atividades')
TERMS=('python','javascript','typescript','java','react','node.js','sql','postgresql',
       'excel','power bi','docker','git','aws','azure','fastapi','django',
       'comunicacao','lideranca','ingles','logistica','administrativo')

def normalize(value):
    import unicodedata
    value=unicodedata.normalize('NFKD',value)
    return ''.join(c for c in value if not unicodedata.combining(c)).casefold()

def extract_job_preview(text):
    if not isinstance(text,str) or not 40<=len(text.strip())<=12000:
        raise ValueError('Cole uma descrição de vaga de 40 a 12.000 caracteres.')
    text=text.strip()
    lines=[line.strip(' \t•*-') for line in text.splitlines()]
    lines=[line for line in lines if line]
    title=''
    company=''
    for line in lines[:12]:
        m=re.match(r'(?i)^(?:cargo|vaga|posi[cç][aã]o|job title)\s*:\s*(.+)$',line)
        if m:title=m.group(1).strip()[:160]
        m=re.match(r'(?i)^(?:empresa|company|organiza[cç][aã]o)\s*:\s*(.+)$',line)
        if m:company=m.group(1).strip()[:160]
    if not title:
        first=lines[0]
        if len(first)<=90 and ':' not in first:title=first[:160]
    requirements=[]
    in_section=False
    for line in lines:
        normalized=normalize(line).rstrip(':')
        if normalized in HEADINGS:
            in_section=normalized not in ('responsabilidades','atividades')
            continue
        if re.match(r'^([A-ZÀ-Ý][\wÀ-ÿ\s]{3,40}):$',line):
            in_section=False
            continue
        candidate=line.lstrip('0123456789. )-•').strip()
        if in_section and 3<=len(candidate)<=160 and candidate.lower()!=line.lower().rstrip(':'):
            pass
        if in_section and 3<=len(candidate)<=160:
            if candidate not in requirements:requirements.append(candidate)
    normalized=normalize(text)
    for term in TERMS:
        if re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',normalized):
            match=next((r for r in requirements if normalize(term) in normalize(r)),None)
            if not match:requirements.append(term)
    return {'title_draft':title,'company_draft':company,
            'description_draft':text[:10000],
            'requirements_draft':requirements[:40],
            'limitations':['Sugestões extraídas do texto informado, sem checagem externa.',
                           'Revise título, empresa e cada requisito antes de salvar.',
                           'Termos mencionados não são requisitos confirmados automaticamente.'],
            'source':'user_supplied_text','saved':False}
