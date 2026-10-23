"""Conservative static checks for submitted Python source; no code execution."""
import ast
from collections import Counter
from artifact_review import review

VERSION = 'technical-static-v1'

def analyze(files):
    inventory=review(files)
    findings=[]; stats=Counter()
    for item in files:
        path=item['path']; src=item['content']
        if not path.endswith('.py'):continue
        stats['python_files']+=1
        try: tree=ast.parse(src,filename=path)
        except SyntaxError as exc:
            findings.append({'path':path,'line':exc.lineno,'severity':'high','rule':'PY_SYNTAX','detail':'Sintaxe Python inválida'})
            continue
        stats['python_parseable']+=1
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                stats['functions']+=1
                if not ast.get_docstring(node) and not node.name.startswith('test_'):
                    findings.append({'path':path,'line':node.lineno,'severity':'info','rule':'MISSING_DOCSTRING','detail':'Função sem docstring'})
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=([a.name.split('.')[0] for a in node.names] if isinstance(node,ast.Import) else [str(node.module or '').split('.')[0]])
                if any(n in ('subprocess','pickle','marshal') for n in names):
                    findings.append({'path':path,'line':node.lineno,'severity':'review','rule':'SENSITIVE_IMPORT','detail':'Importação requer revisão contextual; não é necessariamente insegura'})
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('eval','exec'):
                findings.append({'path':path,'line':node.lineno,'severity':'review','rule':'DYNAMIC_EXECUTION','detail':'Execução dinâmica requer revisão contextual'})
            if isinstance(node,ast.Assert):stats['assertions']+=1
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='print':stats['print_calls']+=1
    # Do not claim passing tests, secure code, authorship, or proficiency.
    return {'version':VERSION,'inventory_sha256':inventory['inventory_sha256'],'static_findings':findings[:100],
            'statistics':dict(stats),'analyzed_languages':['python'],
            'static_analysis_only':True,'tests_executed':False,'code_correctness_verified':False,
            'authorship_verified':False,'proficiency_score':None,
            'limitations':['Análise sintática e heurística limitada a Python','Não avalia lógica, cobertura, exploração ou autoria','Ausência de achados não demonstra segurança']}
