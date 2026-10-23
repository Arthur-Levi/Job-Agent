"""Evaluate unverified, user-submitted commit summaries without claiming identity."""
from collections import Counter
from datetime import datetime

VERSION='contributions-v1'

def summarize(commits):
    if not isinstance(commits,list) or len(commits)>200:raise ValueError('Máximo de 200 commits')
    authors=Counter(); files=Counter(); seen=set(); entries=[]
    for c in commits:
        if not isinstance(c,dict):raise ValueError('Commit inválido')
        sha=c.get('sha');author=c.get('author');paths=c.get('files',[])
        if not isinstance(sha,str) or not (7<=len(sha)<=64) or not all(ch in '0123456789abcdefABCDEF' for ch in sha) or sha in seen:raise ValueError('SHA inválido ou duplicado')
        if not isinstance(author,str) or not 1<=len(author)<=120 or not isinstance(paths,list) or len(paths)>100:raise ValueError('Metadados inválidos')
        if any(not isinstance(p,str) or len(p)>240 or '..' in p.split('/') for p in paths):raise ValueError('Caminho inválido')
        seen.add(sha);authors[author]+=1;files.update(set(paths));entries.append({'sha':sha,'claimed_author':author,'changed_files_count':len(paths)})
    return {'version':VERSION,'commits_count':len(entries),'claimed_authors':dict(authors),'most_changed_files':files.most_common(10),
            'entries':entries,'source':'USER_SUBMITTED_UNVERIFIED','identity_verified':False,'authorship_verified':False,
            'warning':'Nome/email no commit não comprovam identidade, autoria ou contribuição intelectual; dados fornecidos pelo usuário não foram consultados no provedor.'}
