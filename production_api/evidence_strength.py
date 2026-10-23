"""Conservative evidence documentation rubric. NOT a proficiency or authenticity score."""
from urllib.parse import urlparse

RUBRIC_VERSION = 'documentation-v1.0'
FIELDS = ('scope','personal_contribution','method','result','limitations')
WEIGHTS = {'scope':15,'personal_contribution':25,'method':20,'result':25,'limitations':15}

def evaluate(evidence, submission):
    """Only user-declared details are scored; no URLs are fetched or validated."""
    details = {field:str(submission.get(field) or '').strip() for field in FIELDS}
    checks = {}
    score = 0
    for field in FIELDS:
        # minimum descriptive length reduces gaming by single-word claims, not fraud
        sufficient = len(details[field]) >= 35
        checks[field] = {'documented':sufficient,'points':WEIGHTS[field] if sufficient else 0,
                         'max_points':WEIGHTS[field]}
        score += checks[field]['points']
    url = str(evidence.get('url') or '').strip()
    parsed = urlparse(url)
    source_supplied = parsed.scheme in ('https','http') and bool(parsed.hostname)
    if score >= 85: band='DOCUMENTATION_DETAILED'
    elif score >= 50: band='DOCUMENTATION_PARTIAL'
    else: band='DOCUMENTATION_THIN'
    return {'rubric_version':RUBRIC_VERSION,'documentation_score':score,'documentation_band':band,
            'checks':checks,'source_link_supplied':source_supplied,
            'verification_status':'NOT_INDEPENDENTLY_VERIFIED',
            'proficiency_score':None,'authorship_verified':False,
            'caveats':['Pontuação mede apenas detalhamento textual informado pelo usuário.',
                       'URLs não são abertas; autoria, resultados e domínio técnico não foram verificados.',
                       'Texto longo pode ser falso; não utilize como probabilidade de contratação.']}
