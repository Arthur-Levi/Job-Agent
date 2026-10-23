"""Non-executing, user-submitted source artifact review; NOT authenticity verification."""
import hashlib, re
from pathlib import PurePosixPath

VERSION='artifact-review-v1'
MAX_FILES=30
MAX_TOTAL_BYTES=120_000
TEST_PATH=re.compile(r'(^|/)(tests?/|test_[^/]+\.py$|[^/]+\.(test|spec)\.[jt]sx?$|__tests__/)',re.I)
DOC_PATH=re.compile(r'(^|/)(readme(\.md|\.rst|\.txt)?|docs?/[^/]+\.(md|rst))$',re.I)
CI_PATH=re.compile(r'^\.github/workflows/[^/]+\.ya?ml$|^\.gitlab-ci\.yml$',re.I)
DEPENDENCY_PATH=re.compile(r'(^|/)(pyproject\.toml|requirements[^/]*\.txt|package\.json|go\.mod|cargo\.toml)$',re.I)
SECRET_RE=re.compile(r'(?i)(-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:api[_-]?key|secret|token|password)\s*[:=]\s*[\"\']?[^\s\"\']{12,})')

def review(files):
    if not isinstance(files,list) or not 1<=len(files)<=MAX_FILES:
        raise ValueError('Envie entre 1 e 30 arquivos de texto.')
    total=0; normalized=[]; paths=set()
    for item in files:
        if not isinstance(item,dict):raise ValueError('Formato de arquivo inválido.')
        path=item.get('path'); content=item.get('content')
        if not isinstance(path,str) or not isinstance(content,str) or not path or len(path)>240:
            raise ValueError('Caminho ou conteúdo inválido.')
        path=path.replace('\\','/')
        p=PurePosixPath(path)
        if p.is_absolute() or any(x in ('.','..') for x in path.split('/')) or '\x00' in path or path in paths:
            raise ValueError('Caminho inválido ou duplicado.')
        if any(ord(ch)<32 for ch in path):raise ValueError('Caminho inválido.')
        size=len(content.encode('utf-8'));total+=size
        if total>MAX_TOTAL_BYTES:raise ValueError('Limite de 120 KB excedido.')
        if SECRET_RE.search(content):raise ValueError('Possível segredo detectado. Remova credenciais antes de enviar.')
        paths.add(path)
        normalized.append((path,content))
    categories={'source':[],'tests':[],'documentation':[],'ci':[],'dependencies':[]}
    for path,content in normalized:
        if TEST_PATH.search(path):categories['tests'].append(path)
        if DOC_PATH.search(path):categories['documentation'].append(path)
        if CI_PATH.search(path):categories['ci'].append(path)
        if DEPENDENCY_PATH.search(path):categories['dependencies'].append(path)
        if re.search(r'\.(py|js|jsx|ts|tsx|go|rs|java)$',path,re.I) and not TEST_PATH.search(path):categories['source'].append(path)
    checks={
        'source_present':bool(categories['source']),
        'test_files_present':bool(categories['tests']),
        'documentation_present':bool(categories['documentation']),
        'dependency_manifest_present':bool(categories['dependencies']),
        'ci_configuration_present':bool(categories['ci']),
    }
    # This is an artifact inventory, not a quality or competence score.
    digest=hashlib.sha256()
    for path,content in sorted(normalized):
        digest.update(path.encode());digest.update(b'\0');digest.update(content.encode());digest.update(b'\0')
    gaps=[k for k,v in checks.items() if not v]
    return {'review_version':VERSION,'inventory_sha256':digest.hexdigest(),'file_count':len(normalized),
            'categories':categories,'checks':checks,'missing_artifact_categories':gaps,
            'interpretation':'Inventário de artefatos fornecidos pelo usuário. Presença de arquivos não comprova execução, correção, autoria ou domínio.',
            'authorship_verified':False,'technical_correctness_verified':False,'tests_executed':False,
            'proficiency_score':None,'verification_status':'USER_SUBMITTED_UNVERIFIED',
            'next_steps':['Executar testes em ambiente isolado e autorizado.', 'Revisar autoria e contribuições com consentimento.', 'Realizar revisão técnica humana quando necessária.']}
