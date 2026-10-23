"""Conservative, explainable near-duplicate detection for imported evidence."""
import re
from difflib import SequenceMatcher
from resume_journey import normalize

def tokens(s):
    return set(re.findall(r"[a-z0-9]+",normalize(s))) - {"de","da","do","em","para","com","e","the","and"}

def similarity(a,b):
    a,b=normalize(a),normalize(b)
    if not a or not b:return 0.0
    ta,tb=tokens(a),tokens(b)
    overlap=len(ta&tb)/len(ta|tb) if ta|tb else 0.0
    return round(max(SequenceMatcher(None,a,b).ratio(),overlap),3)

def classify(incoming,existing):
    if incoming.kind!=existing.kind:return None
    title=similarity(incoming.title,existing.title)
    desc=similarity(incoming.description,existing.description)
    if title>=0.98 and desc>=0.96:return 'duplicate'
    if title>=0.84 and desc>=0.64:return 'possible_duplicate'
    return None
