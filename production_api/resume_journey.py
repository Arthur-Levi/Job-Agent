"""Conservative CV segmentation; never asserts authorship or verified skills."""
import re
import unicodedata

HEADINGS = {
 'experience':r'(?:experi[eê]ncias?(?: profissional| profissionais| de trabalho)?|hist[oó]rico profissional|employment|work experience|professional experience|experiencia laboral)',
 'education':r'(?:forma[cç][aã]o(?: acad[eê]mica)?|educa[cç][aã]o|education|academic background|escolaridade)',
 'projects':r'(?:projetos?(?: pessoais| profissionais| relevantes)?|projects|portfolio|portf[oó]lio)',
 'skills':r'(?:habilidades|compet[eê]ncias(?: t[eé]cnicas)?|tecnologias|skills|technical skills)',
 'summary':r'(?:resumo(?: profissional)?|perfil profissional|sobre mim|professional summary|about me)',
 'objective':r'(?:objetivo(?: profissional)?|cargo desejado|career objective|objective)',
}
KINDS={'experience':'experience','education':'education','projects':'project'}
DEFAULTS={'experience':'Experiência descrita no currículo','education':'Formação descrita no currículo','projects':'Projeto descrito no currículo'}
DATE=r'(?:\b(?:19|20)\d{2}\b|\b(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*[ /-]+\d{4}\b|\b(?:atual|presente|current|present)\b)'

def normalize(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c)).split())

def section_for(line):
    line=line.strip().strip('#*: ').rstrip(':').strip()
    line=re.sub(r'^[0-9]+[.)\s-]+','',line).strip()
    if len(line)>80:return None
    for key,pat in HEADINGS.items():
        if re.fullmatch(pat,line,flags=re.I):return key
    return None

def split_entries(lines):
    """Split only at explicit bullets, blank lines, or strong date-bearing headings."""
    groups=[];current=[]
    for raw in lines:
        line=raw.strip()
        if not line:
            if current:groups.append(current);current=[]
            continue
        bullet=bool(re.match(r'^(?:[-•●*]|\d+[.)])\s+',line))
        # Table-cell delimiters can indicate a new role, but never split plain prose.
        table_role=bool(re.match(r'^.{3,65}\s*[|\t]\s*.{3,65}',line)) and bool(re.search(DATE,line,re.I))
        title_like=(bool(re.search(DATE,line,re.I)) and len(line)<=115 and not line.endswith('.'))
        if current and (bullet or table_role or (title_like and len(current)>=2)):
            groups.append(current);current=[]
        current.append(re.sub(r'^(?:[-•●*]|\d+[.)])\s+','',line)[:350])
    if current:groups.append(current)
    return groups[:15]

def suggestions(text):
    blocks={};current=None
    for line in text.splitlines():
        heading=section_for(line)
        if heading:
            current=heading;blocks.setdefault(current,[])
        elif current is not None:
            blocks[current].append(line.rstrip())
    evidence=[]
    for section,kind in KINDS.items():
        for group in split_entries(blocks.get(section,[])):
            if not group:continue
            first=group[0]
            title=first[:160] if len(first)>=3 and len(first)<=115 else DEFAULTS[section]
            description='\n'.join(group)[:3500]
            if len(description)<5:continue
            evidence.append({'kind':kind,'title':title,'description':description,'url':'',
               'source_section':section,'status':'DRAFT_UNVERIFIED'})
    role=next((line.strip() for line in blocks.get('objective',[]) if 3<=len(line.strip())<=120),'')
    return {'evidence_drafts':evidence[:15],'target_role_draft':role,
      'limitations':['Separação heurística: revise agrupamentos, datas e títulos.',
       'Seções sem cabeçalho reconhecido podem ser ignoradas.',
       'Autoria, resultados e competências não são verificados automaticamente.']}
